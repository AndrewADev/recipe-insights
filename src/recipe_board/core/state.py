from dataclasses import dataclass, field
from typing import List, Dict, Any
from recipe_board.core.recipe import Ingredient, Equipment, Action


@dataclass
class RecipeSessionState:
    """
    Session state for recipe processing workflow.

    Stores structured data throughout the multi-step agent pipeline,
    enabling data sharing between ingredient parsing, action extraction,
    and dependency analysis.
    """

    raw_text: str = ""
    ingredients: List[Ingredient] = field(default_factory=list)
    equipment: List[Equipment] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    workflow_step: str = "initial"

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for JSON serialization/UI display."""
        return {
            "raw_text": self.raw_text,
            "ingredients": [ing.model_dump() for ing in self.ingredients],
            "equipment": [eq.model_dump() for eq in self.equipment],
            "actions": [action.model_dump() for action in self.actions],
            "workflow_step": self.workflow_step,
        }

    def has_parsed_data(self) -> bool:
        """Check if recipe has been parsed with valid ingredients and equipment."""
        return len(self.ingredients) > 0 and len(self.equipment) > 0

    def clear(self):
        """Reset state to initial values."""
        self.raw_text = ""
        self.ingredients = []
        self.equipment = []
        self.actions = []
        self.workflow_step = "initial"

    def format_ingredients_for_display(self) -> str:
        """Format ingredients list for UI display."""
        if not self.ingredients:
            return "No ingredients parsed yet."

        formatted = []
        for ing in self.ingredients:
            parts = []
            if ing.amount:
                parts.append(str(ing.amount))
            if ing.unit:
                parts.append(ing.unit)
            parts.append(ing.name)
            if ing.modifiers:
                parts.append(f"({', '.join(ing.modifiers)})")
            formatted.append(" ".join(parts))

        return "\n".join(f"- {item}" for item in formatted)

    def format_equipment_for_display(self) -> str:
        """Format equipment list for UI display."""
        if not self.equipment:
            return "No equipment parsed yet."

        formatted = []
        for eq in self.equipment:
            display = eq.name
            if eq.modifiers:
                display += f" ({eq.modifiers})"
            if eq.required:
                display += " [required]"
            formatted.append(display)

        return "\n".join(f"- {item}" for item in formatted)

    def format_actions_for_display(self) -> str:
        """Format actions list for UI display."""
        if not self.actions:
            return "No actions parsed yet."

        formatted = []
        for action in self.actions:
            parts = [f"Action: {action.name}"]
            if action.ingredient_ids:
                ing_names = [
                    ing.name
                    for ing in self.ingredients
                    if ing.id in action.ingredient_ids
                ]
                parts.append(f"Ingredients: {', '.join(ing_names)}")
            if action.equipment_ids:
                eq_name = next(
                    (eq.name for eq in self.equipment if eq.id == action.equipment_ids),
                    "Unknown",
                )
                parts.append(f"Equipment: {eq_name}")
            formatted.append(" | ".join(parts))

        return "\n".join(f"- {item}" for item in formatted)
