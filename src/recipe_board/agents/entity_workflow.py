from recipe_board.agents.parsing_agent import model
from recipe_board.agents.prompts import parse_equipment_prompt
from recipe_board.core.logging_utils import safe_log_user_data
from recipe_board.core.recipe import BasicAction, Equipment, Ingredient
from recipe_board.core.state import ParsingState, RecipeSessionState


from huggingface_hub import InferenceClient
from wasabi import msg


import os


def _extract_json_from_response(response: str) -> str:
    """Extract JSON content from LLM response, handling various formats."""
    import re

    if not response or not response.strip():
        return response.strip()

    clean_result = response.strip()

    # Look for JSON code blocks anywhere in the response (not just at the start)
    json_match = re.search(r"```json\s*(.*?)\s*```", clean_result, re.DOTALL)
    if json_match:
        # Extract just the JSON content from the code block
        extracted = json_match.group(1).strip()
        msg.info("Extracted JSON from ```json code block")
        return extracted

    # Fallback: try to find any code block
    code_match = re.search(r"```\s*(.*?)\s*```", clean_result, re.DOTALL)
    if code_match:
        extracted = code_match.group(1).strip()
        msg.info("Extracted content from generic ``` code block")
        return extracted

    # No code blocks found, but there might be text before/after JSON
    # Try to extract JSON object from the response
    json_obj_match = re.search(r"\{.*\}", clean_result, re.DOTALL)
    if json_obj_match:
        extracted = json_obj_match.group(0).strip()
        msg.info("Extracted JSON object from response text")
        return extracted

    # No JSON structure found, return original
    msg.warn("No JSON structure found in response")
    return clean_result


def _convert_json_to_objects(
    parsed_json: dict,
) -> tuple[list[Ingredient], list[Equipment], list[BasicAction]]:
    """Convert parsed JSON to Ingredient, Equipment, and BasicAction objects."""

    # Log the structure of the parsed JSON for debugging
    if isinstance(parsed_json, dict):
        available_keys = list(parsed_json.keys())
        msg.info(f"Parsed JSON contains keys: {available_keys}")
    else:
        safe_log_user_data(
            msg.warn, f"Expected dict but got {type(parsed_json)}: {parsed_json}"
        )

    ingredients_data = parsed_json.get("ingredients", [])
    equipment_data = parsed_json.get("equipment", [])
    basic_actions_data = parsed_json.get("basic_actions", [])

    if not isinstance(ingredients_data, list):
        msg.warn("'ingredients' must be an array")
        ingredients_data = []
    if not isinstance(equipment_data, list):
        msg.warn("'equipment' must be an array")
        equipment_data = []
    if not isinstance(basic_actions_data, list):
        msg.warn("'basic_actions' must be an array")
        basic_actions_data = []

    # Log what we're attempting to convert
    msg.info(
        f"Converting: {len(ingredients_data)} ingredients, {len(equipment_data)} equipment, {len(basic_actions_data)} basic actions"
    )

    # Convert ingredients
    ingredients = []
    for item in ingredients_data:
        if not isinstance(item, dict):
            safe_log_user_data(msg.warn, f"Skipping invalid ingredient item: {item}")
            continue

        # Handle modifiers - convert string to list or ensure it's a list
        modifiers = item.get("modifiers", [])
        if isinstance(modifiers, str):
            modifiers = [modifiers] if modifiers else []
        elif modifiers is None:
            modifiers = []
        elif not isinstance(modifiers, list):
            modifiers = []

        name = item.get("name", "")
        amount = item.get("amount")
        unit = item.get("unit")

        raw_text_parts = []
        if amount is not None:
            raw_text_parts.append(str(amount))
        if unit:
            raw_text_parts.append(unit)
        raw_text_parts.append(name)
        if modifiers:
            raw_text_parts.extend(modifiers)
        raw_text = " ".join(raw_text_parts)

        try:
            ingredient = Ingredient(
                name=name,
                amount=amount,
                unit=unit,
                modifiers=modifiers,
                raw_text=raw_text,
            )
            ingredients.append(ingredient)
        except Exception as e:
            safe_log_user_data(
                msg.warn, f"Failed to create ingredient from {item}: {e}"
            )
            continue

    # Convert equipment
    equipment_list = []
    for item in equipment_data:
        if not isinstance(item, dict):
            safe_log_user_data(msg.warn, f"Skipping invalid equipment item: {item}")
            continue

        try:
            equipment = Equipment(
                name=item.get("name", ""),
                required=item.get("required", True),
                modifiers=item.get("modifiers"),
            )
            equipment_list.append(equipment)
        except Exception as e:
            safe_log_user_data(msg.warn, f"Failed to create equipment from {item}: {e}")
            continue

    # Convert basic actions
    basic_actions_list = []
    for item in basic_actions_data:
        if not isinstance(item, dict):
            safe_log_user_data(msg.warn, f"Skipping invalid basic action item: {item}")
            continue

        try:
            basic_action = BasicAction(
                verb=item.get("verb", ""),
                sentence=item.get("sentence", ""),
                sentence_index=item.get("sentence_index", 0),
            )
            basic_actions_list.append(basic_action)
        except Exception as e:
            safe_log_user_data(
                msg.warn, f"Failed to create basic action from {item}: {e}"
            )
            continue

    return ingredients, equipment_list, basic_actions_list


