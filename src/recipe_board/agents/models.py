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
from ..core.recipe import Ingredient, Equipment, Action
from ..core.state import RecipeSessionState

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
    state.workflow_step = "parsing"

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
        msg.warn("No result returned!")
        return state

    # Try to parse as JSON and convert to Pydantic objects
    try:
        import json
        import re

        # Strip markdown code blocks if present
        clean_result = result.strip()
        if clean_result.startswith("```json"):
            clean_result = re.sub(r"```json\s*", "", clean_result)
        if clean_result.startswith("```"):
            clean_result = re.sub(r"```\s*", "", clean_result)
        if clean_result.endswith("```"):
            clean_result = re.sub(r"\s*```$", "", clean_result)

        parsed = json.loads(clean_result)

        # Convert to structured state
        ingredients, equipment = _convert_json_to_objects(parsed)
        state.ingredients = ingredients
        state.equipment = equipment
        state.workflow_step = "parsed"

        return state

    except json.JSONDecodeError:
        # Fallback - return state with empty data but preserve raw text
        msg.warn("Response is not valid JSON, returning empty state")
        return state


def _convert_json_to_objects(
    parsed_json: dict,
) -> tuple[list[Ingredient], list[Equipment]]:
    """Convert parsed JSON to Ingredient and Equipment objects."""
    ingredients_data = parsed_json.get("ingredients", [])
    equipment_data = parsed_json.get("equipment", [])

    if not isinstance(ingredients_data, list):
        msg.warn("'ingredients' must be an array")
        ingredients_data = []
    if not isinstance(equipment_data, list):
        msg.warn("'equipment' must be an array")
        equipment_data = []

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


def parse_actions(state: RecipeSessionState) -> RecipeSessionState:
    """Parse actions from recipe state using agent with spaCy tools.

    Args:
        state: RecipeSessionState with parsed ingredients and equipment

    Returns:
        Updated RecipeSessionState with parsed actions

    Raises:
        ValueError: If state is invalid or agent request fails
    """
    import json

    if not state.ingredients and not state.equipment:
        msg.warn("No ingredients or equipment found, cannot parse actions")
        return state

    # Set up the agent with tools
    try:
        hf_model = InferenceClientModel(model_id=model, token=os.environ["HF_TOKEN"])

        agent = CodeAgent(
            tools=[
                extract_verbs,
                find_ingredients_in_sentence,
                find_equipment_in_sentence,
                filter_valid_actions,
                validate_action_structure,
            ],
            model=hf_model,
            max_steps=10,
        )
    except Exception as e:
        msg.fail(f"Error creating agent: {e}")
        raise ValueError(f"Failed to create agent: {e}")

    # Prepare ingredient and equipment names for the agent
    ingredient_names = [ing.name for ing in state.ingredients]
    equipment_names = [eq.name for eq in state.equipment]

    # Create the agent prompt with recipe text properly quoted
    recipe_text_escaped = state.raw_text.replace('"', '\\"').replace("'", "\\'")

    agent_prompt = f"""
You are a recipe analysis expert. Your task is to identify actions in a recipe and link them to specific ingredients and equipment.

You have access to these tools:
- extract_verbs: Find all verbs in the recipe text with their sentence context
- find_ingredients_in_sentence: Find ingredient names in a single sentence
- find_equipment_in_sentence: Find equipment names in a single sentence
- filter_valid_actions: Remove actions that have no ingredients or equipment
- validate_action_structure: Ensure actions have proper structure and field types

Available ingredients (with IDs):
{[{"name": ing.name, "id": ing.id} for ing in state.ingredients]}

Available equipment (with IDs):
{[{"name": eq.name, "id": eq.id} for eq in state.equipment]}

Recipe text to analyze:
"{recipe_text_escaped}"

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
1. Use extract_verbs to get all verbs with their sentence context
2. For each cooking-relevant verb, use its sentence to find ingredients/equipment:
   - find_ingredients_in_sentence(sentence=verb_sentence, ingredient_names=ingredient_list)
   - find_equipment_in_sentence(sentence=verb_sentence, equipment_names=equipment_list)
3. Create action objects linking verbs to the appropriate ingredient/equipment IDs
4. Call filter_valid_actions(actions=validated_actions)
5. OUTPUT FINAL JSON: {{"actions": [filtered_actions]}}

Start by calling: extract_verbs(text="{recipe_text_escaped}")
Then for each cooking verb, search only within its sentence context.
Use the filtering tools at the end instead of writing your own filtering code.
"""

    # Run the agent
    try:
        result = agent.run(agent_prompt)
        state.workflow_step = "actions_parsing"

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
        state.workflow_step = "actions_parsed"
        return state

    except Exception as e:
        msg.warn(f"Agent execution failed: {e}")
        return state
