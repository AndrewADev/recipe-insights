#!/usr/bin/env python3
"""Debug test for parse_dependencies function using monkeypatch approach."""

from recipe_board.agents.models import parse_dependencies
from recipe_board.core.state import ParsingState, RecipeSessionState
from recipe_board.core.recipe import Ingredient, Equipment, BasicAction

def test_parse_dependencies_success(monkeypatch):
    """Test parse_dependencies with mocked agent response (new state-based API)."""

    # Mock the agent.run method to return a dict response
    mock_response = {
        "actions": [
            {
                "name": "mix",
                "ingredient_ids": ["ing1", "ing2"],
                "equipment_id": "eq1"
            },
            {
                "name": "whisk",
                "ingredient_ids": ["ing1", "ing2"],
                "equipment_id": "eq2"
            }
        ]
    }

    def mock_agent_run(self, prompt):
        print(f"Mock agent received prompt: {prompt[:100]}...")
        return mock_response

    # Mock the CodeAgent.run method
    monkeypatch.setattr("recipe_board.agents.models.CodeAgent.run", mock_agent_run)

    # Create test state with ingredients and equipment
    state = RecipeSessionState()
    state.raw_text = "Mix the flour and salt in a large mixing bowl. Whisk the ingredients together."
    state.ingredients = [
        Ingredient(name="flour", amount=2.0, unit="cups", modifiers=["all-purpose"], raw_text="2 cups flour"),
        Ingredient(name="salt", amount=1.0, unit="tsp", modifiers=[], raw_text="1 tsp salt")
    ]
    state.equipment = [
        Equipment(name="mixing bowl", required=True, modifiers="large"),
        Equipment(name="whisk", required=True, modifiers=None)
    ]

    # Add basic actions (required for new two-pass approach)
    state.basic_actions = [
        BasicAction(verb="mix", sentence="Mix the flour and salt in a large mixing bowl.", sentence_index=0),
        BasicAction(verb="whisk", sentence="Whisk the ingredients together.", sentence_index=1)
    ]

    # Test the function
    result = parse_dependencies(state)

    print(f"Result type: {type(result)}")
    print(f"Actions count: {len(result.actions)}")

    # Verify it returns updated state with actions
    assert isinstance(result, RecipeSessionState)
    assert len(result.actions) == 2
    assert result.actions[0].name == "mix"
    assert result.actions[1].name == "whisk"
    assert result.parsing_state == ParsingState.COMPLETED

def test_parse_dependencies_missing_env_vars(monkeypatch):
    """Test parse_dependencies when environment variables are missing."""
    import pytest

    # Remove the environment variables
    monkeypatch.delenv("HF_MODEL", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)

    # Create test state
    state = RecipeSessionState()
    state.raw_text = "Mix the flour in a large mixing bowl."
    state.ingredients = [
        Ingredient(name="flour", amount=2.0, unit="cups", modifiers=["all-purpose"], raw_text="2 cups flour")
    ]
    state.equipment = [
        Equipment(name="mixing bowl", required=True, modifiers="large")
    ]

    # Add basic actions (required for new two-pass approach)
    state.basic_actions = [
        BasicAction(verb="mix", sentence="Mix the flour in a large mixing bowl.", sentence_index=0)
    ]

    # Test that it raises ValueError when env vars are missing
    with pytest.raises(ValueError, match="Failed to create agent"):
        parse_dependencies(state)
