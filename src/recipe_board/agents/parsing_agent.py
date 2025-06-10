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

# Global spaCy model cache for performance
_spacy_nlp = None


def _get_spacy_model():
    """Get cached spaCy model, loading it if necessary."""
    global _spacy_nlp
    if _spacy_nlp is None:
        import spacy
        from spacy.language import Language

        try:
            _spacy_nlp = spacy.load("en_core_web_lg")
        except OSError:
            # Fallback to smaller model if large model not available
            _spacy_nlp = spacy.load("en_core_web_sm")

        # Register custom sentence boundary component for measurement units
        @Language.component("unit_sentence_boundaries")
        def unit_sentence_boundaries(doc):
            """Ensure measurement units at sentence ends are properly detected as boundaries."""
            for i, token in enumerate(doc[:-1]):
                # Handle temperature patterns where F/C and period are in same token (like "350F.")
                if token.text.endswith(("F.", "C.")) and i + 1 < len(doc):
                    doc[i + 1].is_sent_start = True
                # Handle degree symbols with period in same token "350°F." and "180°C."
                elif token.text.endswith(("°F.", "°C.")) and i + 1 < len(doc):
                    doc[i + 1].is_sent_start = True
                # Handle separated tokens: "350F" + "."
                elif (
                    token.text.endswith(("F", "C"))
                    and i + 1 < len(doc)
                    and doc[i + 1].text == "."
                    and i + 2 < len(doc)
                ):
                    doc[i + 2].is_sent_start = True
                # Handle separated degree symbols: "350°F" + "."
                elif (
                    token.text.endswith(("°F", "°C"))
                    and i + 1 < len(doc)
                    and doc[i + 1].text == "."
                    and i + 2 < len(doc)
                ):
                    doc[i + 2].is_sent_start = True
            return doc

        _spacy_nlp.add_pipe("unit_sentence_boundaries", before="parser")

    return _spacy_nlp


def _build_sentence_context(raw_text: str) -> dict[int, str]:
    """Build indexed sentence context from recipe text using spaCy.

    Args:
        raw_text: The raw recipe text

    Returns:
        Dictionary mapping sentence index to sentence text (consecutive indexing)
    """
    nlp = _get_spacy_model()

    # Process text with spaCy for sentence segmentation
    doc = nlp(raw_text)

    # Build sentence context mapping with consecutive indexing
    sentence_context = {}
    index = 0
    for sent in doc.sents:
        sentence_text = sent.text.strip()
        if sentence_text:  # Only include non-empty sentences
            sentence_context[index] = sentence_text
            index += 1

    return sentence_context


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
You are a recipe analysis expert. Your task is to link pre-identified cooking verbs to specific ingredients and equipment using sentence context.

You have access to these tools:
- find_ingredients_in_sentence: Find ingredient names in a single sentence
- find_equipment_in_sentence: Find equipment names in a single sentence
- filter_valid_actions: Remove actions that have no ingredients or equipment
- validate_action_structure: Ensure actions have proper structure and field types

Available data:
- `available_ingredients`: List of ingredient objects with IDs and names
- `available_equipment`: List of equipment objects with IDs and names
- `available_actions`: Basic actions with verb, sentence, and sentence_index
- `sentence_context`: Dict mapping sentence index → sentence text for context analysis

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

ENHANCED CONTEXT ANALYSIS:
For each basic action, analyze not just the action sentence, but also check the 2 preceding sentences for additional context:

1. Get the action's sentence_index from `available_actions`
2. Look up the sentence in `sentence_context[sentence_index]`
3. Also check `sentence_context[sentence_index-1]` and `sentence_context[sentence_index-2]` (if they exist)
4. Use ALL relevant sentences when calling the tools:
   - find_ingredients_in_sentence(sentence=combined_context, ingredient_names=ingredient_list)
   - find_equipment_in_sentence(sentence=combined_context, equipment_names=equipment_list)

This context analysis helps capture ingredients/equipment mentioned in previous sentences that are still relevant to the current action.

Steps:
1. For each basic action, build context from current + preceding sentences
2. Use the expanded context to find ingredients/equipment with tools
3. Create action objects linking verbs to the appropriate ingredient/equipment IDs
4. Call filter_valid_actions(actions=validated_actions)
5. OUTPUT FINAL JSON: {{"actions": [filtered_actions]}}

Process each basic action systematically, using sentence context for better dependency detection.
"""

    # Build sentence context for enhanced dependency detection
    sentence_context = _build_sentence_context(state.raw_text)
    msg.info(f"Built sentence context with {len(sentence_context)} sentences")

    # Run the agent
    try:
        state.parsing_state = ParsingState.PARSING_DEPENDENCIES
        result = parsing_agent.run(
            agent_prompt,
            additional_args={
                "available_ingredients": state.ingredients,
                "available_equipment": state.equipment,
                "available_actions": basic_actions_info,
                "sentence_context": sentence_context,
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
