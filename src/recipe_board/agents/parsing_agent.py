import os
from smolagents import InferenceClientModel, CodeAgent, RunResult
from smolagents.agent_types import AgentText
from .tools import (
    find_ingredients_in_sentence,
    find_equipment_in_sentence,
    filter_valid_actions,
    validate_action_structure,
)
from wasabi import msg
from ..core.recipe import Action
from ..core.state import RecipeSessionState, ParsingState
from ..core.logging_utils import safe_log_user_data

model = os.environ["HF_MODEL"]


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

        parsing_agent = CodeAgent(
            tools=[
                find_ingredients_in_sentence,
                find_equipment_in_sentence,
                filter_valid_actions,
                validate_action_structure,
            ],
            model=hf_model,
            additional_authorized_imports=["json"],
            max_steps=10,
        )
    except Exception as e:
        msg.fail(f"Error creating agent: {e}")
        raise ValueError(f"Failed to create agent: {e}")

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

Available ingredients are stored in: `available_ingredients`

Available equipment is stored in: `available_ingredients`

Available basic actions (with id, action_sentence; identified, but not yet associated with ingredients nor equipment): are stored in `available_actions`

=== The original Recipe ===
{state.raw_text}
=== end original recipe ===

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
1. For each basic action, use its sentence to find ingredients/equipment:
   - find_ingredients_in_sentence(sentence=action.sentence, ingredient_names=ingredient_list)
   - find_equipment_in_sentence(sentence=action.sentence, equipment_names=equipment_list)
2. Create action objects linking verbs to the appropriate ingredient/equipment IDs
3. Call filter_valid_actions(actions=validated_actions)
4. OUTPUT FINAL JSON: {{"actions": [filtered_actions]}}

Process each basic action systematically, matching ingredients and equipment within each sentence context.
Use the filtering tools at the end instead of writing your own filtering code.
"""

    # Run the agent
    try:
        state.parsing_state = ParsingState.PARSING_DEPENDENCIES
        result = parsing_agent.run(
            agent_prompt,
            additional_args={
                "available_ingredients": state.ingredients,
                "available_equipment": state.equipment,
                "available_actions": basic_actions_info,
            },
        )

        # Try to extract JSON from the result and convert to Action objects
        actions_data = None
        if isinstance(result, dict):
            msg.info("We received the response in the expected format - a `dict` !")
            actions_data = result.get("actions", [])
        elif isinstance(result, RunResult):
            safe_log_user_data(msg.info, f"Agent result: {result.output[0:25]}...")
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
        elif isinstance(result, AgentText):
            safe_log_user_data(
                msg.info, f"Agent returned AgentText: {str(result)[:50]}..."
            )
            raw = str(result)
            # Look for JSON in the response
            import re

            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                try:
                    # Validate JSON
                    parsed = json.loads(json_str)
                    actions_data = parsed.get("actions", [])
                    msg.info(
                        f"Successfully extracted {len(actions_data)} actions from AgentText"
                    )
                except json.JSONDecodeError as e:
                    msg.warn(f"Invalid JSON in AgentText response: {e}")
                    actions_data = []
            else:
                # No JSON found
                msg.warn("No JSON found in AgentText response")
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
                    equipment_id=action_item.get("equipment_id", ""),
                )
                actions.append(action)
            except Exception as e:
                msg.warn(f"Failed to create action from {action_item}: {e}")
                continue

        state.actions = actions
        state.parsing_state = ParsingState.COMPLETED
        return state

    except Exception as e:
        msg.warn(f"Agent execution failed: {e}")
        state.parsing_state = ParsingState.ERROR
        return state
