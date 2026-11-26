import json
import pandas as pd
import numpy as np
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from textblob import TextBlob
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import Dict, List, Tuple, Optional, Any
import logging
import os
from datetime import datetime
from dataclasses import dataclass
import requests  # for LM Studio local API
from dotenv import load_dotenv

try:
    import spacy
    SPACY_IMPORT_ERROR = None
except Exception as exc:
    spacy = None
    SPACY_IMPORT_ERROR = exc

load_dotenv()

LMSTUDIO_CONNECT_TIMEOUT_SECONDS = 10
LMSTUDIO_READ_TIMEOUT_SECONDS = 180

class NutritionDataProcessor:
    def __init__(self, use_spacy: bool = True):
        self.use_spacy = use_spacy
        self.lemmatizer = WordNetLemmatizer()
        try:
            self.stop_words = set(stopwords.words('english'))
        except LookupError:
            logging.warning("NLTK stopwords data not available, continuing with an empty stopword set.")
            self.stop_words = set()
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.tfidf_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        if self.use_spacy and spacy is not None:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logging.warning("spaCy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm")
                self.use_spacy = False
            except Exception as exc:
                logging.warning("spaCy is unavailable, falling back to basic matching: %s", exc)
                self.use_spacy = False
        elif self.use_spacy and spacy is None:
            logging.warning("spaCy import failed, falling back to basic matching: %s", SPACY_IMPORT_ERROR)
            self.use_spacy = False
        self._embedder = None
        enable_embeddings = os.getenv("ENABLE_SENTENCE_TRANSFORMERS", "false").strip().lower() == "true"
        if enable_embeddings:
            try:
                from sentence_transformers import SentenceTransformer

                self._embedder = SentenceTransformer("paraphrase-MiniLM-L6-v2")
            except Exception as exc:
                logging.warning("SentenceTransformer unavailable, falling back to rule-based retrieval: %s", exc)
        self._food_embeddings = None

    def clean_text(self, text: str) -> str:
        if pd.isna(text) or not isinstance(text, str): return ""
        text = text.lower()
        text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
        text = ' '.join(text.split())
        return text

    def load_nutrition_data(self, file_paths: List[str]) -> pd.DataFrame:
        dataframes = []
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    if file_path.endswith('.xlsx'):
                        df = pd.read_excel(file_path)
                    else:
                        df = pd.read_csv(file_path)
                    df['source_file'] = os.path.basename(file_path)
                    dataframes.append(df)
                    logging.info(f"Loaded {len(df)} records from {file_path}")
                else:
                    logging.warning(f"File not found: {file_path}")
            except Exception as e:
                logging.error(f"Error loading {file_path}: {str(e)}")
        if not dataframes:
            return pd.DataFrame()
        combined_df = pd.concat(dataframes, ignore_index=True)
        logging.info(f"Combined dataset: {len(combined_df)} total records")
        if 'food_name' in combined_df.columns:
            combined_df['food_name_clean'] = combined_df['food_name'].astype(str).apply(self.clean_text)
        return combined_df

    def advanced_food_item_retrieve(self, query: str, df: pd.DataFrame, topn: int = 1) -> pd.DataFrame:
        if 'food_name_clean' not in df.columns:
            df['food_name_clean'] = df['food_name'].astype(str).apply(self.clean_text)
        food_names = df['food_name_clean'].tolist()
        query_clean = self.clean_text(query)
        matches = [name for name in food_names if name in query_clean]
        if matches:
            return df[df['food_name_clean'].isin(matches)].head(topn)
        if self.use_spacy and hasattr(self, 'nlp'):
            doc = self.nlp(query)
            noun_chunks = [self.clean_text(chunk.text) for chunk in doc.noun_chunks]
            for chunk in noun_chunks:
                matches = [name for name in food_names if chunk in name]
                if matches:
                    return df[df['food_name_clean'].isin(matches)].head(topn)

        if self._embedder:
            try:
                if self._food_embeddings is None:
                    self._food_embeddings = self._embedder.encode(food_names, normalize_embeddings=True)
                query_vec = self._embedder.encode([query_clean], normalize_embeddings=True)
                sims = np.dot(self._food_embeddings, query_vec.T).flatten()
                idx = np.argmax(sims)
                if sims[idx] > 0.65:
                    return df.iloc[[idx]]
            except Exception:
                pass
        return pd.DataFrame()

