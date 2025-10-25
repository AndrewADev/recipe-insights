import pytest
from unittest.mock import MagicMock
from recipe_board.agents.parsing_agent import parse_dependencies
from recipe_board.agents.entity_workflow import parse_recipe
from recipe_board.core.state import RecipeSessionState, ParsingState
from recipe_board.core.recipe import Ingredient, Equipment, BasicAction
from smolagents.agent_types import AgentText


@pytest.fixture
def mock_llm_response(monkeypatch):
    """Fixture to mock InferenceClient for parse_recipe tests.

    Returns a callable that accepts the mock response content and sets up the mock.
    """
    def _mock_response(content: str):
        mock_choice = MagicMock()
        mock_choice.message.content = content
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_chat_response

        def mock_inference_client(*args, **kwargs):
            return mock_client

        monkeypatch.setattr(
            "recipe_board.agents.entity_workflow.InferenceClient",
            mock_inference_client
        )

    return _mock_response


class TestParseRecipeEquipment:
    """Test suite for parse_recipe function (new state-based API)."""

    def test_parse_recipe_with_markdown_code_blocks(self, mock_llm_response):
        """Test that markdown code blocks are properly stripped from response."""
        mock_response = """```json
{
  "equipment": [
    {"name": "oven", "required": true, "modifiers": null},
    {"name": "mixing bowl", "required": true, "modifiers": "large"}
  ],
  "ingredients": [
    {"name": "flour", "amount": 2, "unit": "cups", "modifiers": null}
  ],
  "basic_actions": [
    {"verb": "mix", "sentence": "Mix flour in large bowl.", "sentence_index": 0}
  ]
}
```"""

        mock_llm_response(mock_response)
        result = parse_recipe("test recipe")

        # Verify result is RecipeSessionState
        assert isinstance(result, RecipeSessionState)
        assert result.raw_text == "test recipe"
        assert result.parsing_state == ParsingState.COMPLETED

        # Verify basic actions were parsed
        assert len(result.basic_actions) == 1
        assert result.basic_actions[0].verb == "mix"
        assert result.basic_actions[0].sentence == "Mix flour in large bowl."
        assert result.basic_actions[0].sentence_index == 0

        # Verify ingredients and equipment are parsed
        assert len(result.ingredients) == 1
        assert result.ingredients[0].name == "flour"
        assert result.ingredients[0].amount == 2
        assert result.ingredients[0].unit == "cups"

        assert len(result.equipment) == 2
        assert result.equipment[0].name == "oven"
        assert result.equipment[0].required == True
        assert result.equipment[1].name == "mixing bowl"

    def test_parse_recipe_clean_json(self, mock_llm_response):
        """Test parsing when response is already clean JSON."""
        mock_response = '{"equipment": [], "ingredients": [], "basic_actions": []}'

        mock_llm_response(mock_response)
        result = parse_recipe("test recipe")

        # Verify empty state
        assert isinstance(result, RecipeSessionState)
        assert len(result.ingredients) == 0
        assert len(result.equipment) == 0
        assert len(result.basic_actions) == 0
        assert result.parsing_state == ParsingState.COMPLETED

    def test_parse_recipe_invalid_json(self, mock_llm_response):
        """Test handling of invalid JSON response."""
        mock_response = "This is not valid JSON at all!"

        mock_llm_response(mock_response)
        result = parse_recipe("test recipe")

        # Should return empty state when JSON parsing fails
        assert isinstance(result, RecipeSessionState)
        assert len(result.ingredients) == 0
        assert len(result.equipment) == 0
        assert result.raw_text == "test recipe"

    def test_parse_recipe_empty_response(self, mock_llm_response):
        """Test handling of empty response."""
        mock_llm_response("")
        result = parse_recipe("test recipe")

        # Should return empty state
        assert isinstance(result, RecipeSessionState)
        assert len(result.ingredients) == 0
        assert len(result.equipment) == 0

    def test_parse_recipe_none_response(self, mock_llm_response):
        """Test handling of None response."""
        mock_llm_response(None)
        result = parse_recipe("test recipe")

        # Should return empty state
        assert isinstance(result, RecipeSessionState)
        assert len(result.ingredients) == 0
        assert len(result.equipment) == 0


