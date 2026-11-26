from typing import Any

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    app_name: str
    default_use_lmstudio: bool
    lmstudio_url: str
    lmstudio_model: str
    has_openai_key: bool
    dataset_path: str


class QueryRequest(BaseModel):
    user_id: str = "guest_123"
    query: str = Field(min_length=1)
    query_type: str
    context: dict[str, Any] = Field(default_factory=dict)
    use_lmstudio: bool = True
    openai_api_key: str | None = None
    lmstudio_url: str | None = None
    lmstudio_model: str | None = None


class QueryResponse(BaseModel):
    response: str
    matched_items: list[dict[str, Any]] = Field(default_factory=list)


class AnalysisRequest(BaseModel):
    user_id: str = "guest_123"
    query: str = Field(min_length=1)
    use_lmstudio: bool = True
    openai_api_key: str | None = None
    lmstudio_url: str | None = None
    lmstudio_model: str | None = None


class MealPlanRequest(BaseModel):
    user_id: str = "guest_123"
    goal: str
    restrictions: str = ""
    use_lmstudio: bool = True
    openai_api_key: str | None = None
    lmstudio_url: str | None = None
    lmstudio_model: str | None = None


class EducationRequest(BaseModel):
    user_id: str = "guest_123"
    question: str = Field(min_length=1)
    use_lmstudio: bool = True
    openai_api_key: str | None = None
    lmstudio_url: str | None = None
    lmstudio_model: str | None = None


class RecommendationRequest(BaseModel):
    user_id: str = "guest_123"
    goal: str = Field(min_length=1)
    use_lmstudio: bool = True
    openai_api_key: str | None = None
    lmstudio_url: str | None = None
    lmstudio_model: str | None = None


class ProfileRequest(BaseModel):
    user_id: str = "guest_123"
    age: int = 25
    weight: float = 70
    height: float = 170
    gender: str = "female"
    activity_level: str = "moderate"
    health_goals: list[str] = Field(default_factory=lambda: ["balanced_diet"])
    dietary_restrictions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    health_conditions: list[str] = Field(default_factory=list)
    cuisine_preferences: list[str] = Field(default_factory=lambda: ["indian"])
    budget_preference: str = "medium"
    max_prep_time: int = 30


class PersonalizedRecommendationRequest(BaseModel):
    user_id: str = "guest_123"
    meal_type: str = "general"
    query: str | None = None
    top_k: int = 6
    use_lmstudio: bool = True
    openai_api_key: str | None = None
    lmstudio_url: str | None = None
    lmstudio_model: str | None = None


class SearchRequest(BaseModel):
    user_id: str = "guest_123"
    query: str = Field(min_length=1)
    top_k: int = 8
    use_lmstudio: bool = True
    openai_api_key: str | None = None
    lmstudio_url: str | None = None
    lmstudio_model: str | None = None


class MealRepairRequest(BaseModel):
    user_id: str = "guest_123"
    meal_text: str = Field(min_length=1)
    use_lmstudio: bool = True
    openai_api_key: str | None = None
    lmstudio_url: str | None = None
    lmstudio_model: str | None = None


class SmartPlanRequest(BaseModel):
    user_id: str = "guest_123"
    query: str | None = None
    pantry_items: list[str] = Field(default_factory=list)
    budget_preference: str | None = None
    max_prep_time: int | None = None
    use_lmstudio: bool = True
    openai_api_key: str | None = None
    lmstudio_url: str | None = None
    lmstudio_model: str | None = None


class IndianFoodRequest(BaseModel):
    user_id: str = "guest_123"
    query: str = Field(min_length=1)
    use_lmstudio: bool = True
    openai_api_key: str | None = None
    lmstudio_url: str | None = None
    lmstudio_model: str | None = None


class FoodLookupRequest(BaseModel):
    user_id: str = "guest_123"
    query: str = Field(min_length=1)
    top_k: int = 5
    use_lmstudio: bool = True
    openai_api_key: str | None = None
    lmstudio_url: str | None = None
    lmstudio_model: str | None = None


class FoodCompareRequest(BaseModel):
    user_id: str = "guest_123"
    first_query: str = Field(min_length=1)
    second_query: str = Field(min_length=1)
    use_lmstudio: bool = True
    openai_api_key: str | None = None
    lmstudio_url: str | None = None
    lmstudio_model: str | None = None
