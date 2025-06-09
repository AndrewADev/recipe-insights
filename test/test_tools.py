"""Tests for recipe parsing tools."""

import pytest
from recipe_board.agents.tools import (
    extract_verbs,
    find_ingredients_in_sentence,
    find_equipment_in_sentence,
    filter_valid_actions,
    validate_action_structure,
)


class TestExtractVerbs:
    """Test suite for extract_verbs tool."""

    def test_extract_verbs_simple_sentence(self):
        """Test verb extraction from simple sentence."""
        text = "Mix the flour with water."
        result = extract_verbs(text)

        assert len(result) == 1
        assert result[0]["verb"] == "Mix"
        assert result[0]["lemma"] == "mix"
        assert "flour" in result[0]["sentence"]

    def test_extract_verbs_multiple_sentences(self):
        """Test verb extraction from multiple sentences."""
        text = "Heat the oven. Mix flour and salt. Bake for 30 minutes."
        result = extract_verbs(text)

        verbs = [v["lemma"] for v in result]
        assert "heat" in verbs
        assert "mix" in verbs
        assert "bake" in verbs

    def test_extract_verbs_no_verbs(self):
        """Test verb extraction when no verbs present."""
        text = "Salt and pepper."
        result = extract_verbs(text)

        assert len(result) == 0

    def test_extract_verbs_empty_text(self):
        """Test verb extraction with empty text."""
        result = extract_verbs("")
        assert len(result) == 0


class TestFindIngredientsInSentence:
    """Test suite for find_ingredients_in_sentence tool."""

    def test_find_ingredients_basic_match(self):
        """Test finding ingredients in sentence."""
        sentence = "Add flour and salt to the bowl."
        ingredients = ["flour", "salt", "pepper", "water"]

        result = find_ingredients_in_sentence(sentence, ingredients)

        assert "flour" in result
        assert "salt" in result
        assert "pepper" not in result
        assert "water" not in result

    def test_find_ingredients_case_insensitive(self):
        """Test case-insensitive ingredient matching."""
        sentence = "Add FLOUR and Salt to the bowl."
        ingredients = ["flour", "salt"]

        result = find_ingredients_in_sentence(sentence, ingredients)

        assert "flour" in result
        assert "salt" in result

    def test_find_ingredients_no_matches(self):
        """Test when no ingredients found."""
        sentence = "Heat the oven to 350 degrees."
        ingredients = ["flour", "salt", "pepper"]

        result = find_ingredients_in_sentence(sentence, ingredients)

        assert len(result) == 0

    def test_find_ingredients_empty_lists(self):
        """Test with empty inputs."""
        result1 = find_ingredients_in_sentence("", ["flour"])
        result2 = find_ingredients_in_sentence("Add flour", [])

        assert len(result1) == 0
        assert len(result2) == 0


class TestFindEquipmentInSentence:
    """Test suite for find_equipment_in_sentence tool."""

    def test_find_equipment_basic_match(self):
        """Test finding equipment in sentence."""
        sentence = "Use a large mixing bowl and whisk."
        equipment = ["mixing bowl", "whisk", "oven", "pan"]

        result = find_equipment_in_sentence(sentence, equipment)

        assert "mixing bowl" in result
        assert "whisk" in result
        assert "oven" not in result
        assert "pan" not in result

    def test_find_equipment_partial_match(self):
        """Test partial equipment name matching."""
        sentence = "Put in the oven."
        equipment = ["oven", "mixing bowl"]

        result = find_equipment_in_sentence(sentence, equipment)

        assert "oven" in result
        assert "mixing bowl" not in result

    def test_find_equipment_case_insensitive(self):
        """Test case-insensitive equipment matching."""
        sentence = "Use a MIXING BOWL."
        equipment = ["mixing bowl", "whisk"]

        result = find_equipment_in_sentence(sentence, equipment)

        assert "mixing bowl" in result


