import os
from huggingface_hub import InferenceClient
from smolagents import InferenceClientModel, CodeAgent, RunResult
from .prompts import parse_equipment_prompt
from .tools import (
    extract_verbs,
    find_ingredients_in_sentence,
    find_equipment_in_sentence,
    filter_valid_actions,
    validate_action_structure,
)
from wasabi import msg
from ..core.recipe import Ingredient, Equipment, Action, BasicAction
from ..core.state import RecipeSessionState, ParsingState

model = os.environ["HF_MODEL"]


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
    msg.info(f"LLM raw response: {result_preview}")

    # Try to parse as JSON and convert to Pydantic objects
    try:
        import json

        # Extract JSON from response using improved logic
        clean_result = _extract_json_from_response(result)

        # Log the cleaned response for debugging
        clean_preview = (
            clean_result[:300] + "..." if len(clean_result) > 300 else clean_result
        )
        msg.info(f"Cleaned response for JSON parsing: {clean_preview}")

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
            msg.fail(f"Error context: ...{context}...")
            msg.fail(f"Error position: ...{error_marker}")

        # Also log the full cleaned response for manual inspection
        msg.fail(f"Full cleaned response that failed to parse: {clean_result}")

        # Fallback - return state with empty data but preserve raw text
        msg.warn("Returning empty state due to JSON parsing failure")
        return state

    except Exception as e:
        # Catch any other unexpected errors during parsing
        msg.fail(f"Unexpected error during recipe parsing: {str(e)}")
        msg.fail(f"Error type: {type(e).__name__}")

        # Log the response that caused the issue
        result_preview = result[:300] + "..." if len(result) > 300 else result
        msg.fail(f"Response that caused error: {result_preview}")

        # Return empty state but preserve raw text
        msg.warn("Returning empty state due to unexpected parsing error")
        return state


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
        msg.warn(f"Expected dict but got {type(parsed_json)}: {parsed_json}")

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
            msg.warn(f"Skipping invalid ingredient item: {item}")
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
            msg.warn(f"Failed to create ingredient from {item}: {e}")
            continue

    # Convert equipment
    equipment_list = []
    for item in equipment_data:
        if not isinstance(item, dict):
            msg.warn(f"Skipping invalid equipment item: {item}")
            continue

        try:
            equipment = Equipment(
                name=item.get("name", ""),
                required=item.get("required", True),
                modifiers=item.get("modifiers"),
            )
            equipment_list.append(equipment)
        except Exception as e:
            msg.warn(f"Failed to create equipment from {item}: {e}")
            continue

    # Convert basic actions
    basic_actions_list = []
    for item in basic_actions_data:
        if not isinstance(item, dict):
            msg.warn(f"Skipping invalid basic action item: {item}")
            continue

        try:
            basic_action = BasicAction(
                verb=item.get("verb", ""),
                sentence=item.get("sentence", ""),
                sentence_index=item.get("sentence_index", 0),
            )
            basic_actions_list.append(basic_action)
        except Exception as e:
            msg.warn(f"Failed to create basic action from {item}: {e}")
            continue

    return ingredients, equipment_list, basic_actions_list


def ingredients_and_equipment_from_parsed_recipe(
    serialized_json_components: str,
) -> tuple[list[Ingredient], list[Equipment]]:
    """Convert serialized JSON from parse_recipe into Ingredient and Equipment objects.

    Args:
        serialized_json_components: JSON string containing 'ingredients' and 'equipment' arrays

    Returns:
        Tuple of (ingredients_list, equipment_list) as Pydantic objects

    Raises:
        ValueError: If JSON is invalid or missing required structure
    """
    try:
        import json

        data = json.loads(serialized_json_components)

        # Validate required top-level keys
        if not isinstance(data, dict):
            raise ValueError("JSON must be an object")
        if "ingredients" not in data or "equipment" not in data:
            raise ValueError("JSON must contain 'ingredients' and 'equipment' keys")

        ingredients_data = data.get("ingredients", [])
        equipment_data = data.get("equipment", [])

        if not isinstance(ingredients_data, list):
            raise ValueError("'ingredients' must be an array")
        if not isinstance(equipment_data, list):
            raise ValueError("'equipment' must be an array")

        # Convert ingredients
        ingredients = []
        for item in ingredients_data:
            if not isinstance(item, dict):
                msg.warn(f"Skipping invalid ingredient item: {item}")
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
                msg.warn(f"Failed to create ingredient from {item}: {e}")
                continue

        # Convert equipment
        equipment_list = []
        for item in equipment_data:
            if not isinstance(item, dict):
                msg.warn(f"Skipping invalid equipment item: {item}")
                continue

            try:
                equipment = Equipment(
                    name=item.get("name", ""),
                    required=item.get("required", True),
                    modifiers=item.get("modifiers"),
                )
                equipment_list.append(equipment)
            except Exception as e:
                msg.warn(f"Failed to create equipment from {item}: {e}")
                continue

        return ingredients, equipment_list

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    except Exception as e:
        msg.fail(f"Error parsing recipe components: {e}")
        raise


