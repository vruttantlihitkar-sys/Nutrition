import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_allowed_origins, settings
from backend.intelligence import get_coach
from backend.schemas import (
    AnalysisRequest,
    EducationRequest,
    FoodCompareRequest,
    FoodLookupRequest,
    IndianFoodRequest,
    MealPlanRequest,
    MealRepairRequest,
    PersonalizedRecommendationRequest,
    ProfileRequest,
    QueryRequest,
    QueryResponse,
    RecommendationRequest,
    SearchRequest,
    SmartPlanRequest,
    SettingsResponse,
)
from backend.services import generate_grounded_nutrition_text, run_query


def _build_discover_context(query: str, results: list[dict[str, Any]]) -> list[str]:
    blocks = [
        f"User query: {query}",
        "Top dataset matches:",
    ]
    for item in results[:3]:
        blocks.append(
            f"{item['food_name']}: {item['calories']} kcal, {item['protein_g']} g protein, {item['carbs_g']} g carbs, {item['fat_g']} g fat, {item['fiber_g']} g fiber per {item['serving_unit']}."
        )
    return blocks


def _build_repair_context(meal_text: str, result: dict[str, Any]) -> list[str]:
    blocks = [
        f"Meal description: {meal_text}",
        f"Meal totals: {result['meal_totals']['calories']} kcal, {result['meal_totals']['protein_g']} g protein, {result['meal_totals']['carbs_g']} g carbs, {result['meal_totals']['fat_g']} g fat, {result['meal_totals']['fiber_g']} g fiber.",
        "Detected foods from dataset:",
    ]
    for food in result.get('matched_foods', [])[:5]:
        blocks.append(
            f"{food['food_name']}: {food['calories']} kcal, {food['protein_g']} g protein, {food['carbs_g']} g carbs, {food['fat_g']} g fat, {food['fiber_g']} g fiber per {food['serving_unit']}.",
        )
    if result.get('issues'):
        blocks.append("Issues found: " + "; ".join(result['issues']))
    if result.get('upgrades'):
        blocks.append("Suggested improvements: " + "; ".join(upgrade['suggestion'] for upgrade in result['upgrades'][:3]))
    return blocks


def _build_recommendation_context(query: str | None, meal_type: str, recommendations: list[dict[str, Any]]) -> list[str]:
    blocks = [
        f"Request: personalized recommendations for {meal_type}.",
        f"User query: {query or 'general nutrition'}.",
        "Top dataset foods:",
    ]
    for item in recommendations[:3]:
        blocks.append(
            f"{item['food_name']}: {item['calories']} kcal, {item['protein_g']} g protein, {item['fiber_g']} g fiber, {item['carbs_g']} g carbs per {item['serving_unit']}."
        )
    return blocks


def _build_plan_context(plan: dict[str, Any]) -> list[str]:
    blocks = [
        f"Daily estimate: {plan['daily_estimate']['calories']} kcal, {plan['daily_estimate']['protein_g']} g protein, {plan['daily_estimate']['fiber_g']} g fiber.",
        "Meals included:",
    ]
    for meal_type, meal in plan['meals'].items():
        if meal['items']:
            blocks.append(
                f"{meal_type.title()}: {', '.join(item['food_name'] for item in meal['items'][:3])} - target {meal['target_calories']} kcal."
            )
    return blocks


def _build_indian_context(query: str, lens: dict[str, Any], recommended_foods: list[dict[str, Any]], smart_swaps: list[dict[str, str]]) -> list[str]:
    blocks = [
        f"Query: {query}",
        f"Detected Indian styles: {', '.join(lens.get('detected_styles', []))}.",
        "Recommended dataset foods:",
    ]
    for food in recommended_foods[:3]:
        blocks.append(
            f"{food['food_name']}: {food['calories']} kcal, {food['protein_g']} g protein, {food['fiber_g']} g fiber, categorized as {food.get('category', 'general')}."
        )
    if smart_swaps:
        blocks.append(
            "Smart swaps: " + "; ".join(f"{swap['from']} → {swap['to']}" for swap in smart_swaps[:3])
        )
    return blocks


app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "The server hit an unexpected error while processing the request.",
            "error": str(exc),
        },
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    return SettingsResponse(
        app_name=settings.app_name,
        default_use_lmstudio=settings.default_use_lmstudio,
        lmstudio_url=settings.lmstudio_url,
        lmstudio_model=settings.lmstudio_model,
        has_openai_key=bool(settings.openai_api_key),
        dataset_path=settings.dataset_path,
    )


@app.post("/query", response_model=QueryResponse)
def query_endpoint(payload: QueryRequest) -> QueryResponse:
    try:
        result = run_query(
            user_id=payload.user_id,
            query_text=payload.query,
            query_type=payload.query_type,
            context=payload.context,
            use_lmstudio=payload.use_lmstudio,
            openai_api_key=payload.openai_api_key,
            lmstudio_url=payload.lmstudio_url,
            lmstudio_model=payload.lmstudio_model,
        )
        return QueryResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to process query: {exc}") from exc


