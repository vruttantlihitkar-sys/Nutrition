from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import pandas as pd

from backend.config import settings


GOAL_RULES: dict[str, dict[str, Any]] = {
    "weight_loss": {
        "label": "Weight Loss",
        "calorie_factor": 0.82,
        "protein_ratio": 0.3,
        "carb_ratio": 0.35,
        "fat_ratio": 0.35,
        "reason": "Prioritizes lower-calorie, higher-satiety foods with strong protein and fiber.",
    },
    "muscle_gain": {
        "label": "Muscle Gain",
        "calorie_factor": 1.12,
        "protein_ratio": 0.3,
        "carb_ratio": 0.45,
        "fat_ratio": 0.25,
        "reason": "Prioritizes calorie-adequate meals with strong protein and recovery-friendly carbs.",
    },
    "balanced_diet": {
        "label": "Balanced Diet",
        "calorie_factor": 1.0,
        "protein_ratio": 0.24,
        "carb_ratio": 0.46,
        "fat_ratio": 0.3,
        "reason": "Targets balanced macros, fiber, and micronutrient density.",
    },
    "diabetic_friendly": {
        "label": "Diabetic Friendly",
        "calorie_factor": 0.95,
        "protein_ratio": 0.28,
        "carb_ratio": 0.37,
        "fat_ratio": 0.35,
        "reason": "Favors fiber, protein, and steadier carbohydrate choices.",
    },
    "heart_health": {
        "label": "Heart Health",
        "calorie_factor": 0.98,
        "protein_ratio": 0.23,
        "carb_ratio": 0.45,
        "fat_ratio": 0.32,
        "reason": "Favors fiber, potassium, and unsaturated-fat-friendly foods.",
    },
}

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

MEAL_DISTRIBUTION = {
    "breakfast": 0.25,
    "lunch": 0.33,
    "dinner": 0.30,
    "snacks": 0.12,
}

INDIAN_CUISINE_RULES = {
    "south_indian": ["idli", "dosa", "sambar", "upma", "pongal", "uttapam", "rasam"],
    "north_indian": ["roti", "paratha", "paneer", "rajma", "chole", "dal", "biryani", "naan"],
    "street_food": ["chaat", "samosa", "kachori", "pav", "pakora", "bhaji", "jalebi"],
    "beverage": ["chai", "tea", "coffee", "lassi", "sharbat"],
    "festival": ["halwa", "laddu", "kheer", "payasam", "barfi", "modak"],
}


def normalize_text(text: str) -> str:
    cleaned = str(text).strip().lower()
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def tokenize(text: str) -> list[str]:
    return [token for token in normalize_text(text).split() if token]


