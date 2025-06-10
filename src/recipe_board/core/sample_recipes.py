"""
Sample recipe utilities for loading and previewing recipe files.
"""

import os
import glob
from typing import Dict, Optional
from wasabi import msg


def load_sample_recipes(data_dir: Optional[str] = None) -> Dict[str, str]:
    """
    Load sample recipes from the data directory.

    Args:
        data_dir: Path to data directory. If None, uses default relative path.

    Returns:
        Dictionary mapping recipe titles to full recipe content.
    """
    recipes = {}

    if data_dir is None:
        # Default path relative to this module
        data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")

    # Find all markdown files in data directory
    recipe_files = glob.glob(os.path.join(data_dir, "*.md"))

    for file_path in recipe_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract title from first line (remove # prefix)
            lines = content.strip().split("\n")
            title = (
                lines[0].replace("#", "").strip()
                if lines
                else os.path.basename(file_path)
            )

            recipes[title] = content
        except Exception as e:
            msg.warn(f"Could not load recipe from {file_path}: {e}")

    return recipes


def create_recipe_preview(recipe_text: str, max_lines: int = 8) -> str:
    """
    Create a preview of the recipe showing ingredients and first few steps.

    Args:
        recipe_text: Full recipe text content.
        max_lines: Maximum number of lines to include in preview.

    Returns:
        Truncated preview text with "..." if truncated.
    """
    if not recipe_text:
        return ""

    lines = recipe_text.strip().split("\n")
    preview_lines = []
    line_count = 0

    for line in lines:
        if line_count >= max_lines:
            preview_lines.append("...")
            break

        # Skip empty lines at start
        if not preview_lines and not line.strip():
            continue

        preview_lines.append(line)
        line_count += 1

    return "\n".join(preview_lines)


def get_sample_recipe_choices(include_empty: bool = True) -> list:
    """
    Get list of sample recipe choices for dropdowns.

    Args:
        include_empty: Whether to include empty string as first choice.

    Returns:
        List of recipe titles suitable for dropdown choices.
    """
    recipes = load_sample_recipes()
    # Filter out empty or whitespace-only titles
    choices = [title for title in recipes.keys() if title and title.strip()]

    if include_empty:
        choices = [""] + choices

    return choices
