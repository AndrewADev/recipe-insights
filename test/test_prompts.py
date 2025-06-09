import pytest
from recipe_board.core.recipe import Ingredient, Equipment
from recipe_board.agents.prompts import build_parse_actions_prompt


class TestBuildParseActionsPrompt:
    """Test suite for build_parse_actions_prompt function."""

    def test_build_parse_actions_prompt_empty_lists(self):
        """Test prompt generation with empty ingredient and equipment lists."""
        ingredients = []
        equipment = []

        result = build_parse_actions_prompt(ingredients, equipment)

        # Should contain the basic prompt structure
        assert "kitchen operations GURU" in result
        assert "Return ONLY valid JSON" in result
        assert "Recipe to parse:" in result
        assert "The parsed Ingredients with their IDs:" in result
        assert "The parsed Equipment with their IDs:" in result
        assert "[]" in result  # Empty lists should be represented

    def test_build_parse_actions_prompt_single_items(self):
        """Test prompt generation with single ingredient and equipment."""
        ingredients = [
            Ingredient(
                name="flour",
                amount=2.0,
                unit="cups",
                modifiers=["all-purpose"],
                raw_text="2 cups all-purpose flour"
            )
        ]
        equipment = [
            Equipment(
                name="mixing bowl",
                required=True,
                modifiers="large"
            )
        ]

        result = build_parse_actions_prompt(ingredients, equipment)

        # Should contain ingredient details
        assert "flour" in result
        assert "2.0" in result
        assert "cups" in result
        assert ingredients[0].id in result

        # Should contain equipment details
        assert "mixing bowl" in result
        assert equipment[0].id in result

        # Should maintain prompt structure
        assert "kitchen operations GURU" in result
        assert "Recipe to parse:" in result

    def test_build_parse_actions_prompt_multiple_items(self):
        """Test prompt generation with multiple ingredients and equipment."""
        ingredients = [
            Ingredient(
                name="flour",
                amount=2.0,
                unit="cups",
                modifiers=["all-purpose"],
                raw_text="2 cups all-purpose flour"
            ),
            Ingredient(
                name="salt",
                amount=1.0,
                unit="tsp",
                modifiers=[],
                raw_text="1 tsp salt"
            ),
            Ingredient(
                name="water",
                amount=1.0,
                unit="cup",
                modifiers=["warm"],
                raw_text="1 cup warm water"
            )
        ]
        equipment = [
            Equipment(name="mixing bowl", required=True, modifiers="large"),
            Equipment(name="wooden spoon", required=True, modifiers=None)
        ]

        result = build_parse_actions_prompt(ingredients, equipment)

        # Should contain all ingredient names and IDs
        assert "flour" in result
        assert "salt" in result
        assert "water" in result
        assert ingredients[0].id in result
        assert ingredients[1].id in result
        assert ingredients[2].id in result

        # Should contain all equipment names and IDs
        assert "mixing bowl" in result
        assert "wooden spoon" in result
        assert equipment[0].id in result
        assert equipment[1].id in result

        # Should maintain prompt structure
        assert "kitchen operations GURU" in result
        assert "ingredient_id" in result
        assert "equipment_id" in result

    def test_build_parse_actions_prompt_structure(self):
        """Test that prompt maintains required structure and instructions."""
        ingredients = [
            Ingredient(
                name="test ingredient",
                amount=1.0,
                unit="unit",
                modifiers=[],
                raw_text="test"
            )
        ]
        equipment = [
            Equipment(name="test equipment", required=True, modifiers=None)
        ]

        result = build_parse_actions_prompt(ingredients, equipment)

        # Should contain key instruction elements
        assert "Return ONLY valid JSON" in result
        assert "Do not include markdown code blocks" in result
        assert "Use the Ingredient and Equipment IDs provided" in result
        assert "DO NOT generate your own" in result

        # Should contain JSON structure example
        assert '"actions"' in result
        assert '"name"' in result
        assert 'ingredient_id' in result
        assert 'equipment_id' in result

    def test_build_parse_actions_prompt_ids_are_unique(self):
        """Test that generated IDs are actually unique across multiple calls."""
        ingredients = [
            Ingredient(
                name="flour",
                amount=2.0,
                unit="cups",
                modifiers=[],
                raw_text="2 cups flour"
            )
        ]
        equipment = [
            Equipment(name="bowl", required=True, modifiers=None)
        ]

        result1 = build_parse_actions_prompt(ingredients, equipment)

        # Create new instances (should have different IDs)
        ingredients2 = [
            Ingredient(
                name="flour",
                amount=2.0,
                unit="cups",
                modifiers=[],
                raw_text="2 cups flour"
            )
        ]
        equipment2 = [
            Equipment(name="bowl", required=True, modifiers=None)
        ]

        result2 = build_parse_actions_prompt(ingredients2, equipment2)

        # IDs should be different even for identical content
        assert ingredients[0].id != ingredients2[0].id
        assert equipment[0].id != equipment2[0].id
        assert ingredients[0].id in result1
        assert ingredients2[0].id in result2
        assert ingredients[0].id not in result2
        assert ingredients2[0].id not in result1
