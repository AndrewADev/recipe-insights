#!/usr/bin/env python3
"""Debug test for parse_actions function using monkeypatch approach."""

from recipe_board.agents.models import parse_actions
from recipe_board.core.state import RecipeSessionState
from recipe_board.core.recipe import Ingredient, Equipment

def test_parse_actions_success(monkeypatch):
    """Test parse_actions with mocked agent response (new state-based API)."""

    # Mock the agent.run method to return a dict response
    mock_response = {
        "actions": [
            {
                "name": "mix",
                "ingredient_ids": ["ing1", "ing2"],
                "equipment_ids": "eq1"
            },
            {
                "name": "whisk",
                "ingredient_ids": ["ing1", "ing2"],
                "equipment_ids": "eq2"
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

    # Test the function
    result = parse_actions(state)

    print(f"Result type: {type(result)}")
    print(f"Actions count: {len(result.actions)}")

    # Verify it returns updated state with actions
    assert isinstance(result, RecipeSessionState)
    assert len(result.actions) == 2
    assert result.actions[0].name == "mix"
    assert result.actions[1].name == "whisk"
    assert result.workflow_step == "actions_parsed"

def test_parse_actions_missing_env_vars(monkeypatch):
    """Test parse_actions when environment variables are missing."""
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

    # Test that it raises ValueError when env vars are missing
    with pytest.raises(ValueError, match="Failed to create agent"):
        parse_actions(state)