class NutriWiseCoach:
    def __init__(self) -> None:
        self.foods = self._load_foods()
        self.profiles: dict[str, dict[str, Any]] = {}
        self.history: dict[str, list[dict[str, Any]]] = {}

    def _load_foods(self) -> pd.DataFrame:
        dataset_path = settings.dataset_path
        if dataset_path.endswith(".xlsx"):
            df = pd.read_excel(dataset_path)
        else:
            df = pd.read_csv(dataset_path)

        foods = df.copy()
        foods["food_name"] = foods["food_name"].fillna("").astype(str)
        foods["search_text"] = foods["food_name"].map(normalize_text)
        foods["calories_per_100g"] = foods.get("energy_kcal", 0).fillna(0)
        foods["carbs_g"] = foods.get("carb_g", 0).fillna(0)
        foods["fiber_g"] = foods.get("fibre_g", 0).fillna(0)
        foods["serving_calories"] = foods.get("unit_serving_energy_kcal", foods["calories_per_100g"]).fillna(foods["calories_per_100g"])
        foods["serving_protein_g"] = foods.get("unit_serving_protein_g", foods.get("protein_g", 0)).fillna(foods.get("protein_g", 0))
        foods["serving_carbs_g"] = foods.get("unit_serving_carb_g", foods["carbs_g"]).fillna(foods["carbs_g"])
        foods["serving_fat_g"] = foods.get("unit_serving_fat_g", foods.get("fat_g", 0)).fillna(foods.get("fat_g", 0))
        foods["serving_fiber_g"] = foods.get("unit_serving_fibre_g", foods["fiber_g"]).fillna(foods["fiber_g"])
        foods["category"] = foods["food_name"].map(self._infer_category)
        foods["meal_slots"] = foods["food_name"].map(self._infer_meal_slots)
        foods["cuisine_tags"] = foods["food_name"].map(self._infer_cuisine_tags)
        foods["budget_tier"] = foods["food_name"].map(self._infer_budget_tier)
        foods["prep_time_minutes"] = foods["food_name"].map(self._infer_prep_time)
        foods["nutrition_density"] = foods.apply(self._nutrition_density, axis=1)
        return foods

    def _infer_category(self, food_name: str) -> str:
        name = normalize_text(food_name)
        category_rules = {
            "beverage": ["tea", "chai", "coffee", "lassi", "juice"],
            "grain": ["rice", "roti", "naan", "bread", "oats", "poha", "upma", "biryani", "quinoa", "millet"],
            "fruit": ["apple", "banana", "mango", "orange", "papaya", "fruit", "guava", "berry"],
            "vegetable": ["spinach", "broccoli", "bhindi", "okra", "gobi", "vegetable", "salad", "sabzi", "aloo", "tomato", "capsicum"],
            "protein": ["dal", "rajma", "chole", "paneer", "egg", "chicken", "fish", "tofu", "soya", "lentil", "sprout"],
            "snack": ["samosa", "pakora", "kachori", "chips", "chaat", "biscuit", "cookie", "namkeen"],
            "dessert": ["halwa", "kheer", "laddu", "barfi", "sweet", "jalebi", "payasam", "dessert"],
        }
        for category, keywords in category_rules.items():
            if any(keyword in name for keyword in keywords):
                return category
        return "general"

    def _infer_meal_slots(self, food_name: str) -> list[str]:
        name = normalize_text(food_name)
        slots: list[str] = []
        if any(keyword in name for keyword in ["tea", "coffee", "oats", "poha", "upma", "idli", "dosa", "egg", "toast"]):
            slots.append("breakfast")
        if any(keyword in name for keyword in ["rice", "dal", "rajma", "chole", "roti", "paneer", "salad", "biryani"]):
            slots.extend(["lunch", "dinner"])
        if any(keyword in name for keyword in ["fruit", "nuts", "chai", "coffee", "biscuit", "snack", "chaat"]):
            slots.append("snacks")
        if not slots:
            slots = ["lunch", "dinner"]
        return sorted(set(slots))

    def _infer_cuisine_tags(self, food_name: str) -> list[str]:
        name = normalize_text(food_name)
        tags = ["indian"]
        for cuisine, keywords in INDIAN_CUISINE_RULES.items():
            if any(keyword in name for keyword in keywords):
                tags.append(cuisine)
        if any(keyword in name for keyword in ["paneer", "rajma", "roti", "dal", "chai"]):
            tags.append("everyday_home_style")
        return sorted(set(tags))

    def _infer_budget_tier(self, food_name: str) -> str:
        name = normalize_text(food_name)
        if any(keyword in name for keyword in ["saffron", "salmon", "almond", "cashew", "pistachio", "mutton"]):
            return "high"
        if any(keyword in name for keyword in ["paneer", "chicken", "fish", "biryani", "quinoa"]):
            return "medium"
        return "low"

    def _infer_prep_time(self, food_name: str) -> int:
        name = normalize_text(food_name)
        if any(keyword in name for keyword in ["tea", "coffee", "fruit", "salad", "sprout"]):
            return 5
        if any(keyword in name for keyword in ["poha", "upma", "egg", "oats", "sandwich"]):
            return 15
        if any(keyword in name for keyword in ["dal", "rajma", "paneer", "biryani", "chole", "paratha"]):
            return 35
        return 20

    def _nutrition_density(self, row: pd.Series) -> float:
        calories = float(row.get("calories_per_100g", 0) or 0)
        protein = float(row.get("protein_g", 0) or 0)
        fiber = float(row.get("fiber_g", 0) or 0)
        calcium = float(row.get("calcium_mg", 0) or 0)
        iron = float(row.get("iron_mg", 0) or 0)
        potassium = float(row.get("potassium_mg", 0) or 0)
        base = protein * 1.8 + fiber * 1.4 + calcium / 120 + iron * 3 + potassium / 400
        penalty = calories / 180 if calories else 0
        return round(base - penalty, 3)

    def create_or_update_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = payload.get("user_id", "guest_123")
        age = int(payload.get("age", 25))
        weight = float(payload.get("weight", 70))
        height = float(payload.get("height", 170))
        gender = str(payload.get("gender", "female"))
        activity_level = str(payload.get("activity_level", "moderate"))
        health_goals = payload.get("health_goals") or ["balanced_diet"]

        bmi = weight / ((height / 100) ** 2)
        if gender.lower() == "male":
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        tdee = bmr * ACTIVITY_FACTORS.get(activity_level, 1.55)

        calorie_factor = sum(GOAL_RULES.get(goal, GOAL_RULES["balanced_diet"])["calorie_factor"] for goal in health_goals) / max(len(health_goals), 1)
        protein_ratio = max(GOAL_RULES.get(goal, GOAL_RULES["balanced_diet"])["protein_ratio"] for goal in health_goals)
        carb_ratio = min(GOAL_RULES.get(goal, GOAL_RULES["balanced_diet"])["carb_ratio"] for goal in health_goals)
        fat_ratio = max(0.2, 1 - protein_ratio - carb_ratio)

        calorie_target = round(tdee * calorie_factor)
        targets = {
            "calories": calorie_target,
            "protein_g": round((calorie_target * protein_ratio) / 4),
            "carbs_g": round((calorie_target * carb_ratio) / 4),
            "fat_g": round((calorie_target * fat_ratio) / 9),
            "fiber_g": 25 if gender.lower() == "female" else 35,
            "water_l": 2.2 if gender.lower() == "female" else 3.0,
        }

        profile = {
            "user_id": user_id,
            "age": age,
            "weight": weight,
            "height": height,
            "gender": gender,
            "activity_level": activity_level,
            "health_goals": health_goals,
            "dietary_restrictions": payload.get("dietary_restrictions", []),
            "allergies": payload.get("allergies", []),
            "health_conditions": payload.get("health_conditions", []),
            "cuisine_preferences": payload.get("cuisine_preferences", ["indian"]),
            "budget_preference": payload.get("budget_preference", "medium"),
            "max_prep_time": int(payload.get("max_prep_time", 30)),
            "metrics": {
                "bmi": round(bmi, 1),
                "bmi_category": self._bmi_category(bmi),
                "bmr": round(bmr),
                "tdee": round(tdee),
            },
            "targets": targets,
            "twin_summary": self._build_twin_summary(health_goals, targets),
        }
        self.profiles[user_id] = profile
        self.history.setdefault(user_id, [])
        return profile

    def _bmi_category(self, bmi: float) -> str:
        if bmi < 18.5:
            return "underweight"
        if bmi < 25:
            return "normal"
        if bmi < 30:
            return "overweight"
        return "obese"

    def _build_twin_summary(self, goals: list[str], targets: dict[str, Any]) -> dict[str, Any]:
        focus_labels = [GOAL_RULES.get(goal, GOAL_RULES["balanced_diet"])["label"] for goal in goals]
        principles = [GOAL_RULES.get(goal, GOAL_RULES["balanced_diet"])["reason"] for goal in goals]
        return {
            "focus": focus_labels,
            "principles": principles,
            "headline": f"Aim for about {targets['calories']} kcal with {targets['protein_g']}g protein and {targets['fiber_g']}g fiber daily.",
        }

    def get_profile(self, user_id: str) -> dict[str, Any]:
        return self.profiles.get(user_id) or self.create_or_update_profile({"user_id": user_id})

    def lookup_food(self, query: str, user_id: str | None = None, top_k: int = 5) -> dict[str, Any]:
        profile = self.get_profile(user_id or "guest_123")
        candidates = self._lookup_food_candidates(query, top_k=top_k)
        return {
            "query": query,
            "results": candidates,
            "profile_context": {
                "health_goals": profile["health_goals"],
                "dietary_restrictions": profile["dietary_restrictions"],
            },
        }

    def compare_foods(self, first_query: str, second_query: str, user_id: str | None = None) -> dict[str, Any]:
        profile = self.get_profile(user_id or "guest_123")
        first = self._lookup_food_candidates(first_query, top_k=1)
        second = self._lookup_food_candidates(second_query, top_k=1)
        if not first or not second:
            return {
                "comparison": None,
                "message": "Could not find both foods clearly in the dataset. Try more specific names.",
            }

        first_food = first[0]
        second_food = second[0]
        metrics = ["calories", "protein_g", "carbs_g", "fat_g", "fiber_g", "calcium_mg", "iron_mg", "potassium_mg"]
        differences = []
        for metric in metrics:
            first_value = float(first_food.get(metric, 0) or 0)
            second_value = float(second_food.get(metric, 0) or 0)
            if first_value == second_value:
                winner = "tie"
            else:
                winner = first_food["food_name"] if first_value > second_value else second_food["food_name"]
            differences.append(
                {
                    "metric": metric,
                    "first_value": round(first_value, 2),
                    "second_value": round(second_value, 2),
                    "winner": winner,
                }
            )

        summary = self._comparison_summary(first_food, second_food, profile)
        return {
            "comparison": {
                "first_food": first_food,
                "second_food": second_food,
                "differences": differences,
                "summary": summary,
            }
        }

    def _lookup_food_candidates(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        normalized_query = normalize_text(query)
        query_tokens = set(tokenize(query))
        scored = []
        for _, row in self.foods.iterrows():
            name_tokens = set(tokenize(row["food_name"]))
            search_text = row["search_text"]
            overlap = len(query_tokens.intersection(name_tokens))
            coverage = overlap / max(len(query_tokens), 1)
            exact_bonus = 40 if normalized_query and normalized_query == search_text else 0
            starts_bonus = 22 if normalized_query and search_text.startswith(normalized_query) else 0
            phrase_bonus = 16 if normalized_query and normalized_query in search_text else 0
            token_bonus = overlap * 8
            coverage_bonus = coverage * 10
            partial_bonus = 2 if query_tokens and any(token in search_text for token in query_tokens) else 0
            if exact_bonus == 0 and starts_bonus == 0 and phrase_bonus == 0 and overlap == 0 and partial_bonus == 0:
                continue
            score = exact_bonus + starts_bonus + phrase_bonus + token_bonus + coverage_bonus + partial_bonus + float(row.get("nutrition_density", 0))
            scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = []
        for score, row in scored[:top_k]:
            results.append(
                {
                    "food_name": row["food_name"],
                    "serving_unit": row.get("servings_unit") or "100 g",
                    "calories": round(float(row.get("serving_calories", 0) or 0), 1),
                    "protein_g": round(float(row.get("serving_protein_g", 0) or 0), 1),
                    "carbs_g": round(float(row.get("serving_carbs_g", 0) or 0), 1),
                    "fat_g": round(float(row.get("serving_fat_g", 0) or 0), 1),
                    "fiber_g": round(float(row.get("serving_fiber_g", 0) or 0), 1),
                    "calcium_mg": round(float(row.get("unit_serving_calcium_mg", row.get("calcium_mg", 0)) or 0), 1),
                    "iron_mg": round(float(row.get("unit_serving_iron_mg", row.get("iron_mg", 0)) or 0), 1),
                    "potassium_mg": round(float(row.get("unit_serving_potassium_mg", row.get("potassium_mg", 0)) or 0), 1),
                    "free_sugar_g": round(float(row.get("unit_serving_freesugar_g", row.get("freesugar_g", 0)) or 0), 1),
                    "search_score": round(score, 2),
                    "category": row.get("category", "general"),
                    "cuisine_tags": row.get("cuisine_tags", []),
                    "explanation": self._food_detail_explanation(row.to_dict()),
                }
            )
        return results

    def _food_detail_explanation(self, food: dict[str, Any]) -> str:
        protein = float(food.get("serving_protein_g", 0) or 0)
        fiber = float(food.get("serving_fiber_g", 0) or 0)
        calories = float(food.get("serving_calories", 0) or 0)
        calcium = float(food.get("unit_serving_calcium_mg", food.get("calcium_mg", 0)) or 0)
        iron = float(food.get("unit_serving_iron_mg", food.get("iron_mg", 0)) or 0)

        parts = [f"This serving gives about {round(calories, 1)} kcal."]
        if protein >= 15:
            parts.append("It is a strong protein source.")
        elif protein >= 8:
            parts.append("It contributes a useful amount of protein.")
        if fiber >= 4:
            parts.append("Fiber content is meaningfully supportive.")
        if calcium >= 120:
            parts.append("It is also helpful for calcium intake.")
        if iron >= 2:
            parts.append("It contributes useful iron.")
        return " ".join(parts)

    def _comparison_summary(self, first_food: dict[str, Any], second_food: dict[str, Any], profile: dict[str, Any]) -> list[str]:
        summary = []
        if first_food["protein_g"] > second_food["protein_g"]:
            summary.append(f"{first_food['food_name']} is better for protein.")
        elif second_food["protein_g"] > first_food["protein_g"]:
            summary.append(f"{second_food['food_name']} is better for protein.")
        if first_food["fiber_g"] > second_food["fiber_g"]:
            summary.append(f"{first_food['food_name']} gives more fiber.")
        elif second_food["fiber_g"] > first_food["fiber_g"]:
            summary.append(f"{second_food['food_name']} gives more fiber.")
        if first_food["calories"] < second_food["calories"]:
            summary.append(f"{first_food['food_name']} is lighter in calories.")
        elif second_food["calories"] < first_food["calories"]:
            summary.append(f"{second_food['food_name']} is lighter in calories.")

        goals = profile.get("health_goals", [])
        if "muscle_gain" in goals:
            better = first_food["food_name"] if first_food["protein_g"] >= second_food["protein_g"] else second_food["food_name"]
            summary.append(f"For muscle gain, {better} is the stronger fit.")
        if "weight_loss" in goals:
            better = first_food["food_name"] if first_food["calories"] <= second_food["calories"] else second_food["food_name"]
            summary.append(f"For weight loss, {better} is the lighter choice.")
        return summary

    def _build_intent_search_insight(self, query: str, intent: dict[str, Any], recommendations: list[dict[str, Any]]) -> str:
        if not recommendations:
            return "No clear dataset matches were found for this search query."

        nutrient_focus = intent.get("nutrient_focus") or ["balanced nutrition"]
        top_items = recommendations[:3]
        parts = [
            f"Search query: {query}.",
            f"Detected intent: {intent['meal_type']} with focus on {', '.join(nutrient_focus)}.",
            f"Top dataset matches are {', '.join(item['food_name'] for item in top_items)}.",
        ]
        for item in top_items:
            parts.append(
                f"{item['food_name']} has {item['calories']} kcal, {item['protein_g']} g protein, and {item['fiber_g']} g fiber per serving."
            )
        if intent.get("goals"):
            parts.append(f"These choices support goals such as {', '.join(intent['goals'])}.")
        return " ".join(parts)

    def _build_repair_explanation(self, meal_totals: dict[str, Any], issues: list[str], upgrades: list[dict[str, str]], matched_foods: list[dict[str, Any]]) -> str:
        parts = [
            f"Detected {len(matched_foods)} matching dataset foods in the meal.",
            f"Meal totals are {meal_totals['calories']} kcal, {meal_totals['protein_g']} g protein, {meal_totals['carbs_g']} g carbs, {meal_totals['fat_g']} g fat, and {meal_totals['fiber_g']} g fiber.",
        ]
        if issues:
            parts.append("Key imbalance flags: " + "; ".join(issues) + ".")
        if upgrades:
            parts.append(
                "Recommended dataset-backed upgrades include: " + "; ".join(upgrade['suggestion'] for upgrade in upgrades[:3]) + "."
            )
        if matched_foods:
            parts.append(
                "Most prominent meal items were " + ", ".join(food['food_name'] for food in matched_foods[:3]) + "."
            )
        return " ".join(parts)

    def _build_recommendation_explanation(self, recommendations: list[dict[str, Any]], profile: dict[str, Any], meal_type: str, query: str | None) -> str:
        if not recommendations:
            return "No dataset-backed recommendations were found for this request."

        parts = [
            f"This recommendation list comes from the nutrition dataset for {meal_type}.",
            f"Query focus: {query or 'general nutrition'}.",
        ]
        goal_text = ", ".join(profile.get("health_goals", []))
        if goal_text:
            parts.append(f"Profile goals: {goal_text}.")
        top_items = recommendations[:3]
        for item in top_items:
            parts.append(
                f"{item['food_name']} delivers {item['protein_g']} g protein, {item['fiber_g']} g fiber, and {item['calories']} kcal per serving."
            )
        return " ".join(parts)

    def _build_plan_explanation(self, plan: dict[str, Any]) -> str:
        parts = [
            f"This day plan is built from dataset foods to deliver about {plan['daily_estimate']['calories']} kcal, {plan['daily_estimate']['protein_g']} g protein, and {plan['daily_estimate']['fiber_g']} g fiber.",
        ]
        for meal_type, meal in plan['meals'].items():
            if meal['items']:
                item_names = ", ".join(item['food_name'] for item in meal['items'][:2])
                parts.append(
                    f"{meal_type.title()} includes {item_names} for roughly {meal['target_calories']} kcal."
                )
        return " ".join(parts)

    def _build_indian_lens_explanation(self, query: str, lens: dict[str, Any], recommended_foods: list[dict[str, Any]], smart_swaps: list[dict[str, str]]) -> str:
        parts = [
            f"Query: {query}.",
            f"Detected Indian style tags: {', '.join(lens.get('detected_styles', []))}.",
        ]
        if recommended_foods:
            parts.append(
                "Top dataset recommendations are " + ", ".join(food['food_name'] for food in recommended_foods[:3]) + "."
            )
        if smart_swaps:
            parts.append(
                "Smart swaps include " + "; ".join(f"{swap['from']} → {swap['to']}" for swap in smart_swaps[:3]) + "."
            )
        return " ".join(parts)

    def search_foods(self, query: str, user_id: str | None = None, top_k: int = 8) -> dict[str, Any]:
        profile = self.get_profile(user_id or "guest_123")
        intent = self._parse_intent(query)
        recommendations = self._recommend_foods(
            profile,
            query=query,
            meal_type=intent["meal_type"],
            top_k=top_k,
            query_intent=intent,
        )
        indian_lens = self._indian_lens(query, recommendations)
        return {
            "query": query,
            "intent": intent,
            "results": recommendations,
            "indian_lens": indian_lens,
            "generated_explanation": self._build_intent_search_insight(query, intent, recommendations),
        }

    def _parse_intent(self, query: str) -> dict[str, Any]:
        q = normalize_text(query)
        nutrients = [nutrient for nutrient in ["protein", "fiber", "iron", "calcium", "potassium", "carb", "fat"] if nutrient in q]
        goals = [goal for goal in GOAL_RULES if goal.replace("_", " ") in q]
        meal_type = "general"
        for slot in ["breakfast", "lunch", "dinner", "snacks"]:
            if slot.rstrip("s") in q or slot in q:
                meal_type = slot
                break
        restrictions = [diet for diet in ["vegan", "vegetarian", "jain", "gluten_free", "dairy_free"] if diet.replace("_", " ") in q]
        non_vegetarian = bool(re.search(r"\b(non[\s-]?vegetarian|nonveg|non veg|non-veg)\b", q))
        is_high_protein = "high protein" in q or "protein rich" in q
        calorie_target = None
        match = re.search(r"(?:over|above|more than|at least)\s+(\d{2,4})\s*(?:kcal|calories|cal)?", q)
        if match:
            calorie_target = int(match.group(1))
        return {
            "nutrient_focus": nutrients,
            "goals": goals,
            "meal_type": meal_type,
            "restrictions": restrictions,
            "non_vegetarian": non_vegetarian,
            "is_high_protein": is_high_protein,
            "calorie_target": calorie_target,
        }

    def get_personalized_recommendations(
        self,
        user_id: str,
        meal_type: str = "general",
        query: str | None = None,
        top_k: int = 6,
    ) -> dict[str, Any]:
        profile = self.get_profile(user_id)
        intent = self._parse_intent(query or "")
        recommendations = self._recommend_foods(
            profile,
            meal_type=meal_type,
            query=query or "",
            top_k=top_k,
            query_intent=intent,
        )
        payload = {
            "profile_snapshot": {
                "health_goals": profile["health_goals"],
                "dietary_restrictions": profile["dietary_restrictions"],
                "budget_preference": profile["budget_preference"],
                "max_prep_time": profile["max_prep_time"],
            },
            "meal_type": meal_type,
            "summary": f"{meal_type.title()} suggestions tuned for {', '.join(profile['health_goals'])}.",
            "recommendations": recommendations,
            "generated_explanation": self._build_recommendation_explanation(recommendations, profile, meal_type, query),
        }
        self.history[user_id].append({"type": "recommendation", "payload": payload})
        self.history[user_id] = self.history[user_id][-20:]
        return payload

    def _recommend_foods(
        self,
        profile: dict[str, Any],
        *,
        meal_type: str = "general",
        query: str = "",
        top_k: int = 6,
        pantry_items: list[str] | None = None,
        budget_override: str | None = None,
        max_prep_time: int | None = None,
        query_intent: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        pantry_items = pantry_items or []
        budget_preference = budget_override or profile.get("budget_preference", "medium")
        prep_limit = max_prep_time or profile.get("max_prep_time", 30)
        query_tokens = set(tokenize(query))
        pantry_tokens = {normalize_text(item) for item in pantry_items if item}

        foods = self.foods.copy()
        foods = self._apply_profile_filters(foods, profile)
        if meal_type != "general":
            foods = foods[foods["meal_slots"].map(lambda slots: meal_type in slots)]
        if query_intent is not None:
            foods = self._apply_query_filters(foods, query_intent)
        if budget_preference == "low":
            foods = foods[foods["budget_tier"].isin(["low", "medium"])]
        if prep_limit:
            foods = foods[foods["prep_time_minutes"] <= prep_limit]

        scored: list[dict[str, Any]] = []
        for _, row in foods.iterrows():
            food = row.to_dict()
            score = float(food.get("nutrition_density", 0))
            reasons: list[str] = []

            if query_tokens:
                overlap = len(query_tokens.intersection(set(tokenize(food["food_name"]))))
                score += overlap * 4
                if overlap:
                    reasons.append("Matches your search terms directly.")

            if query_intent and query_intent.get("is_high_protein") and float(food.get("serving_protein_g", 0) or 0) >= 15:
                score += 2
                reasons.append("Strong protein source for your request.")

            if query_intent and query_intent.get("non_vegetarian"):
                if self._food_is_non_veg(row):
                    score += 4
                    reasons.append("Matches your non-vegetarian preference.")
                else:
                    score -= 4

            if query_intent and query_intent.get("calorie_target"):
                target = query_intent["calorie_target"]
                calories = float(food.get("serving_calories", 0) or 0)
                if calories >= target:
                    score += 5
                    reasons.append(f"Meets the requested {target}+ calorie target.")
                elif calories >= target * 0.8:
                    score += 1
                    reasons.append(f"Approaches the requested calorie target.")
                else:
                    score -= 1

            if pantry_tokens and any(token in food["search_text"] for token in pantry_tokens):
                score += 3
                reasons.append("Fits ingredients you already have.")

            for goal in profile["health_goals"]:
                goal_score, goal_reasons = self._score_for_goal(food, goal)
                score += goal_score
                reasons.extend(goal_reasons)

            if meal_type in food["meal_slots"]:
                score += 1.5
                reasons.append(f"Works well for {meal_type}.")

            cuisine_match = set(profile.get("cuisine_preferences", [])).intersection(set(food["cuisine_tags"]))
            if cuisine_match:
                score += 2
                reasons.append(f"Aligned with your cuisine preference: {', '.join(sorted(cuisine_match))}.")

            score += self._micronutrient_bonus(food, query)

            scored.append(
                {
                    "food_name": food["food_name"],
                    "category": food["category"],
                    "serving_unit": food.get("servings_unit") or "100 g",
                    "calories": round(float(food.get("serving_calories", 0) or 0), 1),
                    "protein_g": round(float(food.get("serving_protein_g", 0) or 0), 1),
                    "carbs_g": round(float(food.get("serving_carbs_g", 0) or 0), 1),
                    "fat_g": round(float(food.get("serving_fat_g", 0) or 0), 1),
                    "fiber_g": round(float(food.get("serving_fiber_g", 0) or 0), 1),
                    "calcium_mg": round(float(food.get("unit_serving_calcium_mg", food.get("calcium_mg", 0)) or 0), 1),
                    "iron_mg": round(float(food.get("unit_serving_iron_mg", food.get("iron_mg", 0)) or 0), 1),
                    "potassium_mg": round(float(food.get("unit_serving_potassium_mg", food.get("potassium_mg", 0)) or 0), 1),
                    "prep_time_minutes": int(food["prep_time_minutes"]),
                    "budget_tier": food["budget_tier"],
                    "meal_slots": food["meal_slots"],
                    "cuisine_tags": food["cuisine_tags"],
                    "score": round(score, 2),
                    "why_this_food": sorted(set(reasons))[:4],
                    "healthier_swap": self._healthier_swap(food["food_name"], food["category"]),
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def _apply_profile_filters(self, foods: pd.DataFrame, profile: dict[str, Any]) -> pd.DataFrame:
        filtered = foods.copy()
        restrictions = [normalize_text(item) for item in profile.get("dietary_restrictions", [])]
        allergies = [normalize_text(item) for item in profile.get("allergies", [])]

        if "vegetarian" in restrictions:
            filtered = filtered[~filtered["search_text"].str.contains("chicken|fish|mutton|beef|meat|egg", na=False)]
        if "vegan" in restrictions:
            filtered = filtered[~filtered["search_text"].str.contains("chicken|fish|mutton|beef|meat|paneer|milk|curd|ghee|egg", na=False)]
        if "jain" in restrictions:
            filtered = filtered[~filtered["search_text"].str.contains("onion|garlic|potato", na=False)]
        if "gluten free" in restrictions or "gluten_free" in restrictions:
            filtered = filtered[~filtered["search_text"].str.contains("bread|naan|wheat|pasta", na=False)]
        if "dairy free" in restrictions or "dairy_free" in restrictions:
            filtered = filtered[~filtered["search_text"].str.contains("milk|paneer|curd|cheese|ghee", na=False)]

        allergy_patterns = {
            "nuts": "almond|cashew|walnut|peanut|nut",
            "dairy": "milk|paneer|curd|cheese|ghee",
            "eggs": "egg",
            "soy": "soy|soya|tofu",
            "wheat": "wheat|bread|naan|roti|pasta",
            "fish": "fish|salmon|tuna",
        }
        for allergy in allergies:
            pattern = allergy_patterns.get(allergy)
            if pattern:
                filtered = filtered[~filtered["search_text"].str.contains(pattern, na=False)]
        return filtered

    def _food_is_non_veg(self, food: pd.Series) -> bool:
        text = normalize_text(food["food_name"])
        nonveg_keywords = ["chicken", "fish", "mutton", "beef", "pork", "egg", "shrimp", "prawn", "lamb", "goat", "meat", "seafood", "kebab", "tandoori", "biriyani", "biryani"]
        return any(keyword in text for keyword in nonveg_keywords)

    def _food_is_powder_or_spice(self, food: pd.Series) -> bool:
        text = normalize_text(food["food_name"])
        return any(keyword in text for keyword in ["powder", "masala", "spice", "seasoning", "mix"])

    def _apply_query_filters(self, foods: pd.DataFrame, intent: dict[str, Any]) -> pd.DataFrame:
        filtered = foods.copy()
        if intent.get("non_vegetarian"):
            filtered = filtered[filtered.apply(self._food_is_non_veg, axis=1)]
        if intent.get("calorie_target"):
            threshold = intent["calorie_target"]
            filtered = filtered[filtered["serving_calories"] >= max(threshold * 0.5, 80)]
        if intent.get("meal_type") == "lunch" and intent.get("calorie_target"):
            filtered = filtered[~filtered.apply(self._food_is_powder_or_spice, axis=1)]
        return filtered

    def _score_for_goal(self, food: dict[str, Any], goal: str) -> tuple[float, list[str]]:
        calories = float(food.get("serving_calories", 0) or 0)
        protein = float(food.get("serving_protein_g", 0) or 0)
        fiber = float(food.get("serving_fiber_g", 0) or 0)
        carbs = float(food.get("serving_carbs_g", 0) or 0)
        potassium = float(food.get("unit_serving_potassium_mg", 0) or 0)
        score = 0.0
        reasons: list[str] = []

        if goal == "weight_loss":
            if calories <= 220:
                score += 2.5
                reasons.append("Keeps calories moderate for weight loss.")
            if protein >= 12:
                score += 2
                reasons.append("Provides useful protein for satiety.")
            if fiber >= 4:
                score += 1.5
                reasons.append("Adds fiber to help fullness.")
        elif goal == "muscle_gain":
            if protein >= 18:
                score += 3
                reasons.append("High protein helps muscle recovery.")
            if carbs >= 15:
                score += 1.5
                reasons.append("Provides training-friendly carbohydrates.")
            if calories >= 180:
                score += 1
        elif goal == "diabetic_friendly":
            if fiber >= 4:
                score += 2
                reasons.append("Higher fiber supports steadier glucose response.")
            if protein >= 10:
                score += 1.5
                reasons.append("Protein improves meal balance.")
            if carbs <= 25:
                score += 1.5
        elif goal == "heart_health":
            if potassium >= 250:
                score += 2
                reasons.append("Provides useful potassium for heart-friendly eating.")
            if fiber >= 4:
                score += 1.5
            if calories <= 250:
                score += 1
        else:
            if protein >= 10:
                score += 1.5
            if fiber >= 4:
                score += 1
        return score, reasons

    def _micronutrient_bonus(self, food: dict[str, Any], query: str) -> float:
        q = normalize_text(query)
        bonus = 0.0
        if "iron" in q and float(food.get("unit_serving_iron_mg", food.get("iron_mg", 0)) or 0) >= 2:
            bonus += 2
        if "calcium" in q and float(food.get("unit_serving_calcium_mg", food.get("calcium_mg", 0)) or 0) >= 120:
            bonus += 2
        if "potassium" in q and float(food.get("unit_serving_potassium_mg", food.get("potassium_mg", 0)) or 0) >= 250:
            bonus += 2
        if "protein" in q and float(food.get("serving_protein_g", 0) or 0) >= 15:
            bonus += 2
        if "fiber" in q and float(food.get("serving_fiber_g", 0) or 0) >= 4:
            bonus += 2
        return bonus

    def _healthier_swap(self, food_name: str, category: str) -> str | None:
        name = normalize_text(food_name)
        foods = self.foods[self.foods["category"] == category]
        if foods.empty:
            return None
        if any(keyword in name for keyword in ["samosa", "kachori", "jalebi", "biscuit", "biryani", "paratha"]):
            better = foods.sort_values(["nutrition_density", "serving_calories"], ascending=[False, True]).head(1)
            if not better.empty:
                candidate = better.iloc[0]["food_name"]
                if candidate != food_name:
                    return str(candidate)
        return None

    def repair_meal(self, user_id: str, meal_text: str) -> dict[str, Any]:
        profile = self.get_profile(user_id)
        matched_foods = self._extract_foods_from_text(meal_text)
        meal_totals = {
            "calories": round(sum(item["calories"] for item in matched_foods), 1),
            "protein_g": round(sum(item["protein_g"] for item in matched_foods), 1),
            "carbs_g": round(sum(item["carbs_g"] for item in matched_foods), 1),
            "fat_g": round(sum(item["fat_g"] for item in matched_foods), 1),
            "fiber_g": round(sum(item["fiber_g"] for item in matched_foods), 1),
        }
        total_macro_calories = meal_totals["protein_g"] * 4 + meal_totals["carbs_g"] * 4 + meal_totals["fat_g"] * 9
        macro_ratios = {
            "protein_pct": round((meal_totals["protein_g"] * 4 / total_macro_calories) * 100, 1) if total_macro_calories else 0,
            "carbs_pct": round((meal_totals["carbs_g"] * 4 / total_macro_calories) * 100, 1) if total_macro_calories else 0,
            "fat_pct": round((meal_totals["fat_g"] * 9 / total_macro_calories) * 100, 1) if total_macro_calories else 0,
        }
        issues = self._meal_issues(meal_totals, macro_ratios)
        upgrades = self._meal_upgrades(profile, meal_totals)
        response = {
            "meal_text": meal_text,
            "matched_foods": matched_foods,
            "meal_totals": meal_totals,
            "macro_ratios": macro_ratios,
            "assessment": "Balanced enough" if not issues else "; ".join(issues),
            "issues": issues,
            "upgrades": upgrades,
            "indian_lens": self._indian_lens(meal_text, matched_foods),
            "generated_explanation": self._build_repair_explanation(meal_totals, issues, upgrades, matched_foods),
        }
        self.history[user_id].append({"type": "meal_repair", "payload": response})
        self.history[user_id] = self.history[user_id][-20:]
        return response

    def _extract_foods_from_text(self, meal_text: str) -> list[dict[str, Any]]:
        q = normalize_text(meal_text)
        foods: list[dict[str, Any]] = []
        for _, row in self.foods.iterrows():
            name = row["search_text"]
            tokens = name.split()
            if name and name in q:
                foods.append(self._food_summary(row))
            elif len(tokens) >= 2 and len(set(tokens).intersection(set(q.split()))) >= min(2, len(tokens)):
                foods.append(self._food_summary(row))
        foods.sort(key=lambda item: item["calories"], reverse=True)
        return foods[:6]

    def _food_summary(self, row: pd.Series) -> dict[str, Any]:
        return {
            "food_name": row["food_name"],
            "calories": round(float(row.get("serving_calories", 0) or 0), 1),
            "protein_g": round(float(row.get("serving_protein_g", 0) or 0), 1),
            "carbs_g": round(float(row.get("serving_carbs_g", 0) or 0), 1),
            "fat_g": round(float(row.get("serving_fat_g", 0) or 0), 1),
            "fiber_g": round(float(row.get("serving_fiber_g", 0) or 0), 1),
            "serving_unit": row.get("servings_unit") or "100 g",
            "cuisine_tags": row.get("cuisine_tags", []),
        }

    def _meal_issues(self, totals: dict[str, float], ratios: dict[str, float]) -> list[str]:
        issues: list[str] = []
        if totals["protein_g"] < 18:
            issues.append("Protein looks low for a satisfying meal.")
        if totals["fiber_g"] < 6:
            issues.append("Fiber is on the lower side.")
        if ratios["carbs_pct"] > 60:
            issues.append("The meal leans heavily on carbohydrates.")
        if ratios["fat_pct"] > 40:
            issues.append("Fat contribution is a bit high.")
        if totals["calories"] > 800:
            issues.append("Calories are high for a single meal.")
        return issues

    def _meal_upgrades(self, profile: dict[str, Any], totals: dict[str, float]) -> list[dict[str, str]]:
        upgrades: list[dict[str, str]] = []
        if totals["protein_g"] < 18:
            protein_pick = self._recommend_foods(profile, query="high protein", top_k=1)
            if protein_pick:
                upgrades.append({
                    "type": "protein_fix",
                    "suggestion": f"Add {protein_pick[0]['food_name']} to lift protein without rebuilding the meal.",
                })
        if totals["fiber_g"] < 6:
            fiber_pick = self._recommend_foods(profile, query="high fiber", top_k=1)
            if fiber_pick:
                upgrades.append({
                    "type": "fiber_fix",
                    "suggestion": f"Pair it with {fiber_pick[0]['food_name']} for more fiber and fullness.",
                })
        if totals["calories"] > 800:
            upgrades.append({
                "type": "portion_fix",
                "suggestion": "Trim one energy-dense item and replace it with a dal, salad, or fruit-based side.",
            })
        upgrades.append({
            "type": "diabetic_friendly",
            "suggestion": "For a steadier glucose response, combine carbs with a protein-rich side and a fiber-rich vegetable.",
        })
        return upgrades[:4]

    def generate_smart_plan(self, user_id: str, constraints: dict[str, Any]) -> dict[str, Any]:
        profile = self.get_profile(user_id)
        pantry_items = constraints.get("pantry_items", [])
        budget = constraints.get("budget_preference") or profile.get("budget_preference", "medium")
        prep_limit = int(constraints.get("max_prep_time", profile.get("max_prep_time", 30)))
        plan: dict[str, Any] = {"meals": {}, "daily_estimate": {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": 0}}

        for meal_type, fraction in MEAL_DISTRIBUTION.items():
            meal_budget = round(profile["targets"]["calories"] * fraction)
            picks = self._recommend_foods(
                profile,
                meal_type=meal_type if meal_type != "snacks" else "snacks",
                query=constraints.get("query", ""),
                top_k=3,
                pantry_items=pantry_items,
                budget_override=budget,
                max_prep_time=prep_limit,
            )
            chosen = picks[:2] if meal_type != "snacks" else picks[:1]
            plan["meals"][meal_type] = {
                "target_calories": meal_budget,
                "items": chosen,
                "notes": f"Built for {budget} budget and max {prep_limit} min prep.",
            }
            for item in chosen:
                plan["daily_estimate"]["calories"] += item["calories"]
                plan["daily_estimate"]["protein_g"] += item["protein_g"]
                plan["daily_estimate"]["carbs_g"] += item["carbs_g"]
                plan["daily_estimate"]["fat_g"] += item["fat_g"]
                plan["daily_estimate"]["fiber_g"] += item["fiber_g"]

        for key in plan["daily_estimate"]:
            plan["daily_estimate"][key] = round(plan["daily_estimate"][key], 1)

        plan["target_snapshot"] = profile["targets"]
        plan["constraint_summary"] = {
            "budget_preference": budget,
            "max_prep_time": prep_limit,
            "pantry_items": pantry_items,
        }
        plan["generated_explanation"] = self._build_plan_explanation(plan)
        self.history[user_id].append({"type": "smart_plan", "payload": plan})
        self.history[user_id] = self.history[user_id][-20:]
        return plan

    def indian_food_intelligence(self, user_id: str, query: str) -> dict[str, Any]:
        profile = self.get_profile(user_id)
        results = self._recommend_foods(profile, query=query, top_k=5)
        lens = self._indian_lens(query, results)
        swaps = []
        for item in results[:3]:
            if item.get("healthier_swap"):
                swaps.append({
                    "from": item["food_name"],
                    "to": item["healthier_swap"],
                    "why": "Higher nutrition density or lighter calorie profile within a similar Indian eating context.",
                })
        return {
            "query": query,
            "lens": lens,
            "smart_swaps": swaps,
            "recommended_foods": results,
            "generated_explanation": self._build_indian_lens_explanation(query, lens, results, swaps),
        }

    def _indian_lens(self, query: str, foods: list[dict[str, Any]]) -> dict[str, Any]:
        text = normalize_text(query)
        query_detected: list[str] = []
        for cuisine, keywords in INDIAN_CUISINE_RULES.items():
            if any(keyword in text for keyword in keywords):
                query_detected.append(cuisine)
        all_tags: list[str] = []
        for food in foods:
            all_tags.extend(food.get("cuisine_tags", []))
        detected = sorted(set(query_detected or all_tags))
        notes: list[str] = []
        if "street_food" in detected:
            notes.append("Street-food style dishes often benefit from adding protein and fiber on the side.")
        if "north_indian" in detected:
            notes.append("North Indian meals are easier to balance when rotis or rice are paired with dal, paneer, or sabzi.")
        if "south_indian" in detected:
            notes.append("South Indian breakfasts become more complete when paired with sambar, curd, or an egg/protein side.")
        if "festival" in detected:
            notes.append("Festival foods can stay enjoyable with smaller portions plus a lighter protein-forward meal later in the day.")
        return {
            "detected_styles": detected or ["indian"],
            "notes": notes or ["Indian meals often improve most through better pairing, not complete replacement."],
        }

    def get_history(self, user_id: str) -> list[dict[str, Any]]:
        self.get_profile(user_id)
        return self.history.get(user_id, [])


@lru_cache(maxsize=1)
def get_coach() -> NutriWiseCoach:
    return NutriWiseCoach()
