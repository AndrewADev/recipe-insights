import os
from huggingface_hub import InferenceClient
from smolagents import HfApiModel, CodeAgent, RunResult
from .prompts import parse_equipment_prompt
from .tools import (
    extract_verbs,
    find_ingredients_in_sentence,
    find_equipment_in_sentence,
    filter_valid_actions,
    validate_action_structure,
)
from wasabi import msg
from ..core.recipe import Ingredient, Equipment

model = os.environ["HF_MODEL"]


def parse_recipe(recipe: str):
    try:
        hf_client = InferenceClient(
            provider="hf-inference",
            api_key=os.environ["HF_TOKEN"],
        )
    except Exception as e:
        # TODO: retries?
        msg.fail("error creating client:  {e}")

    result = hf_client.text_generation(parse_equipment_prompt + recipe, model=model)

    if result is None or result == "":
        msg.warn("No result returned!")
        return "{}"

    # Try to parse as JSON and format nicely
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

        # TODO: avoid back-and-forth
        parsed = json.loads(clean_result)
        return json.dumps(parsed, indent=2)
    except json.JSONDecodeError:
        # Fallback to raw result if not valid JSON
        msg.warn("Response is not valid JSON, returning raw result")
        return result


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


def parse_actions(recipe_text: str, parsed_recipe_json: str) -> str:
    """Parse actions from recipe text using agent with spaCy tools.

    Args:
        recipe_text: Original recipe text
        parsed_recipe_json: JSON string from parse_recipe containing ingredients/equipment

    Returns:
        JSON string containing parsed actions

    Raises:
        ValueError: If parsed_recipe_json is invalid or agent request fails
    """
    try:
        import json

        # Convert JSON to Pydantic objects
        ingredients, equipment = ingredients_and_equipment_from_parsed_recipe(
            parsed_recipe_json
        )

        if not ingredients and not equipment:
            msg.warn("No ingredients or equipment found, cannot parse actions")
            return json.dumps({"actions": []}, indent=2)

        # Set up the agent with tools
        try:
            hf_model = HfApiModel(model_id=model, token=os.environ["HF_TOKEN"])

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
        ingredient_names = [ing.name for ing in ingredients]
        equipment_names = [eq.name for eq in equipment]

        # Create the agent prompt with recipe text properly quoted
        recipe_text_escaped = recipe_text.replace('"', '\\"').replace("'", "\\'")

        agent_prompt = f"""
You are a recipe analysis expert. Your task is to identify actions in a recipe and link them to specific ingredients and equipment.

You have access to these tools:
- extract_verbs: Find all verbs in the recipe text with their sentence context
- find_ingredients_in_sentence: Find ingredient names in a single sentence
- find_equipment_in_sentence: Find equipment names in a single sentence
- filter_valid_actions: Remove actions that have no ingredients or equipment
- validate_action_structure: Ensure actions have proper structure and field types

Available ingredients (with IDs):
{[{"name": ing.name, "id": ing.id} for ing in ingredients]}

Available equipment (with IDs):
{[{"name": eq.name, "id": eq.id} for eq in equipment]}

Recipe text to analyze:
"{recipe_text_escaped}"

Your goal: Return a JSON object with this structure:
{{
  "actions": [
    {{
      "name": "action_verb",
      "ingredient_ids": ["id1", "id2"],
      "equipment_id": "equipment_id"
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

            # TODO: conver str case too
            # Try to extract JSON from the result
            if isinstance(result, dict):
                msg.info("We received the response in the expected format - a `dict` !")
                return json.dumps(result, indent=2)
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
                    return json.dumps(parsed, indent=2)
                else:
                    # No JSON found, return empty actions
                    msg.warn("No JSON found in agent response")
                    return json.dumps({"actions": []}, indent=2)

            else:
                # Unexpected result type
                msg.warn(f"Unexpected agent result type: {type(result)}")
                return json.dumps({"actions": []}, indent=2)

        except Exception as e:
            msg.warn(f"Agent execution failed: {e}")
            return json.dumps({"actions": []}, indent=2)
    except Exception as e:
        msg.fail(f"Error parsing actions: {e}")
        raise ValueError(f"Failed to parse actions: {e}")