@app.post("/analyze", response_model=QueryResponse)
def analyze_food(payload: AnalysisRequest) -> QueryResponse:
    try:
        result = run_query(
            user_id=payload.user_id,
            query_text=payload.query,
            query_type="analysis",
            context={"goal": "analyze food nutrients"},
            use_lmstudio=payload.use_lmstudio,
            openai_api_key=payload.openai_api_key,
            lmstudio_url=payload.lmstudio_url,
            lmstudio_model=payload.lmstudio_model,
        )
        return QueryResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to analyze food: {exc}") from exc


@app.post("/meal-plan", response_model=QueryResponse)
def meal_plan(payload: MealPlanRequest) -> QueryResponse:
    try:
        result = run_query(
            user_id=payload.user_id,
            query_text=f"Create a meal plan for {payload.goal}, restrictions: {payload.restrictions}",
            query_type="meal_planning",
            context={"goal": payload.goal, "restrictions": payload.restrictions},
            use_lmstudio=payload.use_lmstudio,
            openai_api_key=payload.openai_api_key,
            lmstudio_url=payload.lmstudio_url,
            lmstudio_model=payload.lmstudio_model,
        )
        return QueryResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to generate meal plan: {exc}") from exc


@app.post("/education", response_model=QueryResponse)
def education(payload: EducationRequest) -> QueryResponse:
    try:
        result = run_query(
            user_id=payload.user_id,
            query_text=payload.question,
            query_type="education",
            context={},
            use_lmstudio=payload.use_lmstudio,
            openai_api_key=payload.openai_api_key,
            lmstudio_url=payload.lmstudio_url,
            lmstudio_model=payload.lmstudio_model,
        )
        return QueryResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to answer education query: {exc}") from exc


@app.post("/recommendations", response_model=QueryResponse)
def recommendations(payload: RecommendationRequest) -> QueryResponse:
    try:
        result = run_query(
            user_id=payload.user_id,
            query_text=f"Recommend foods for {payload.goal}",
            query_type="recommendation",
            context={"goal": payload.goal},
            use_lmstudio=payload.use_lmstudio,
            openai_api_key=payload.openai_api_key,
            lmstudio_url=payload.lmstudio_url,
            lmstudio_model=payload.lmstudio_model,
        )
        return QueryResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to generate recommendations: {exc}") from exc


