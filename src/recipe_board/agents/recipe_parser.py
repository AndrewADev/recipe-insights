import re
from typing import List
from smolagents import tool
import pandas as pd

from recipe_board.agents.recipe_analyzer import parse_ingredients_from_section
from recipe_board.core.recipe import Ingredient


@tool
def get_ingredients_section(recipe: str) -> str:
    """
    Extract the ingredients section from a complete recipe text.

    Searches for a markdown section starting with "## Ingredients" and extracts
    all content until the next section (marked by another "## " header).

    Args:
        recipe (str): Complete recipe text in markdown format.
                     Example: "# Recipe Title\n\n## Ingredients\n\n- 1 cup flour\n\n## Instructions\n\n1. Mix well"

    Returns:
        str: The ingredients section including the "## Ingredients" header and all ingredient items,
             or None if no ingredients section is found.

    Examples:
        >>> recipe = "# Title\n\n## Ingredients\n\n- 1 cup flour\n- 2 eggs\n\n## Instructions\n\n1. Mix"
        >>> get_ingredients_section(recipe)
        "## Ingredients\n\n- 1 cup flour\n- 2 eggs"
    """
    # Pattern to match from "## Ingredients" to the next "## " heading or end of string
    pattern = r"## Ingredients\n(.*?)(?=\n## |\Z)"

    match = re.search(pattern, recipe, re.DOTALL)
    if match:
        content = match.group(1).rstrip()
        if content:
            return f"## Ingredients\n{content}"
        else:
            return "## Ingredients"
    return None


def ingredients_to_dataframe(ingredients: List[Ingredient]) -> pd.DataFrame:
    """Convert list of Ingredient objects to a pandas DataFrame for display."""
    if not ingredients:
        return pd.DataFrame(columns=["Amount", "Unit", "Name", "Modifiers", "Raw Text"])

    data = []
    for ingredient in ingredients:
        data.append(
            {
                "Amount": ingredient.amount if ingredient.amount is not None else "",
                "Unit": ingredient.unit if ingredient.unit else "",
                "Name": ingredient.name,
                "Modifiers": (
                    ", ".join(ingredient.modifiers) if ingredient.modifiers else ""
                ),
                "Raw Text": ingredient.raw_text,
            }
        )

    return pd.DataFrame(data)


def parse_recipe_ingredients(recipe_text: str) -> pd.DataFrame:
    """Parse a recipe and return ingredients as a DataFrame."""
    if not recipe_text.strip():
        return pd.DataFrame(columns=["Amount", "Unit", "Name", "Modifiers", "Raw Text"])

    try:
        # Extract ingredients section from full recipe
        ingredients_section = get_ingredients_section(recipe_text)

        if not ingredients_section:
            # If no clear ingredients section found, try parsing the whole text
            ingredients_section = recipe_text

        # Parse ingredients using existing analyzer
        ingredients = parse_ingredients_from_section(ingredients_section)

        # Convert to DataFrame for display
        return ingredients_to_dataframe(ingredients)

    except Exception as e:
        # Return error message in DataFrame format
        error_df = pd.DataFrame(
            {
                "Amount": ["Error"],
                "Unit": [""],
                "Name": [f"Parsing failed: {str(e)}"],
                "Modifiers": [""],
                "Raw Text": [""],
            }
        )
        return error_df