class TestFilterValidActions:
    """Test suite for filter_valid_actions tool."""

    def test_filter_actions_with_ingredients(self):
        """Test filtering keeps actions with ingredients."""
        actions = [
            {"name": "mix", "ingredient_ids": ["id1", "id2"], "equipment_id": None},
            {"name": "heat", "ingredient_ids": [], "equipment_id": "oven_id"},
            {"name": "empty", "ingredient_ids": [], "equipment_id": None}
        ]

        result = filter_valid_actions(actions)

        assert len(result) == 2
        action_names = [a["name"] for a in result]
        assert "mix" in action_names
        assert "heat" in action_names
        assert "empty" not in action_names

    def test_filter_actions_with_equipment(self):
        """Test filtering keeps actions with equipment."""
        actions = [
            {"name": "bake", "ingredient_ids": [], "equipment_id": "oven_id"},
            {"name": "stir", "ingredient_ids": ["flour_id"], "equipment_id": ""},
            {"name": "wait", "ingredient_ids": [], "equipment_id": ""}
        ]

        result = filter_valid_actions(actions)

        assert len(result) == 2
        action_names = [a["name"] for a in result]
        assert "bake" in action_names
        assert "stir" in action_names
        assert "wait" not in action_names

    def test_filter_actions_missing_fields(self):
        """Test filtering handles missing fields gracefully."""
        actions = [
            {"name": "mix", "ingredient_ids": ["id1"]},  # Missing equipment_id
            {"name": "heat", "equipment_id": "oven_id"},  # Missing ingredient_ids
            {"name": "incomplete"}  # Missing both
        ]

        result = filter_valid_actions(actions)

        assert len(result) == 2
        action_names = [a["name"] for a in result]
        assert "mix" in action_names
        assert "heat" in action_names
        assert "incomplete" not in action_names

    def test_filter_actions_empty_list(self):
        """Test filtering empty actions list."""
        result = filter_valid_actions([])
        assert len(result) == 0

    def test_filter_actions_null_values(self):
        """Test filtering handles null and empty values."""
        actions = [
            {"name": "valid", "ingredient_ids": ["id1"], "equipment_id": None},
            {"name": "invalid1", "ingredient_ids": None, "equipment_id": None},
            {"name": "invalid2", "ingredient_ids": [], "equipment_id": ""},
            {"name": "invalid3", "ingredient_ids": [], "equipment_id": None}
        ]

        result = filter_valid_actions(actions)

        assert len(result) == 1
        assert result[0]["name"] == "valid"


class TestValidateActionStructure:
    """Test suite for validate_action_structure tool."""

    def test_validate_complete_actions(self):
        """Test validation of complete, well-formed actions."""
        actions = [
            {
                "name": "mix",
                "description": "Mix ingredients",
                "ingredient_ids": ["id1", "id2"],
                "equipment_id": "bowl_id"
            }
        ]

        result = validate_action_structure(actions)

        assert len(result) == 1
        assert result[0]["name"] == "mix"
        assert result[0]["description"] == "Mix ingredients"
        assert result[0]["ingredient_ids"] == ["id1", "id2"]
        assert result[0]["equipment_id"] == "bowl_id"

    def test_validate_missing_fields(self):
        """Test validation adds missing fields with defaults."""
        actions = [
            {"name": "mix"},  # Missing other fields
            {"ingredient_ids": ["id1"]}  # Missing name
        ]

        result = validate_action_structure(actions)

        assert len(result) == 2

        # First action
        assert result[0]["name"] == "mix"
        assert result[0]["description"] == ""
        assert result[0]["ingredient_ids"] == []
        assert result[0]["equipment_id"] is None

        # Second action
        assert result[1]["name"] == "unknown_action"
        assert result[1]["ingredient_ids"] == ["id1"]

    def test_validate_incorrect_types(self):
        """Test validation fixes incorrect field types."""
        actions = [
            {
                "name": "mix",
                "ingredient_ids": "single_id",  # Should be list
                "equipment_id": ["list_id"]  # Should be string
            }
        ]

        result = validate_action_structure(actions)

        assert len(result) == 1
        assert result[0]["ingredient_ids"] == ["single_id"]
        assert result[0]["equipment_id"] == "list_id"

    def test_validate_non_dict_items(self):
        """Test validation skips non-dictionary items."""
        actions = [
            {"name": "valid"},
            "invalid_string",
            123,
            None,
            {"name": "also_valid"}
        ]

        result = validate_action_structure(actions)

        assert len(result) == 2
        assert result[0]["name"] == "valid"
        assert result[1]["name"] == "also_valid"

    def test_validate_empty_list(self):
        """Test validation of empty actions list."""
        result = validate_action_structure([])
        assert len(result) == 0

    def test_validate_empty_strings(self):
        """Test validation handles empty strings appropriately."""
        actions = [
            {
                "name": "",
                "ingredient_ids": [""],
                "equipment_id": ""
            }
        ]

        result = validate_action_structure(actions)

        assert len(result) == 1
        assert result[0]["name"] == ""  # Empty name preserved
        assert result[0]["ingredient_ids"] == [""]  # Empty string in list preserved
        assert result[0]["equipment_id"] is None  # Empty string converted to None
