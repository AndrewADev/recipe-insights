"""Tools for recipe parsing agents using spaCy and other utilities."""

import spacy
from smolagents import tool
from typing import List, Dict, Any
from wasabi import msg


# Load spaCy model - using the large English model for better accuracy
try:
    nlp = spacy.load("en_core_web_lg")
except OSError:
    msg.warn("en_core_web_lg not found, falling back to en_core_web_sm")
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        msg.fail(
            "No spaCy English model found. Install with: python -m spacy download en_core_web_lg"
        )
        raise


@tool
def extract_verbs(text: str) -> List[Dict[str, Any]]:
    """Extract all verbs from recipe text with their context.

    Args:
        text: Recipe text to analyze

    Returns:
        List of verb dictionaries with verb, position, sentence, and lemma
    """
    doc = nlp(text)
    verbs = []

    for token in doc:
        if token.pos_ == "VERB":
            # Get the sentence containing this verb
            sentence = token.sent.text.strip()

            verb_info = {
                "verb": token.text,
                "lemma": token.lemma_,
                "position": token.idx,
                "sentence": sentence,
                "sentence_start": token.sent.start_char,
                "sentence_end": token.sent.end_char,
            }
            verbs.append(verb_info)

    return verbs


@tool
def find_ingredients_in_sentence(
    sentence: str, ingredient_names: List[str]
) -> List[str]:
    """Find mentions of ingredients in a single sentence.

    Args:
        sentence: Single sentence to search in
        ingredient_names: List of ingredient names to look for

    Returns:
        List of ingredient names found in the sentence
    """
    sentence_lower = sentence.lower()
    found_ingredients = []

    for ingredient in ingredient_names:
        if ingredient.lower() in sentence_lower:
            found_ingredients.append(ingredient)

    return found_ingredients


@tool
def find_equipment_in_sentence(sentence: str, equipment_names: List[str]) -> List[str]:
    """Find mentions of equipment in a single sentence.

    Args:
        sentence: Single sentence to search in
        equipment_names: List of equipment names to look for

    Returns:
        List of equipment names found in the sentence
    """
    sentence_lower = sentence.lower()
    found_equipment = []

    for equipment in equipment_names:
        if equipment.lower() in sentence_lower:
            found_equipment.append(equipment)

    return found_equipment


@tool
def filter_valid_actions(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out actions that have no associated ingredients or equipment.

    Args:
        actions: List of action dictionaries

    Returns:
        Filtered list containing only actions with ingredients and/or equipment
    """
    valid_actions = []

    for action in actions:
        # Check if action has ingredients or equipment
        has_ingredients = (
            "ingredient_ids" in action
            and action["ingredient_ids"]
            and len(action["ingredient_ids"]) > 0
        )
        has_equipment = (
            "equipment_id" in action
            and action["equipment_id"]
            and action["equipment_id"] != ""
            and action["equipment_id"] is not None
        )

        # Keep action if it has at least one ingredient OR equipment
        if has_ingredients or has_equipment:
            valid_actions.append(action)

    return valid_actions


@tool
def validate_action_structure(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate and clean action dictionary structure.

    Args:
        actions: List of action dictionaries to validate

    Returns:
        List of validated actions with proper structure
    """
    validated_actions = []

    for action in actions:
        if not isinstance(action, dict):
            continue

        # Ensure required fields exist
        validated_action = {
            "name": action.get("name", "unknown_action"),
            "description": action.get("description", ""),
            "ingredient_ids": [],
            "equipment_id": None,
        }

        # Handle ingredient_ids - ensure it's a list
        ingredient_ids = action.get("ingredient_ids", [])
        if isinstance(ingredient_ids, list):
            validated_action["ingredient_ids"] = ingredient_ids
        elif isinstance(ingredient_ids, str) and ingredient_ids:
            validated_action["ingredient_ids"] = [ingredient_ids]

        # Handle equipment_id - ensure it's a string or None
        equipment_id = action.get("equipment_id")
        if isinstance(equipment_id, str) and equipment_id:
            validated_action["equipment_id"] = equipment_id
        elif isinstance(equipment_id, list) and len(equipment_id) > 0:
            # If accidentally passed as list, take first item
            validated_action["equipment_id"] = str(equipment_id[0])

        validated_actions.append(validated_action)

    return validated_actions
