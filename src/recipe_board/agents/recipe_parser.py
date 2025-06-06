import re
from smolagents import tool


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
    pattern = r'## Ingredients\n(.*?)(?=\n## |\Z)'

    match = re.search(pattern, recipe, re.DOTALL)
    if match:
        content = match.group(1).rstrip()
        if content:
            return f"## Ingredients\n{content}"
        else:
            return '## Ingredients'
    return None
