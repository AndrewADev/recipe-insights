# Core models (src/models/recipe.py)
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class IngredientState(Enum):
    RAW = "raw"
    CLEANED = "cleaned"
    CHOPPED = "chopped"
    COOKED = "cooked"
    # TODO: how many/what kind of states?


class Ingredient(BaseModel):
    name: str
    # TODO: fractions? Pretty common in recipes
    amount: Optional[float]
    unit: Optional[str]
    # TODO: later (where belong?)
    # state: IngredientState = IngredientState.RAW
    modifiers: List[str]
    raw_text: str


class Equipment(BaseModel):
    name: str
    required: bool = True
    estimated_size: Optional[str] = None


class RecipeStep(BaseModel):
    step_number: int
    instruction: str
    ingredients_used: List[str]
    equipment_needed: List[str]
    estimated_time_minutes: Optional[int]
    dependencies: List[int] = []  # step numbers this depends on
