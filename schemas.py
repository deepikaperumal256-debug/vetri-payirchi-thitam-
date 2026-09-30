from typing import Literal
from pydantic import BaseModel, Field


class UserInput(BaseModel):
    username: str = Field(min_length=1, max_length=60)
    user_id: str = Field(min_length=1, max_length=40)
    age: int = Field(ge=10, le=100)
    weight: float = Field(gt=20, lt=400)
    goal: str = Field(min_length=2, max_length=60)
    intensity: Literal["low", "medium", "high"]


class FeedbackRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=40)
    feedback: str = Field(min_length=3, max_length=500)