@app.post("/profile")
def create_or_update_profile(payload: ProfileRequest) -> dict:
    try:
        coach = get_coach()
        return coach.create_or_update_profile(payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to save profile: {exc}") from exc


@app.get("/profile/{user_id}")
def get_profile(user_id: str) -> dict:
    try:
        return get_coach().get_profile(user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to load profile: {exc}") from exc


@app.post("/discover")
def discover_foods(payload: SearchRequest) -> dict:
    try:
        result = get_coach().search_foods(payload.query, payload.user_id, payload.top_k)
        result["generated_explanation"] = generate_grounded_nutrition_text(
            prompt=f"Explain why these top dataset matches are appropriate for the query: {payload.query}. Use only these dataset values and avoid adding unrelated information.",
            context_blocks=_build_discover_context(payload.query, result.get("results", [])),
            use_lmstudio=payload.use_lmstudio,
            openai_api_key=payload.openai_api_key,
            lmstudio_url=payload.lmstudio_url,
            lmstudio_model=payload.lmstudio_model,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to search foods: {exc}") from exc


@app.post("/recommendations/personalized")
def personalized_recommendations(payload: PersonalizedRecommendationRequest) -> dict:
    try:
        result = get_coach().get_personalized_recommendations(
            user_id=payload.user_id,
            meal_type=payload.meal_type,
            query=payload.query,
            top_k=payload.top_k,
        )
        result["generated_explanation"] = generate_grounded_nutrition_text(
            prompt=f"Explain why these recommended dataset foods are a good fit for the query: {payload.query or 'general nutrition'} and meal type: {payload.meal_type}.",
            context_blocks=_build_recommendation_context(payload.query, payload.meal_type, result.get("recommendations", [])),
            use_lmstudio=payload.use_lmstudio,
            openai_api_key=payload.openai_api_key,
            lmstudio_url=payload.lmstudio_url,
            lmstudio_model=payload.lmstudio_model,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to generate personalized recommendations: {exc}") from exc


@app.post("/meal-repair")
def repair_meal(payload: MealRepairRequest) -> dict:
    try:
        result = get_coach().repair_meal(payload.user_id, payload.meal_text)
        result["generated_explanation"] = generate_grounded_nutrition_text(
            prompt=f"Explain the meal repair suggestions based on the dataset foods identified in the user's meal. Use the meal totals and matched dataset items to support the explanation.",
            context_blocks=_build_repair_context(payload.meal_text, result),
            use_lmstudio=payload.use_lmstudio,
            openai_api_key=payload.openai_api_key,
            lmstudio_url=payload.lmstudio_url,
            lmstudio_model=payload.lmstudio_model,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to repair meal: {exc}") from exc


@app.post("/smart-plan")
def smart_plan(payload: SmartPlanRequest) -> dict:
    try:
        result = get_coach().generate_smart_plan(payload.user_id, payload.model_dump())
        result["generated_explanation"] = generate_grounded_nutrition_text(
            prompt=f"Explain this smart meal plan using the selected dataset foods and daily nutrition summary.",
            context_blocks=_build_plan_context(result),
            use_lmstudio=payload.use_lmstudio,
            openai_api_key=payload.openai_api_key,
            lmstudio_url=payload.lmstudio_url,
            lmstudio_model=payload.lmstudio_model,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to generate smart plan: {exc}") from exc


@app.post("/indian-intelligence")
def indian_food_intelligence(payload: IndianFoodRequest) -> dict:
    try:
        result = get_coach().indian_food_intelligence(payload.user_id, payload.query)
        result["generated_explanation"] = generate_grounded_nutrition_text(
            prompt=f"Explain the Indian food intelligence output using the dataset matches and suggested swaps.",
            context_blocks=_build_indian_context(payload.query, result.get("lens", {}), result.get("recommended_foods", []), result.get("smart_swaps", [])),
            use_lmstudio=payload.use_lmstudio,
            openai_api_key=payload.openai_api_key,
            lmstudio_url=payload.lmstudio_url,
            lmstudio_model=payload.lmstudio_model,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to generate Indian food intelligence: {exc}") from exc


@app.post("/food-lookup")
def food_lookup(payload: FoodLookupRequest) -> dict:
    try:
        result = get_coach().lookup_food(payload.query, payload.user_id, payload.top_k)
        # Return only very similar items (top 3 matches)
        top_results = result.get("results", [])[:3]
        
        if not top_results:
            return {
                "query": payload.query,
                "results": [],
                "source": "Anuvaad_INDB_2024.11.xlsx",
                "generated_explanation": "No matching foods found in dataset."
            }
        
        # Generate explanation ONLY for the best match, grounded in its real data
        best_match = top_results[0]
        context_blocks = [
            f"User searched for: {payload.query}",
            f"Best match found: {best_match['food_name']}",
            "Actual dataset values:",
            f"- Calories: {best_match.get('calories', 'N/A')} kcal per {best_match.get('serving_unit', 'serving')}",
            f"- Protein: {best_match.get('protein_g', 'N/A')} g",
            f"- Carbohydrates: {best_match.get('carbs_g', 'N/A')} g",
            f"- Fat: {best_match.get('fat_g', 'N/A')} g",
            f"- Fiber: {best_match.get('fiber_g', 'N/A')} g",
            f"- Calcium: {best_match.get('calcium_mg', 'N/A')} mg",
            f"- Iron: {best_match.get('iron_mg', 'N/A')} mg",
        ]
        
        explanation = generate_grounded_nutrition_text(
            prompt=f"Explain the nutritional profile of {best_match['food_name']} based on these actual dataset values. What makes it nutritionally significant?",
            context_blocks=context_blocks,
            use_lmstudio=payload.use_lmstudio,
            openai_api_key=payload.openai_api_key,
            lmstudio_url=payload.lmstudio_url,
            lmstudio_model=payload.lmstudio_model,
        )
        
        return {
            "query": payload.query,
            "best_match": best_match['food_name'],
            "results": top_results,
            "source": "Anuvaad_INDB_2024.11.xlsx",
            "generated_explanation": explanation
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to look up food: {exc}") from exc


@app.post("/food-compare")
def food_compare(payload: FoodCompareRequest) -> dict:
    try:
        result = get_coach().compare_foods(payload.first_query, payload.second_query, payload.user_id)
        comparison = result.get("comparison")
        if comparison:
            first_food = comparison["first_food"]
            second_food = comparison["second_food"]
            result["generated_explanation"] = generate_grounded_nutrition_text(
                prompt="Compare these two foods in plain language. Highlight protein, calories, fiber, and when each food is the better choice.",
                context_blocks=[
                    (
                        f"{first_food['food_name']}: {first_food['calories']} kcal, protein {first_food['protein_g']} g, "
                        f"carbs {first_food['carbs_g']} g, fat {first_food['fat_g']} g, fiber {first_food['fiber_g']} g."
                    ),
                    (
                        f"{second_food['food_name']}: {second_food['calories']} kcal, protein {second_food['protein_g']} g, "
                        f"carbs {second_food['carbs_g']} g, fat {second_food['fat_g']} g, fiber {second_food['fiber_g']} g."
                    ),
                ],
                use_lmstudio=payload.use_lmstudio,
                openai_api_key=payload.openai_api_key,
                lmstudio_url=payload.lmstudio_url,
                lmstudio_model=payload.lmstudio_model,
            )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to compare foods: {exc}") from exc


@app.get("/history/{user_id}")
def get_history(user_id: str) -> dict:
    try:
        return {"history": get_coach().get_history(user_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to load history: {exc}") from exc
