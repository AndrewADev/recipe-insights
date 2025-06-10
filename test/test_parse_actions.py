#!/usr/bin/env python3
"""Debug test for parse_dependencies function using monkeypatch approach."""

from recipe_board.agents.parsing_agent import parse_dependencies, _build_sentence_context
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

    def mock_agent_run(self, prompt, additional_args=None):
        print(f"Mock agent received prompt: {prompt[:100]}...")
        return mock_response

    # Mock the CodeAgent.run method
    monkeypatch.setattr("recipe_board.agents.parsing_agent.CodeAgent.run", mock_agent_run)

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


class TestSentenceContext:
    """Test suite for sentence context functionality."""

    def test_build_sentence_context_basic(self):
        """Test basic sentence context building with proper temperature boundaries."""
        recipe_text = "Heat the oven to 350F. Mix flour and salt in a bowl. Bake for 30 minutes."

        result = _build_sentence_context(recipe_text)

        assert isinstance(result, dict)
        assert len(result) == 3
        assert 0 in result
        assert 1 in result
        assert 2 in result
        assert result[0] == "Heat the oven to 350F."
        assert result[1] == "Mix flour and salt in a bowl."
        assert result[2] == "Bake for 30 minutes."

    def test_build_sentence_context_empty_text(self):
        """Test sentence context with empty text."""
        result = _build_sentence_context("")
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_build_sentence_context_whitespace_only(self):
        """Test sentence context with whitespace only."""
        result = _build_sentence_context("   \n\t   ")
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_build_sentence_context_single_sentence(self):
        """Test sentence context with single sentence."""
        recipe_text = "Mix everything together until smooth."

        result = _build_sentence_context(recipe_text)

        assert isinstance(result, dict)
        assert len(result) == 1
        assert 0 in result
        assert result[0] == "Mix everything together until smooth."

    def test_build_sentence_context_recipe_format(self):
        """Test sentence context with typical recipe formatting."""
        recipe_text = """Preheat oven to 375°F.

In a large bowl, combine flour, sugar, and salt. Add butter and mix until crumbly.
Press mixture into prepared pan. Bake until golden brown."""

        result = _build_sentence_context(recipe_text)

        assert isinstance(result, dict)
        assert len(result) >= 3  # Should detect multiple sentences

        # Check that sentences are properly extracted
        sentences = list(result.values())
        assert any("Preheat oven" in s for s in sentences)
        assert any("combine flour" in s for s in sentences)
        assert any("Bake until golden" in s for s in sentences)

    def test_build_sentence_context_with_lists(self):
        """Test sentence context with ingredient lists and numbered steps."""
        recipe_text = """Ingredients: 2 cups flour, 1 cup sugar, 1/2 cup butter.

1. Preheat oven to 350F.
2. Mix dry ingredients together.
3. Add butter and combine until mixture forms a dough."""

        result = _build_sentence_context(recipe_text)

        assert isinstance(result, dict)
        assert len(result) >= 4  # Should handle the different sentence structures

        # Verify some key content is captured
        sentences = list(result.values())
        assert any("Preheat oven" in s for s in sentences)
        assert any("Mix dry ingredients" in s for s in sentences)


def test_parse_dependencies_with_sentence_context(monkeypatch):
    """Test that parse_dependencies correctly builds and passes sentence context."""

    # Track what gets passed to the agent
    captured_args = {}

    def mock_agent_run(self, prompt, additional_args=None):
        # Capture the additional_args for verification
        captured_args.update(additional_args or {})
        return {
            "actions": [
                {
                    "name": "mix",
                    "ingredient_ids": ["ing1"],
                    "equipment_id": "eq1"
                }
            ]
        }

    # Mock the CodeAgent.run method
    monkeypatch.setattr("recipe_board.agents.parsing_agent.CodeAgent.run", mock_agent_run)

    # Create test state
    state = RecipeSessionState()
    state.raw_text = "Heat the oven to 350F. Mix the flour in a large bowl. Bake for 30 minutes."
    state.ingredients = [
        Ingredient(name="flour", amount=2.0, unit="cups", modifiers=[], raw_text="2 cups flour")
    ]
    state.equipment = [
        Equipment(name="bowl", required=True, modifiers="large")
    ]
    state.basic_actions = [
        BasicAction(verb="mix", sentence="Mix the flour in a large bowl.", sentence_index=1)
    ]

    # Run the function
    result = parse_dependencies(state)

    # Verify sentence_context was passed to the agent
    assert "sentence_context" in captured_args
    sentence_context = captured_args["sentence_context"]

    # Verify the sentence context is properly structured
    assert isinstance(sentence_context, dict)
    assert len(sentence_context) == 3  # Should have 3 sentences
    assert 0 in sentence_context
    assert 1 in sentence_context
    assert 2 in sentence_context
    assert "Heat the oven" in sentence_context[0]
    assert "Mix the flour" in sentence_context[1]
    assert "Bake for 30 minutes" in sentence_context[2]

    # Verify the function still works correctly
    assert result.parsing_state == ParsingState.COMPLETED
    assert len(result.actions) == 1
