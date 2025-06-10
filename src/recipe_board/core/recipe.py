import uuid
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class IngredientState(Enum):
    RAW = "raw"
    CLEANED = "cleaned"
    CHOPPED = "chopped"
    COOKED = "cooked"
    # TODO: how many/what kind of states?


class Ingredient(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    amount: Optional[float]
    unit: Optional[str]
    # TODO: later (where belong?)
    # state: IngredientState = IngredientState.RAW
    modifiers: list[str]
    raw_text: str


class Equipment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    required: bool = True
    modifiers: Optional[str]


class BasicAction(BaseModel):
    """Represents a cooking verb identified in the first parsing pass."""

    verb: str
    sentence: str
    sentence_index: int  # For reference back to original text


class Action(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    ingredient_ids: list[str]
    equipment_id: str


class RecipeStep(BaseModel):
    step_number: int
    instruction: str
    ingredients_used: list[str]
    equipment_needed: list[str]
    estimated_time_minutes: Optional[int]
    dependencies: list[int] = []  # step numbers this depends on
