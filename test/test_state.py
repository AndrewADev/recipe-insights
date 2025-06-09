from recipe_board.core.state import RecipeSessionState
from recipe_board.core.recipe import Ingredient, Equipment, Action, BasicAction


class TestRecipeSessionState:
    """Test suite for RecipeSessionState class."""

    def test_initial_state(self):
        """Test that state is initialized with correct default values."""
        state = RecipeSessionState()

        assert state.raw_text == ""
        assert state.ingredients == []
        assert state.equipment == []
        assert state.actions == []
        assert state.workflow_step == "initial"

    def test_has_parsed_data_empty(self):
        """Test has_parsed_data returns False when no data is present."""
        state = RecipeSessionState()
        assert state.has_parsed_data() == False

    def test_has_parsed_data_ingredients_only(self):
        """Test has_parsed_data returns False when only ingredients are present."""
        state = RecipeSessionState()
        state.ingredients = [
            Ingredient(name="flour", amount=2.0, unit="cups", modifiers=[], raw_text="2 cups flour")
        ]
        assert state.has_parsed_data() == False

    def test_has_parsed_data_equipment_only(self):
        """Test has_parsed_data returns False when only equipment is present."""
        state = RecipeSessionState()
        state.equipment = [
            Equipment(name="mixing bowl", required=True, modifiers=None)
        ]
        assert state.has_parsed_data() == False

    def test_has_parsed_data_both_present(self):
        """Test has_parsed_data returns True when both ingredients and equipment are present."""
        state = RecipeSessionState()
        state.ingredients = [
            Ingredient(name="flour", amount=2.0, unit="cups", modifiers=[], raw_text="2 cups flour")
        ]
        state.equipment = [
            Equipment(name="mixing bowl", required=True, modifiers=None)
        ]
        assert state.has_parsed_data() == True

    def test_clear(self):
        """Test clear method resets all fields to initial values."""
        state = RecipeSessionState()

        # Populate state with data
        state.raw_text = "Some recipe text"
        state.ingredients = [
            Ingredient(name="flour", amount=2.0, unit="cups", modifiers=[], raw_text="2 cups flour")
        ]
        state.equipment = [
            Equipment(name="mixing bowl", required=True, modifiers=None)
        ]
        state.actions = [
            Action(name="mix", ingredient_ids=["id1"], equipment_ids="eq1")
        ]
        state.workflow_step = "parsed"

        # Clear state
        state.clear()

        # Verify all fields are reset
        assert state.raw_text == ""
        assert state.ingredients == []
        assert state.equipment == []
        assert state.actions == []
        assert state.workflow_step == "initial"

    def test_to_dict_empty_state(self):
        """Test to_dict method with empty state."""
        state = RecipeSessionState()

        result = state.to_dict()

        expected = {
            "raw_text": "",
            "ingredients": [],
            "equipment": [],
            "basic_actions": [],
            "actions": [],
            "workflow_step": "initial"
        }
        assert result == expected

    def test_to_dict_populated_state(self):
        """Test to_dict method with populated state."""
        state = RecipeSessionState()
        state.raw_text = "Test recipe"
        state.ingredients = [
            Ingredient(name="flour", amount=2.0, unit="cups", modifiers=["all-purpose"], raw_text="2 cups flour")
        ]
        state.equipment = [
            Equipment(name="mixing bowl", required=True, modifiers="large")
        ]
        state.basic_actions = [
            BasicAction(verb="mix", sentence="Mix flour in bowl.", sentence_index=0)
        ]
        state.actions = [
            Action(name="mix", ingredient_ids=["ing1"], equipment_ids="eq1")
        ]
        state.workflow_step = "parsed"

        result = state.to_dict()

        # Verify structure
        assert "raw_text" in result
        assert "ingredients" in result
        assert "equipment" in result
        assert "basic_actions" in result
        assert "actions" in result
        assert "workflow_step" in result

        assert result["raw_text"] == "Test recipe"
        assert result["workflow_step"] == "parsed"
        assert len(result["ingredients"]) == 1
        assert len(result["basic_actions"]) == 1
        assert len(result["equipment"]) == 1
        assert len(result["actions"]) == 1

        # Verify ingredients are serialized correctly
        ingredient_dict = result["ingredients"][0]
        assert ingredient_dict["name"] == "flour"
        assert ingredient_dict["amount"] == 2.0
        assert ingredient_dict["unit"] == "cups"
        assert ingredient_dict["modifiers"] == ["all-purpose"]

    def test_format_ingredients_for_display_empty(self):
        """Test ingredients formatting with empty list."""
        state = RecipeSessionState()

        result = state.format_ingredients_for_display()

        assert result == "No ingredients parsed yet."

    def test_format_ingredients_for_display_populated(self):
        """Test ingredients formatting with populated list."""
        state = RecipeSessionState()
        state.ingredients = [
            Ingredient(name="flour", amount=2.0, unit="cups", modifiers=["all-purpose"], raw_text="2 cups flour"),
            Ingredient(name="salt", amount=1.0, unit="tsp", modifiers=[], raw_text="1 tsp salt"),
            Ingredient(name="onion", amount=1.0, unit=None, modifiers=["large", "diced"], raw_text="1 large onion, diced")
        ]

        result = state.format_ingredients_for_display()

        expected_lines = [
            "- 2.0 cups flour (all-purpose)",
            "- 1.0 tsp salt",
            "- 1.0 onion (large, diced)"
        ]
        expected = "\n".join(expected_lines)

        assert result == expected

    def test_format_equipment_for_display_empty(self):
        """Test equipment formatting with empty list."""
        state = RecipeSessionState()

        result = state.format_equipment_for_display()

        assert result == "No equipment parsed yet."

    def test_format_equipment_for_display_populated(self):
        """Test equipment formatting with populated list."""
        state = RecipeSessionState()
        state.equipment = [
            Equipment(name="mixing bowl", required=True, modifiers="large"),
            Equipment(name="whisk", required=False, modifiers=None),
            Equipment(name="oven", required=True, modifiers="preheated to 350°F")
        ]

        result = state.format_equipment_for_display()

        expected_lines = [
            "- mixing bowl (large) [required]",
            "- whisk",
            "- oven (preheated to 350°F) [required]"
        ]
        expected = "\n".join(expected_lines)

        assert result == expected

    def test_format_actions_for_display_empty(self):
        """Test actions formatting with empty list."""
        state = RecipeSessionState()

        result = state.format_actions_for_display()

        assert result == "No actions parsed yet."

    def test_format_actions_for_display_populated(self):
        """Test actions formatting with populated list."""
        state = RecipeSessionState()

        # Set up ingredients and equipment with known IDs
        flour = Ingredient(name="flour", amount=2.0, unit="cups", modifiers=[], raw_text="2 cups flour")
        salt = Ingredient(name="salt", amount=1.0, unit="tsp", modifiers=[], raw_text="1 tsp salt")
        bowl = Equipment(name="mixing bowl", required=True, modifiers="large")
        whisk = Equipment(name="whisk", required=True, modifiers=None)

        state.ingredients = [flour, salt]
        state.equipment = [bowl, whisk]

        # Create actions that reference the ingredient and equipment IDs
        state.actions = [
            Action(name="mix", ingredient_ids=[flour.id, salt.id], equipment_ids=bowl.id),
            Action(name="whisk", ingredient_ids=[flour.id], equipment_ids=whisk.id)
        ]

        result = state.format_actions_for_display()

        # Verify the format includes action names, ingredients, and equipment
        assert "Action: mix" in result
        assert "Action: whisk" in result
        assert "Ingredients: flour, salt" in result
        assert "Ingredients: flour" in result
        assert "Equipment: mixing bowl" in result
        assert "Equipment: whisk" in result

    def test_format_actions_for_display_with_missing_references(self):
        """Test actions formatting when ingredient/equipment IDs don't match."""
        state = RecipeSessionState()

        # Set up ingredients and equipment
        flour = Ingredient(name="flour", amount=2.0, unit="cups", modifiers=[], raw_text="2 cups flour")
        bowl = Equipment(name="mixing bowl", required=True, modifiers="large")

        state.ingredients = [flour]
        state.equipment = [bowl]

        # Create action with non-existent IDs
        state.actions = [
            Action(name="mix", ingredient_ids=["nonexistent-id"], equipment_ids="another-nonexistent-id")
        ]

        result = state.format_actions_for_display()

        # Should still show action name but with empty ingredient/equipment lists
        assert "Action: mix" in result
        assert "Ingredients:" in result
        assert "Equipment:" in result

    def test_workflow_step_progression(self):
        """Test workflow step can be updated to track processing state."""
        state = RecipeSessionState()

        # Initial state
        assert state.workflow_step == "initial"

        # Update workflow step
        state.workflow_step = "parsing"
        assert state.workflow_step == "parsing"

        state.workflow_step = "parsed"
        assert state.workflow_step == "parsed"

        state.workflow_step = "actions_parsed"
        assert state.workflow_step == "actions_parsed"

    def test_state_with_complex_data(self):
        """Test state behavior with complex, realistic data."""
        state = RecipeSessionState()
        state.raw_text = "Mix 2 cups flour with 1 tsp salt in a large bowl. Whisk until combined."

        # Add ingredients with various properties
        state.ingredients = [
            Ingredient(name="flour", amount=2.0, unit="cups", modifiers=["all-purpose"], raw_text="2 cups all-purpose flour"),
            Ingredient(name="salt", amount=1.0, unit="tsp", modifiers=["kosher"], raw_text="1 tsp kosher salt")
        ]

        # Add equipment
        bowl = Equipment(name="large bowl", required=True, modifiers="mixing")
        whisk = Equipment(name="whisk", required=True, modifiers=None)
        state.equipment = [bowl, whisk]

        # Add actions
        state.actions = [
            Action(name="mix", ingredient_ids=[state.ingredients[0].id, state.ingredients[1].id], equipment_ids=bowl.id),
            Action(name="whisk", ingredient_ids=[state.ingredients[0].id], equipment_ids=whisk.id)
        ]

        state.workflow_step = "actions_parsed"

        # Test all methods work together
        assert state.has_parsed_data() == True

        ingredients_display = state.format_ingredients_for_display()
        assert "flour" in ingredients_display
        assert "salt" in ingredients_display
        assert "all-purpose" in ingredients_display

        equipment_display = state.format_equipment_for_display()
        assert "large bowl" in equipment_display
        assert "whisk" in equipment_display

        actions_display = state.format_actions_for_display()
        assert "mix" in actions_display
        assert "whisk" in actions_display

        # Test serialization
        state_dict = state.to_dict()
        assert len(state_dict["ingredients"]) == 2
        assert len(state_dict["equipment"]) == 2
        assert len(state_dict["actions"]) == 2
        assert state_dict["workflow_step"] == "actions_parsed"
