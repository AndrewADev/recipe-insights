import json
from recipe_board.agents.models import parse_recipe_equipment


class TestParseRecipeEquipment:
    """Test suite for parse_recipe_equipment function."""

    def test_parse_recipe_equipment_with_markdown_code_blocks(self, monkeypatch):
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
  "actions": [
    {"name": "mix", "description": "combine ingredients"}
  ]
}
```"""

        def mock_text_generation(*args, **kwargs):
            return mock_response

        monkeypatch.setattr(
            "recipe_board.agents.models.InferenceClient.text_generation",
            mock_text_generation
        )

        result = parse_recipe_equipment("test recipe")

        # Verify markdown is stripped and JSON is properly formatted
        assert result.startswith('{\n')
        assert '```' not in result
        assert '"equipment"' in result
        assert '"ingredients"' in result
        assert '"actions"' in result

        # Verify it's valid JSON
        parsed = json.loads(result)
        assert len(parsed["equipment"]) == 2
        assert parsed["equipment"][0]["name"] == "oven"

    def test_parse_recipe_equipment_clean_json(self, monkeypatch):
        """Test parsing when response is already clean JSON."""
        mock_response = '{"equipment": [], "ingredients": [], "actions": []}'

        def mock_text_generation(*args, **kwargs):
            return mock_response

        monkeypatch.setattr(
            "recipe_board.agents.models.InferenceClient.text_generation",
            mock_text_generation
        )

        result = parse_recipe_equipment("test recipe")

        # Should be properly formatted JSON
        expected = '{\n  "equipment": [],\n  "ingredients": [],\n  "actions": []\n}'
        assert result == expected

    def test_parse_recipe_equipment_invalid_json(self, monkeypatch):
        """Test handling of invalid JSON response."""
        mock_response = "This is not valid JSON at all!"

        def mock_text_generation(*args, **kwargs):
            return mock_response

        monkeypatch.setattr(
            "recipe_board.agents.models.InferenceClient.text_generation",
            mock_text_generation
        )

        result = parse_recipe_equipment("test recipe")

        # Should return the raw response when JSON parsing fails
        assert result == mock_response

    def test_parse_recipe_equipment_empty_response(self, monkeypatch):
        """Test handling of empty response."""
        def mock_text_generation(*args, **kwargs):
            return ""

        monkeypatch.setattr(
            "recipe_board.agents.models.InferenceClient.text_generation",
            mock_text_generation
        )

        result = parse_recipe_equipment("test recipe")

        # Should return empty JSON object
        assert result == "{}"

    def test_parse_recipe_equipment_none_response(self, monkeypatch):
        """Test handling of None response."""
        def mock_text_generation(*args, **kwargs):
            return None

        monkeypatch.setattr(
            "recipe_board.agents.models.InferenceClient.text_generation",
            mock_text_generation
        )

        result = parse_recipe_equipment("test recipe")

        # Should return empty JSON object
        assert result == "{}"