class TestBasicActionsAndDependencies:
    """Test suite for basic actions parsing and dependency parsing."""

    def test_parse_dependencies_requires_basic_actions(self):
        """Test that parse_dependencies requires basic actions to be present."""
        state = RecipeSessionState()

        # Add ingredients and equipment but no basic actions
        state.ingredients = [Ingredient(name="flour", amount=2.0, unit="cups", modifiers=[], raw_text="2 cups flour")]
        state.equipment = [Equipment(name="bowl", required=True, modifiers=None)]
        # No basic_actions

        result = parse_dependencies(state)

        # Should return same state unchanged
        assert result == state
        assert len(result.actions) == 0

    def test_parse_dependencies_requires_ingredients_and_equipment(self):
        """Test that parse_dependencies requires ingredients and equipment."""
        state = RecipeSessionState()

        # Add basic actions but no ingredients/equipment
        state.basic_actions = [BasicAction(verb="mix", sentence="Mix ingredients.", sentence_index=0)]

        result = parse_dependencies(state)

        # Should return same state unchanged
        assert result == state
        assert len(result.actions) == 0

    def test_state_formatting_basic_actions(self):
        """Test the format_basic_actions_for_display method."""
        state = RecipeSessionState()

        # Test empty basic actions
        assert "No basic actions parsed yet." in state.format_basic_actions_for_display()

        # Test with basic actions
        state.basic_actions = [
            BasicAction(verb="mix", sentence="Mix flour and salt in large bowl with spoon.", sentence_index=0),
            BasicAction(verb="bake", sentence="Bake in preheated oven for 30 minutes.", sentence_index=1)
        ]

        display = state.format_basic_actions_for_display()
        assert "'mix' in: Mix flour and salt in large bowl with spoon..." in display
        assert "'bake' in: Bake in preheated oven for 30 minutes..." in display

    def test_parse_dependencies_with_agent_text_result(self, monkeypatch):
        """Test parse_dependencies when agent returns AgentText instance."""
        # Create state with valid ingredients, equipment and basic actions
        state = RecipeSessionState()
        state.ingredients = [
            Ingredient(name="flour", amount=2.0, unit="cups", modifiers=[], raw_text="2 cups flour")
        ]
        state.equipment = [
            Equipment(name="mixing bowl", required=True, modifiers=None)
        ]
        state.basic_actions = [
            BasicAction(verb="mix", sentence="Mix flour in mixing bowl.", sentence_index=0)
        ]

        # Mock agent that returns AgentText with JSON content
        agent_text_content = '''
        Based on the ingredients and equipment, here are the actions:

        {"actions": [{"name": "mix", "ingredient_ids": ["id1"], "equipment_id": "eq1"}]}

        This JSON represents the cooking actions.
        '''

        mock_agent_text = AgentText(agent_text_content)

        # Mock the agent creation and run
        from unittest.mock import MagicMock
        mock_agent = MagicMock()
        mock_agent.run.return_value = mock_agent_text

        def mock_code_agent(*args, **kwargs):
            return mock_agent

        monkeypatch.setattr("recipe_board.agents.parsing_agent.CodeAgent", mock_code_agent)
        monkeypatch.setattr("recipe_board.agents.parsing_agent.InferenceClientModel", lambda **kwargs: MagicMock())

        # Test the function
        result = parse_dependencies(state)

        # Should successfully parse actions from AgentText content
        assert len(result.actions) == 1
        assert result.actions[0].name == "mix"
        assert result.actions[0].ingredient_ids == ["id1"]
        assert result.actions[0].equipment_id == "eq1"
