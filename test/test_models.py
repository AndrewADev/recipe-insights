import json
import pytest
from recipe_board.agents.models import parse_recipe, parse_dependencies, ingredients_and_equipment_from_parsed_recipe
from recipe_board.core.state import RecipeSessionState, ParsingState
from recipe_board.core.recipe import Ingredient, Equipment, BasicAction
from smolagents.agent_types import AgentText


class TestIngredientsAndEquipmentFromParsedRecipe:
    """Test suite for ingredients_and_equipment_from_parsed_recipe function."""

    def test_valid_complete_json(self):
        """Test parsing valid JSON with complete data."""
        json_data = json.dumps({
            "ingredients": [
                {"name": "flour", "amount": 2.0, "unit": "cups", "modifiers": ["all-purpose"]},
                {"name": "salt", "amount": 1.0, "unit": "tsp", "modifiers": None}
            ],
            "equipment": [
                {"name": "mixing bowl", "required": True, "modifiers": "large"},
                {"name": "whisk", "required": False, "modifiers": None}
            ]
        })

        ingredients, equipment = ingredients_and_equipment_from_parsed_recipe(json_data)

        # Verify ingredients
        assert len(ingredients) == 2
        assert ingredients[0].name == "flour"
        assert ingredients[0].amount == 2.0
        assert ingredients[0].unit == "cups"
        assert ingredients[0].modifiers == ["all-purpose"]
        assert "2.0 cups flour all-purpose" in ingredients[0].raw_text

        assert ingredients[1].name == "salt"
        assert ingredients[1].amount == 1.0
        assert ingredients[1].unit == "tsp"
        assert ingredients[1].modifiers == []

        # Verify equipment
        assert len(equipment) == 2
        assert equipment[0].name == "mixing bowl"
        assert equipment[0].required == True
        assert equipment[0].modifiers == "large"

        assert equipment[1].name == "whisk"
        assert equipment[1].required == False
        assert equipment[1].modifiers == None

    def test_string_modifiers_conversion(self):
        """Test conversion of string modifiers to list."""
        json_data = json.dumps({
            "ingredients": [
                {"name": "flour", "amount": 2.0, "unit": "cups", "modifiers": "all-purpose"}
            ],
            "equipment": []
        })

        ingredients, equipment = ingredients_and_equipment_from_parsed_recipe(json_data)

        assert len(ingredients) == 1
        assert ingredients[0].modifiers == ["all-purpose"]

    def test_missing_optional_fields(self):
        """Test handling of missing optional fields."""
        json_data = json.dumps({
            "ingredients": [
                {"name": "salt"}  # Missing amount, unit, modifiers
            ],
            "equipment": [
                {"name": "bowl"}  # Missing required, modifiers
            ]
        })

        ingredients, equipment = ingredients_and_equipment_from_parsed_recipe(json_data)

        assert len(ingredients) == 1
        assert ingredients[0].name == "salt"
        assert ingredients[0].amount == None
        assert ingredients[0].unit == None
        assert ingredients[0].modifiers == []
        assert ingredients[0].raw_text == "salt"

        assert len(equipment) == 1
        assert equipment[0].name == "bowl"
        assert equipment[0].required == True  # Default value
        assert equipment[0].modifiers == None

    def test_empty_arrays(self):
        """Test handling of empty ingredients and equipment arrays."""
        json_data = json.dumps({
            "ingredients": [],
            "equipment": []
        })

        ingredients, equipment = ingredients_and_equipment_from_parsed_recipe(json_data)

        assert len(ingredients) == 0
        assert len(equipment) == 0

    def test_invalid_json(self):
        """Test handling of invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            ingredients_and_equipment_from_parsed_recipe("not valid json")

    def test_missing_required_keys(self):
        """Test handling of missing required top-level keys."""
        # Missing equipment key
        json_data = json.dumps({"ingredients": []})
        with pytest.raises(ValueError, match="must contain 'ingredients' and 'equipment' keys"):
            ingredients_and_equipment_from_parsed_recipe(json_data)

        # Missing ingredients key
        json_data = json.dumps({"equipment": []})
        with pytest.raises(ValueError, match="must contain 'ingredients' and 'equipment' keys"):
            ingredients_and_equipment_from_parsed_recipe(json_data)

    def test_non_object_json(self):
        """Test handling of non-object JSON."""
        with pytest.raises(ValueError, match="JSON must be an object"):
            ingredients_and_equipment_from_parsed_recipe("[]")

        with pytest.raises(ValueError, match="JSON must be an object"):
            ingredients_and_equipment_from_parsed_recipe("\"string\"")

    def test_non_array_ingredients_equipment(self):
        """Test handling of non-array ingredients/equipment."""
        json_data = json.dumps({
            "ingredients": "not an array",
            "equipment": []
        })
        with pytest.raises(ValueError, match="'ingredients' must be an array"):
            ingredients_and_equipment_from_parsed_recipe(json_data)

        json_data = json.dumps({
            "ingredients": [],
            "equipment": "not an array"
        })
        with pytest.raises(ValueError, match="'equipment' must be an array"):
            ingredients_and_equipment_from_parsed_recipe(json_data)

    def test_invalid_ingredient_items_skipped(self):
        """Test that invalid ingredient items are skipped with warnings."""
        json_data = json.dumps({
            "ingredients": [
                {"name": "valid flour", "amount": 2.0},
                "invalid string item",
                {"name": "valid salt", "amount": 1.0}
            ],
            "equipment": []
        })

        ingredients, equipment = ingredients_and_equipment_from_parsed_recipe(json_data)

        # Should only get the valid ingredients
        assert len(ingredients) == 2
        assert ingredients[0].name == "valid flour"
        assert ingredients[1].name == "valid salt"

    def test_invalid_equipment_items_skipped(self):
        """Test that invalid equipment items are skipped with warnings."""
        json_data = json.dumps({
            "ingredients": [],
            "equipment": [
                {"name": "valid bowl"},
                "invalid string item",
                {"name": "valid spoon"}
            ]
        })

        ingredients, equipment = ingredients_and_equipment_from_parsed_recipe(json_data)

        # Should only get the valid equipment
        assert len(equipment) == 2
        assert equipment[0].name == "valid bowl"
        assert equipment[1].name == "valid spoon"

    def test_raw_text_generation(self):
        """Test proper raw_text generation from components."""
        json_data = json.dumps({
            "ingredients": [
                {"name": "flour", "amount": 2.5, "unit": "cups", "modifiers": ["all-purpose", "sifted"]},
                {"name": "water", "amount": 1, "unit": "cup"},
                {"name": "salt"}
            ],
            "equipment": []
        })

        ingredients, equipment = ingredients_and_equipment_from_parsed_recipe(json_data)

        assert "2.5 cups flour all-purpose sifted" == ingredients[0].raw_text
        assert "1 cup water" == ingredients[1].raw_text
        assert "salt" == ingredients[2].raw_text

    def test_unique_ids_generated(self):
        """Test that unique IDs are generated for each object."""
        json_data = json.dumps({
            "ingredients": [
                {"name": "flour", "amount": 2.0},
                {"name": "salt", "amount": 1.0}
            ],
            "equipment": [
                {"name": "bowl"},
                {"name": "spoon"}
            ]
        })

        ingredients, equipment = ingredients_and_equipment_from_parsed_recipe(json_data)

        # All IDs should be unique
        all_ids = [ing.id for ing in ingredients] + [eq.id for eq in equipment]
        assert len(all_ids) == len(set(all_ids))  # No duplicates

        # All IDs should be valid UUIDs (basic check)
        for id_str in all_ids:
            assert len(id_str) == 36  # UUID string length
            assert id_str.count('-') == 4  # UUID format


class TestParseRecipeEquipment:
    """Test suite for parse_recipe function (new state-based API)."""

    def test_parse_recipe_with_markdown_code_blocks(self, monkeypatch):
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

        def mock_text_generation(*args, **kwargs):
            return mock_response

        monkeypatch.setattr(
            "recipe_board.agents.models.InferenceClient.text_generation",
            mock_text_generation
        )

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

    def test_parse_recipe_clean_json(self, monkeypatch):
        """Test parsing when response is already clean JSON."""
        mock_response = '{"equipment": [], "ingredients": [], "basic_actions": []}'

        def mock_text_generation(*args, **kwargs):
            return mock_response

        monkeypatch.setattr(
            "recipe_board.agents.models.InferenceClient.text_generation",
            mock_text_generation
        )

        result = parse_recipe("test recipe")

        # Verify empty state
        assert isinstance(result, RecipeSessionState)
        assert len(result.ingredients) == 0
        assert len(result.equipment) == 0
        assert len(result.basic_actions) == 0
        assert result.parsing_state == ParsingState.COMPLETED

    def test_parse_recipe_invalid_json(self, monkeypatch):
        """Test handling of invalid JSON response."""
        mock_response = "This is not valid JSON at all!"

        def mock_text_generation(*args, **kwargs):
            return mock_response

        monkeypatch.setattr(
            "recipe_board.agents.models.InferenceClient.text_generation",
            mock_text_generation
        )

        result = parse_recipe("test recipe")

        # Should return empty state when JSON parsing fails
        assert isinstance(result, RecipeSessionState)
        assert len(result.ingredients) == 0
        assert len(result.equipment) == 0
        assert result.raw_text == "test recipe"

    def test_parse_recipe_empty_response(self, monkeypatch):
        """Test handling of empty response."""
        def mock_text_generation(*args, **kwargs):
            return ""

        monkeypatch.setattr(
            "recipe_board.agents.models.InferenceClient.text_generation",
            mock_text_generation
        )

        result = parse_recipe("test recipe")

        # Should return empty state
        assert isinstance(result, RecipeSessionState)
        assert len(result.ingredients) == 0
        assert len(result.equipment) == 0

    def test_parse_recipe_none_response(self, monkeypatch):
        """Test handling of None response."""
        def mock_text_generation(*args, **kwargs):
            return None

        monkeypatch.setattr(
            "recipe_board.agents.models.InferenceClient.text_generation",
            mock_text_generation
        )

        result = parse_recipe("test recipe")

        # Should return empty state
        assert isinstance(result, RecipeSessionState)
        assert len(result.ingredients) == 0
        assert len(result.equipment) == 0


class TestBasicActionsAndDependencies:
    """Test suite for basic actions parsing and dependency parsing."""

    def test_basic_actions_creation(self):
        """Test that BasicAction objects are created correctly."""
        basic_action = BasicAction(
            verb="mix",
            sentence="Mix flour and salt in bowl.",
            sentence_index=1
        )

        assert basic_action.verb == "mix"
        assert basic_action.sentence == "Mix flour and salt in bowl."
        assert basic_action.sentence_index == 1

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

        {"actions": [{"name": "mix", "ingredient_ids": ["id1"], "equipment_ids": "eq1"}]}

        This JSON represents the cooking actions.
        '''

        mock_agent_text = AgentText(agent_text_content)

        # Mock the agent.run method to return AgentText
        def mock_agent_run(prompt):
            return mock_agent_text

        # Mock the agent creation and run
        from unittest.mock import MagicMock
        mock_agent = MagicMock()
        mock_agent.run.return_value = mock_agent_text

        def mock_code_agent(*args, **kwargs):
            return mock_agent

        monkeypatch.setattr("recipe_board.agents.models.CodeAgent", mock_code_agent)
        monkeypatch.setattr("recipe_board.agents.models.InferenceClientModel", lambda **kwargs: MagicMock())

        # Test the function
        result = parse_dependencies(state)

        # Should successfully parse actions from AgentText content
        assert len(result.actions) == 1
        assert result.actions[0].name == "mix"
        assert result.actions[0].ingredient_ids == ["id1"]
        assert result.actions[0].equipment_ids == "eq1"