def parse_recipe(recipe: str) -> RecipeSessionState:
    """
    Parse recipe text and return structured state with ingredients and equipment.

    Args:
        recipe: Raw recipe text

    Returns:
        RecipeSessionState with parsed ingredients and equipment
    """
    state = RecipeSessionState()
    state.raw_text = recipe
    state.parsing_state = ParsingState.PARSING_RECIPE

    try:
        hf_client = InferenceClient(
            provider="hf-inference",
            api_key=os.environ["HF_TOKEN"],
        )
    except Exception as e:
        # TODO: retries?
        msg.fail(f"error creating client: {e}")
        return state

    result = hf_client.text_generation(parse_equipment_prompt + recipe, model=model)

    if result is None or result == "":
        msg.warn("No result returned from LLM!")
        return state

    # Log the raw response for debugging (truncated if very long)
    result_preview = result[:500] + "..." if len(result) > 500 else result
    safe_log_user_data(msg.info, f"LLM raw response: {result_preview}")

    # Try to parse as JSON and convert to Pydantic objects
    try:
        import json

        # Extract JSON from response using improved logic
        clean_result = _extract_json_from_response(result)

        # Log the cleaned response for debugging
        clean_preview = (
            clean_result[:300] + "..." if len(clean_result) > 300 else clean_result
        )
        safe_log_user_data(
            msg.info, f"Cleaned response for JSON parsing: {clean_preview}"
        )

        parsed = json.loads(clean_result)

        # Convert to structured state
        ingredients, equipment, basic_actions = _convert_json_to_objects(parsed)
        state.ingredients = ingredients
        state.equipment = equipment
        state.basic_actions = basic_actions
        state.parsing_state = ParsingState.COMPLETED

        # Log successful parsing results
        msg.good(
            f"Successfully parsed recipe: {len(ingredients)} ingredients, {len(equipment)} equipment, {len(basic_actions)} basic actions"
        )

        return state

    except json.JSONDecodeError as e:
        # Provide detailed debugging information for JSON parsing failures
        msg.fail(f"JSON parsing failed: {str(e)}")
        msg.fail(f"JSON error at line {e.lineno}, column {e.colno}: {e.msg}")

        # Show the problematic part of the response around the error
        if hasattr(e, "pos") and e.pos < len(clean_result):
            start = max(0, e.pos - 50)
            end = min(len(clean_result), e.pos + 50)
            context = clean_result[start:end]
            error_marker = " " * (e.pos - start) + "^"
            safe_log_user_data(msg.fail, f"Error context: ...{context}...")
            msg.fail(f"Error position: ...{error_marker}")

        # Also log the full cleaned response for manual inspection
        safe_log_user_data(
            msg.fail, f"Full cleaned response that failed to parse: {clean_result}"
        )

        # Fallback - return state with empty data but preserve raw text
        msg.warn("Returning empty state due to JSON parsing failure")
        return state

    except Exception as e:
        # Catch any other unexpected errors during parsing
        msg.fail(f"Unexpected error during recipe parsing: {str(e)}")
        msg.fail(f"Error type: {type(e).__name__}")

        # Log the response that caused the issue
        result_preview = result[:300] + "..." if len(result) > 300 else result
        safe_log_user_data(msg.fail, f"Response that caused error: {result_preview}")

        # Return empty state but preserve raw text
        msg.warn("Returning empty state due to unexpected parsing error")
        return state