def parse_dependencies(state: RecipeSessionState) -> RecipeSessionState:
    """Parse action dependencies from recipe state with pre-identified basic actions.

    This function takes basic actions identified in the first pass and links them
    to specific ingredient and equipment IDs using smolagents with spaCy tools.

    Args:
        state: RecipeSessionState with parsed ingredients, equipment, and basic_actions

    Returns:
        Updated RecipeSessionState with parsed actions (linked dependencies)

    Raises:
        ValueError: If state is invalid or agent request fails
    """
    import json

    if not state.ingredients and not state.equipment:
        msg.warn("No ingredients or equipment found, cannot parse dependencies")
        return state

    if not state.basic_actions:
        msg.warn("No basic actions found, cannot parse dependencies")
        return state

    # Set up the agent with tools
    try:
        hf_model = InferenceClientModel(model_id=model, token=os.environ["HF_TOKEN"])

        agent = CodeAgent(
            tools=[
                find_ingredients_in_sentence,
                find_equipment_in_sentence,
                filter_valid_actions,
                validate_action_structure,
            ],
            model=hf_model,
            max_steps=8,  # Reduced since we don't need extract_verbs
        )
    except Exception as e:
        msg.fail(f"Error creating agent: {e}")
        raise ValueError(f"Failed to create agent: {e}")

    # Prepare ingredient and equipment names for the agent
    ingredient_names = [ing.name for ing in state.ingredients]
    equipment_names = [eq.name for eq in state.equipment]

    # Create the agent prompt with pre-identified basic actions
    basic_actions_info = [
        {"verb": ba.verb, "sentence": ba.sentence, "sentence_index": ba.sentence_index}
        for ba in state.basic_actions
    ]

    agent_prompt = f"""
You are a recipe analysis expert. Your task is to link pre-identified cooking verbs to specific ingredients and equipment.

You have access to these tools:
- find_ingredients_in_sentence: Find ingredient names in a single sentence
- find_equipment_in_sentence: Find equipment names in a single sentence
- filter_valid_actions: Remove actions that have no ingredients or equipment
- validate_action_structure: Ensure actions have proper structure and field types

Available ingredients (with IDs):
{[{"name": ing.name, "id": ing.id} for ing in state.ingredients]}

Available equipment (with IDs):
{[{"name": eq.name, "id": eq.id} for eq in state.equipment]}

Pre-identified basic actions to process:
{basic_actions_info}

Your goal: Return a JSON object with this structure:
{{
  "actions": [
    {{
      "name": "action_verb",
      "ingredient_ids": ["id1", "id2"],
      "equipment_ids": "equipment_id"
    }}
  ]
}}

Steps:
1. For each basic action, use its sentence to find ingredients/equipment:
   - find_ingredients_in_sentence(sentence=action_sentence, ingredient_names=ingredient_list)
   - find_equipment_in_sentence(sentence=action_sentence, equipment_names=equipment_list)
2. Create action objects linking verbs to the appropriate ingredient/equipment IDs
3. Call filter_valid_actions(actions=validated_actions)
4. OUTPUT FINAL JSON: {{"actions": [filtered_actions]}}

Process each basic action systematically, matching ingredients and equipment within each sentence context.
Use the filtering tools at the end instead of writing your own filtering code.
"""

    # Run the agent
    try:
        result = agent.run(agent_prompt)
        state.workflow_step = "dependencies_parsing"

        # Try to extract JSON from the result and convert to Action objects
        actions_data = None
        if isinstance(result, dict):
            msg.info("We received the response in the expected format - a `dict` !")
            actions_data = result.get("actions", [])
        elif isinstance(result, RunResult):
            msg.info(f"Agent result: {result.output[0:25]}...")
            raw = result.output
            # Look for JSON in the response
            import re

            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                # Validate JSON
                parsed = json.loads(json_str)
                actions_data = parsed.get("actions", [])
            else:
                # No JSON found
                msg.warn("No JSON found in agent response")
                actions_data = []
        else:
            # Unexpected result type
            msg.warn(f"Unexpected agent result type: {type(result)}")
            actions_data = []

        # Convert actions to Pydantic objects
        actions = []
        for action_item in actions_data:
            if not isinstance(action_item, dict):
                msg.warn(f"Skipping invalid action item: {action_item}")
                continue

            try:
                action = Action(
                    name=action_item.get("name", ""),
                    ingredient_ids=action_item.get("ingredient_ids", []),
                    equipment_ids=action_item.get("equipment_ids", ""),
                )
                actions.append(action)
            except Exception as e:
                msg.warn(f"Failed to create action from {action_item}: {e}")
                continue

        state.actions = actions
        state.workflow_step = "dependencies_parsed"
        return state

    except Exception as e:
        msg.warn(f"Agent execution failed: {e}")
        return state


# Backward compatibility alias
def parse_actions(state: RecipeSessionState) -> RecipeSessionState:
    """
    Backward compatibility alias for parse_dependencies.

    DEPRECATED: Use parse_dependencies instead.
    """
    msg.warn("parse_actions is deprecated, use parse_dependencies instead")
    return parse_dependencies(state)
