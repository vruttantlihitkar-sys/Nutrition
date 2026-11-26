import re
from datetime import datetime
from functools import lru_cache
from typing import Any

import pandas as pd

from backend.config import settings

DEFAULT_MATCH_COLUMNS = [
    "food_code",
    "food_name",
    "energy_kcal",
    "protein_g",
    "carb_g",
    "fat_g",
    "fibre_g",
    "servings_unit",
    "source_file",
]


def normalize_text(text: str) -> str:
    cleaned = str(text).strip().lower()
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _get_llm_classes():
    from llm_integration import NutritionDataProcessor, NutritionLLMIntegration, NutritionQuery

    return NutritionDataProcessor, NutritionLLMIntegration, NutritionQuery


@lru_cache(maxsize=1)
def get_processor_and_data() -> tuple[Any, pd.DataFrame]:
    NutritionDataProcessor, _, _ = _get_llm_classes()
    processor = NutritionDataProcessor(use_spacy=True)
    data = processor.load_nutrition_data([settings.dataset_path])
    return processor, data


def build_llm_engine(
    use_lmstudio: bool,
    openai_api_key: str | None = None,
    lmstudio_url: str | None = None,
    lmstudio_model: str | None = None,
) -> Any:
    _, NutritionLLMIntegration, _ = _get_llm_classes()
    processor, nutrition_data = get_processor_and_data()
    return NutritionLLMIntegration(
        nutrition_data=nutrition_data,
        processor=processor,
        api_key=openai_api_key,
        use_lmstudio=use_lmstudio,
        lmstudio_url=lmstudio_url or settings.lmstudio_url,
        lmstudio_model=lmstudio_model or settings.lmstudio_model,
    )


def run_query(
    *,
    user_id: str,
    query_text: str,
    query_type: str,
    context: dict[str, Any],
    use_lmstudio: bool,
    openai_api_key: str | None = None,
    lmstudio_url: str | None = None,
    lmstudio_model: str | None = None,
) -> dict[str, Any]:
    engine = build_llm_engine(
        use_lmstudio=use_lmstudio,
        openai_api_key=openai_api_key,
        lmstudio_url=lmstudio_url,
        lmstudio_model=lmstudio_model,
    )
    _, _, NutritionQuery = _get_llm_classes()
    query = NutritionQuery(
        user_id=user_id,
        query=query_text,
        context=context,
        timestamp=datetime.now(),
        query_type=query_type,
    )
    response = engine.handle_query(query)
    return {
        "response": response,
        "matched_items": find_matched_foods(query_text),
    }


def generate_grounded_nutrition_text(
    *,
    prompt: str,
    context_blocks: list[str],
    use_lmstudio: bool,
    openai_api_key: str | None = None,
    lmstudio_url: str | None = None,
    lmstudio_model: str | None = None,
) -> str:
    engine = build_llm_engine(
        use_lmstudio=use_lmstudio,
        openai_api_key=openai_api_key,
        lmstudio_url=lmstudio_url,
        lmstudio_model=lmstudio_model,
    )
    system_message = (
        "You are a nutrition explanation assistant. "
        "Use only the supplied nutrition facts. "
        "Be specific, practical, and concise. "
        "If the data is limited, say so plainly instead of inventing facts."
    )
    user_message = "\n\n".join([prompt, *context_blocks])

    if use_lmstudio:
        return engine._call_lmstudio(
            [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ]
        )

    if engine.openai_client is not None:
        response = engine.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            max_tokens=220,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""

    if engine._legacy_openai is not None:
        response = engine._legacy_openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            max_tokens=220,
            temperature=0.3,
        )
        return response["choices"][0]["message"]["content"]

    # Deterministic fallback if no LLM is available.
    return "Dataset-backed nutrition facts are available, but AI text generation is currently unavailable."


def find_matched_foods(query_text: str) -> list[dict[str, Any]]:
    _, nutrition_data = get_processor_and_data()
    if "food_name" not in nutrition_data.columns:
        return []

    working_df = nutrition_data.copy()
    if "food_name_norm" not in working_df.columns:
        working_df["food_name_norm"] = working_df["food_name"].apply(normalize_text)

    normalized_query = normalize_text(query_text)
    matched = working_df[working_df["food_name_norm"].apply(lambda value: value in normalized_query)]
    if matched.empty:
        return []

    available_columns = [column for column in DEFAULT_MATCH_COLUMNS if column in matched.columns]
    if available_columns:
        matched = matched[available_columns]

    matched = matched.drop(columns=["food_name_norm"], errors="ignore")
    matched = matched.where(pd.notnull(matched), None)
    return matched.head(10).to_dict(orient="records")
