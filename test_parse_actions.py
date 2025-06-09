#!/usr/bin/env python3
"""Debug test for parse_actions function using monkeypatch approach."""

import json
from recipe_board.agents.models import parse_actions

def test_parse_actions_success(monkeypatch):
    """Test parse_actions with mocked agent response."""

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

    # Sample inputs
    parsed_recipe_json = json.dumps({
        "ingredients": [
            {"name": "flour", "amount": 2.0, "unit": "cups", "modifiers": ["all-purpose"]},
            {"name": "salt", "amount": 1.0, "unit": "tsp", "modifiers": []}
        ],
        "equipment": [
            {"name": "mixing bowl", "required": True, "modifiers": "large"},
            {"name": "whisk", "required": True, "modifiers": None}
        ]
    })

    recipe_text = "Mix the flour and salt in a large mixing bowl. Whisk the ingredients together."

    # Test the function
    result = parse_actions(recipe_text, parsed_recipe_json)

    print(f"Result type: {type(result)}")
    print(f"Result: {result}")

    # Verify it returns valid JSON
    parsed_result = json.loads(result)
    assert "actions" in parsed_result
    assert len(parsed_result["actions"]) == 2
    assert parsed_result["actions"][0]["name"] == "mix"

def test_parse_actions_missing_env_vars(monkeypatch):
    """Test parse_actions when environment variables are missing."""
    import pytest

    # Remove the environment variables
    monkeypatch.delenv("HF_MODEL", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)

    # Sample inputs
    parsed_recipe_json = json.dumps({
        "ingredients": [
            {"name": "flour", "amount": 2.0, "unit": "cups", "modifiers": ["all-purpose"]}
        ],
        "equipment": [
            {"name": "mixing bowl", "required": True, "modifiers": "large"}
        ]
    })

    recipe_text = "Mix the flour in a large mixing bowl."

    # Test that it raises ValueError when env vars are missing
    with pytest.raises(ValueError, match="Failed to create agent"):
        parse_actions(recipe_text, parsed_recipe_json)

def test_parse_actions(monkeypatch):
    """Test parse_actions with mocked agent response."""

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

    # Sample inputs
    parsed_recipe_json = json.dumps({
        "ingredients": [
            {"name": "flour", "amount": 2.0, "unit": "cups", "modifiers": ["all-purpose"]},
            {"name": "salt", "amount": 1.0, "unit": "tsp", "modifiers": []}
        ],
        "equipment": [
            {"name": "mixing bowl", "required": True, "modifiers": "large"},
            {"name": "whisk", "required": True, "modifiers": None}
        ]
    })

    recipe_text = "Mix the flour and salt in a large mixing bowl. Whisk the ingredients together."

    # Test the function
    result = parse_actions(recipe_text, parsed_recipe_json)

    print(f"Result type: {type(result)}")
    print(f"Result: {result}")

    # Verify it returns valid JSON
    parsed_result = json.loads(result)
    assert "actions" in parsed_result
    assert len(parsed_result["actions"]) == 2
    assert parsed_result["actions"][0]["name"] == "mix"
