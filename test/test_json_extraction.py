"""Unit tests for JSON extraction and cleaning logic."""

import pytest
import json
from recipe_board.agents.models import _extract_json_from_response


class TestJSONExtraction:
    """Test suite for JSON extraction from LLM responses."""

    def test_extract_json_from_standard_code_block(self):
        """Test extraction from standard ```json code blocks."""
        response = '''```json
{
  "equipment": [{"name": "oven", "required": true}],
  "ingredients": [{"name": "flour", "amount": 2}],
  "basic_actions": []
}
```'''

        result = _extract_json_from_response(response)
        parsed = json.loads(result)

        assert isinstance(parsed, dict)
        assert "equipment" in parsed
        assert "ingredients" in parsed
        assert "basic_actions" in parsed

    def test_extract_json_with_text_before_code_block(self):
        """Test extraction when there's text before the code block."""
        response = '''{Create Answer} ```json
{
  "equipment": [{"name": "oven", "required": true}],
  "ingredients": [{"name": "flour", "amount": 2}],
  "basic_actions": []
}
```'''

        result = _extract_json_from_response(response)
        parsed = json.loads(result)

        assert isinstance(parsed, dict)
        assert "equipment" in parsed
        assert "ingredients" in parsed

    def test_extract_json_with_text_after_code_block(self):
        """Test extraction when there's text after the code block."""
        response = '''```json
{
  "equipment": [{"name": "oven", "required": true}],
  "ingredients": [{"name": "flour", "amount": 2}],
  "basic_actions": []
}
``` Hope this helps!'''

        result = _extract_json_from_response(response)
        parsed = json.loads(result)

        assert isinstance(parsed, dict)
        assert "equipment" in parsed

    def test_extract_json_with_text_before_and_after(self):
        """Test extraction with text both before and after code block."""
        response = '''Here's your parsed recipe: ```json
{
  "equipment": [{"name": "oven", "required": true}],
  "ingredients": [{"name": "flour", "amount": 0.5}],
  "basic_actions": [{"verb": "mix", "sentence": "Mix ingredients.", "sentence_index": 0}]
}
``` Let me know if you need anything else!'''

        result = _extract_json_from_response(response)
        parsed = json.loads(result)

        assert isinstance(parsed, dict)
        assert len(parsed["ingredients"]) == 1
        assert parsed["ingredients"][0]["amount"] == 0.5

    def test_extract_json_from_generic_code_block(self):
        """Test extraction from generic ``` code blocks without 'json' specifier."""
        response = '''```
{
  "equipment": [{"name": "oven", "required": true}],
  "ingredients": [{"name": "flour", "amount": 2}],
  "basic_actions": []
}
```'''

        result = _extract_json_from_response(response)
        parsed = json.loads(result)

        assert isinstance(parsed, dict)

    def test_extract_json_object_without_code_blocks(self):
        """Test extraction of JSON object when no code blocks are present."""
        response = '''The parsed recipe is: {
  "equipment": [{"name": "oven", "required": true}],
  "ingredients": [{"name": "flour", "amount": 2}],
  "basic_actions": []
} and that's it!'''

        result = _extract_json_from_response(response)
        parsed = json.loads(result)

        assert isinstance(parsed, dict)

    def test_extract_json_handles_nested_braces(self):
        """Test that extraction works with nested JSON structures."""
        response = '''{Some text} ```json
{
  "equipment": [{"name": "oven", "required": true, "details": {"temp": "350F"}}],
  "ingredients": [{"name": "flour", "amount": 2}],
  "basic_actions": []
}
```'''

        result = _extract_json_from_response(response)
        parsed = json.loads(result)

        assert isinstance(parsed, dict)
        assert "details" in parsed["equipment"][0]

    def test_extract_json_no_valid_json_found(self):
        """Test behavior when no valid JSON is found."""
        response = "This is just plain text with no JSON structure at all."

        result = _extract_json_from_response(response)

        # Should return the original response when no JSON is found
        assert result == response

    def test_extract_json_empty_response(self):
        """Test handling of empty or whitespace-only responses."""
        assert _extract_json_from_response("") == ""
        assert _extract_json_from_response("   ") == ""
        assert _extract_json_from_response("\n\t  \n") == ""

    def test_extract_json_with_fractions_in_amounts(self):
        """Test that we can handle responses with decimal amounts."""
        response = '''```json
{
  "equipment": [{"name": "oven", "required": true}],
  "ingredients": [
    {"name": "flour", "amount": 2.5, "unit": "cups"},
    {"name": "oil", "amount": 0.5, "unit": "cup"},
    {"name": "sugar", "amount": 0.25, "unit": "cup"}
  ],
  "basic_actions": []
}
```'''

        result = _extract_json_from_response(response)
        parsed = json.loads(result)

        assert parsed["ingredients"][0]["amount"] == 2.5
        assert parsed["ingredients"][1]["amount"] == 0.5
        assert parsed["ingredients"][2]["amount"] == 0.25