@dataclass
class NutritionQuery:
    user_id: str
    query: str
    context: Dict[str, Any]
    timestamp: datetime
    query_type: str

class NutritionLLMIntegration:
    def __init__(
        self,
        nutrition_data: pd.DataFrame,
        processor,
        api_key: Optional[str] = None,
        use_lmstudio: bool = False,
        lmstudio_url: str = "http://localhost:1234/v1/chat/completions",
        lmstudio_model: str = "openchat-3.6-8b-20240522"
    ):
        self.nutrition_data = nutrition_data
        self.processor = processor
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.use_lmstudio = use_lmstudio
        self.lmstudio_url = lmstudio_url
        self.lmstudio_model = lmstudio_model
        self.openai_client = None
        self._legacy_openai = None
        if self.api_key and not use_lmstudio:
            try:
                from openai import OpenAI

                self.openai_client = OpenAI(api_key=self.api_key)
            except Exception:
                try:
                    import openai

                    openai.api_key = self.api_key
                    self._legacy_openai = openai
                except Exception as exc:
                    logging.warning("OpenAI client unavailable, falling back to rule-based responses: %s", exc)
        self.conversation_history = {}
        self.system_prompts = {
            'nutritionist': "You are a professional nutritionist and dietitian...",
            'meal_planner': "You are an expert meal planning specialist...",
            'educator': "You are a nutrition educator who explains complex concepts...",
            'analyzer': "You are a food and nutrition analyst who can break down meals..."
        }
        self.nutrition_knowledge = {
            'macronutrients': {
                'protein': {
                    'functions': 'Building and repairing tissues, enzyme production, immune function',
                    'sources': 'Meat, fish, eggs, dairy, legumes, nuts, seeds',
                    'daily_needs': '0.8-1.6g per kg body weight'
                },
                'carbohydrates': {
                    'functions': 'Primary energy source, brain fuel, muscle fuel',
                    'sources': 'Grains, fruits, vegetables, legumes',
                    'daily_needs': '45-65% of total calories'
                },
                'fats': {
                    'functions': 'Energy storage, vitamin absorption, hormone production',
                    'sources': 'Oils, nuts, seeds, fatty fish, avocado',
                    'daily_needs': '20-35% of total calories'
                }
            },
            'micronutrients': {
                'vitamins': {
                    'A': {'functions': 'Vision, immune function', 'sources': 'Orange vegetables, leafy greens'},
                    'C': {'functions': 'Antioxidant, collagen synthesis', 'sources': 'Citrus fruits, berries'},
                    'D': {'functions': 'Bone health, immune function', 'sources': 'Sunlight, fatty fish, fortified foods'},
                    'E': {'functions': 'Antioxidant, cell protection', 'sources': 'Nuts, seeds, vegetable oils'},
                    'K': {'functions': 'Blood clotting, bone health', 'sources': 'Leafy greens, broccoli'}
                },
                'minerals': {
                    'calcium': {'functions': 'Bone health, muscle function', 'sources': 'Dairy, leafy greens, fortified foods'},
                    'iron': {'functions': 'Oxygen transport, energy metabolism', 'sources': 'Red meat, beans, spinach'},
                    'magnesium': {'functions': 'Enzyme function, muscle relaxation', 'sources': 'Nuts, seeds, whole grains'},
                    'zinc': {'functions': 'Immune function, wound healing', 'sources': 'Meat, shellfish, legumes'},
                    'potassium': {'functions': 'Fluid balance, nerve signaling', 'sources': 'Bananas, potatoes, beans'}
                }
            }
        }

    def _extract_text_from_lmstudio_response(self, data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message") or {}
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_value = item.get("text")
                        if isinstance(text_value, str) and text_value.strip():
                            text_parts.append(text_value.strip())
                if text_parts:
                    return "\n".join(text_parts)

        output = data.get("output")
        if isinstance(output, list):
            text_parts = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for content_item in content:
                    if isinstance(content_item, dict):
                        text_value = content_item.get("text")
                        if isinstance(text_value, str) and text_value.strip():
                            text_parts.append(text_value.strip())
            if text_parts:
                return "\n".join(text_parts)

        message = data.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()

        return ""

    def _post_to_lmstudio(self, payload: dict[str, Any]) -> dict[str, Any]:
        started_at = datetime.now()
        response = requests.post(
            self.lmstudio_url,
            json=payload,
            timeout=(LMSTUDIO_CONNECT_TIMEOUT_SECONDS, LMSTUDIO_READ_TIMEOUT_SECONDS),
        )
        elapsed = (datetime.now() - started_at).total_seconds()
        logging.info("LM Studio responded in %.2fs with status %s", elapsed, response.status_code)
        response.raise_for_status()
        return response.json()

    def _build_knowledge_summary(self) -> str:
        return (
            "Use the nutrition table as the source of truth for food-specific values. "
            "Protein supports tissue repair, carbohydrates provide energy, fats support hormones and vitamin absorption. "
            "Important micronutrients include calcium for bones, iron for oxygen transport, magnesium for muscle and enzyme function, "
            "potassium for fluid balance, and vitamins A, C, D, E, and K for vision, immunity, bone health, antioxidant protection, and clotting."
        )

    def _build_context(self, query: NutritionQuery) -> str:
        """Build context string for the LLM based on query, including robust table lookup."""
        role = query.query_type
        system_prompt = self.system_prompts.get(role, self.system_prompts['nutritionist'])
        table_context = self._context_from_nutrition_table(query.query, max_foods=5)
        context_parts = [
            system_prompt,
            f"Task type: {role}",
            f"User Context: {query.context}",
            f"Nutrition Table (matching items):\n{table_context}",
            f"Nutrition KB Summary:\n{self._build_knowledge_summary()}",
            "Answer in plain language. Keep it concise and directly answer the user's question."
        ]
        return "\n\n".join(context_parts)

    def _build_fallback_answer(self, query: NutritionQuery) -> str:
        matches = self.processor.advanced_food_item_retrieve(query.query, self.nutrition_data, topn=3)
        if not isinstance(matches, pd.DataFrame) or matches.empty:
            return self._rule_based_response(query)

        response_lines = []
        for _, row in matches.iterrows():
            food_name = row.get("food_name", "Unknown food")
            calories = row.get("energy_kcal", row.get("unit_serving_energy_kcal", "N/A"))
            protein = row.get("protein_g", "N/A")
            carbs = row.get("carb_g", row.get("carbs_g", "N/A"))
            fat = row.get("fat_g", "N/A")
            fibre = row.get("fibre_g", row.get("fiber_g", "N/A"))
            response_lines.append(
                f"{food_name}: about {calories} kcal, protein {protein} g, carbs {carbs} g, fat {fat} g, fibre {fibre} g."
            )

        intro = "I couldn't reach the language model, so here's a direct nutrition lookup from the dataset:"
        return f"{intro}\n\n" + "\n".join(response_lines)

    def _call_lmstudio(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.lmstudio_model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 300,
            "stream": False,
        }
        data = self._post_to_lmstudio(payload)
        answer = self._extract_text_from_lmstudio_response(data)
        if answer:
            return answer

        retry_messages = [
            {
                "role": "system",
                "content": "Answer the user's nutrition question briefly and directly using the provided food values.",
            },
            messages[-1],
        ]
        retry_payload = {
            "model": self.lmstudio_model,
            "messages": retry_messages,
            "temperature": 0.3,
            "max_tokens": 200,
            "stream": False,
        }
        retry_data = self._post_to_lmstudio(retry_payload)
        retry_answer = self._extract_text_from_lmstudio_response(retry_data)
        if retry_answer:
            return retry_answer

        logging.error("LM Studio returned an unrecognized payload: %s", json.dumps(data)[:1000])
        raise ValueError("LM Studio returned an empty or unrecognized response.")

    def _context_from_nutrition_table(self, user_query: str, max_foods=5) -> str:
        df = self.nutrition_data
        processor = self.processor
        matches = processor.advanced_food_item_retrieve(user_query, df, topn=max_foods)
        if isinstance(matches, pd.DataFrame) and not matches.empty:
            food_match_df = matches
        else:
            food_match_df = df.head(3)
        possible_cols = [col for col in df.columns if col not in ['food_name', 'food_name_clean']]
        requested_cols = []
        q_lower = user_query.lower()
        for c in possible_cols:
            simple_c = c.lower().replace("_", " ")
            if simple_c in q_lower or any(n in q_lower for n in simple_c.split()):
                requested_cols.append(c)
        if not requested_cols:
            requested_cols = [c for c in possible_cols if "calories" in c or "protein" in c or "carb" in c or "fat" in c or "fiber" in c]
            if not requested_cols: requested_cols = possible_cols[:5]
        context_df = food_match_df[["food_name"] + requested_cols] if requested_cols else food_match_df
        if not context_df.empty:
            out = context_df.to_string(index=False)
        else:
            out = "No matching foods."
        return out

    def _get_conversation(self, user_id: str) -> List[Dict[str, str]]:
        return self.conversation_history.get(user_id, [])

    def _update_conversation(self, user_id: str, role: str, content: str):
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        self.conversation_history[user_id].append({"role": role, "content": content})

    def handle_query(self, query: NutritionQuery) -> str:
        try:
            context = self._build_context(query)
            messages = [{"role": "system", "content": context}]
            history = self._get_conversation(query.user_id)
            messages.extend(history)
            messages.append({"role": "user", "content": query.query})
            if self.use_lmstudio:
                answer = self._call_lmstudio(messages)
            elif self.api_key:
                if self.openai_client is not None:
                    response = self.openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        max_tokens=500,
                        temperature=0.7
                    )
                    answer = response.choices[0].message.content or ""
                elif self._legacy_openai is not None:
                    response = self._legacy_openai.ChatCompletion.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        max_tokens=500,
                        temperature=0.7
                    )
                    answer = response['choices'][0]['message']['content']
                else:
                    return self._rule_based_response(query)
            else:
                return self._rule_based_response(query)
            self._update_conversation(query.user_id, "assistant", answer)
            return answer
        except Exception as e:
            logging.error(f"Error in handle_query: {e}")
            if self.use_lmstudio:
                return (
                    f"LM Studio did not return a usable answer ({e}). "
                    f"{self._build_fallback_answer(query)}"
                )
            return self._build_fallback_answer(query)

    def _rule_based_response(self, query: NutritionQuery) -> str:
        if query.query_type == "analysis":
            return f"Basic analysis: Based on your input {query.context}, aim for a balanced diet of protein, carbs, and fats."
        elif query.query_type == "recommendation":
            return f"Basic recommendation: Include fruits, vegetables, lean protein, and whole grains."
        elif query.query_type == "education":
            return f"Basic education: Nutrition involves macronutrients (protein, carbs, fats) and micronutrients (vitamins, minerals)."
        elif query.query_type == "meal_planning":
            return f"Basic meal plan: Breakfast - oats and fruit, Lunch - grilled chicken salad, Dinner - lentil soup with whole wheat bread."
        else:
            return "I'm not sure, but maintaining a balanced diet with variety is always beneficial."

# -------- MAIN USAGE EXAMPLE ---------
if __name__ == "__main__":
    # Set your file path!
    excel_path = "Anuvaad_INDB_2024.11.xlsx"

    processor = NutritionDataProcessor(use_spacy=True)
    nutrition_data = processor.load_nutrition_data([excel_path])

    # Initialize with processor argument included:
    llm_engine = NutritionLLMIntegration(
        nutrition_data,
        processor,  # <-- REQUIRED argument!
        api_key=None,        # Set if using OpenAI
        use_lmstudio=False,  # Set True if using LM Studio
        lmstudio_url="http://localhost:1234/v1/chat/completions",
        lmstudio_model="openchat-3.6-8b-20240522"
    )

    # Example test query
    query = NutritionQuery(
        user_id="user1",
        query="Show carbs and fat for lemonade and roti.",
        context={},
        timestamp=datetime.now(),
        query_type="analysis"
    )
    answer = llm_engine.handle_query(query)
    print(answer)
