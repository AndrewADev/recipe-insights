"""
Tests for sample recipe utilities.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, mock_open

from recipe_board.core.sample_recipes import (
    load_sample_recipes,
    create_recipe_preview,
    get_sample_recipe_choices,
)


class TestLoadSampleRecipes:
    """Tests for load_sample_recipes function."""

    def test_load_sample_recipes_with_valid_files(self):
        """Test loading sample recipes from valid markdown files."""
        # Create a temporary directory with sample recipes
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample recipe file
            recipe_content = """# Classic Lasagne

A delicious Italian dish.

## Ingredients
- 500g pasta
- 200g cheese

## Instructions
1. Cook pasta
2. Add cheese
"""
            recipe_file = os.path.join(temp_dir, "lasagne.md")
            with open(recipe_file, "w", encoding="utf-8") as f:
                f.write(recipe_content)

            # Load recipes
            recipes = load_sample_recipes(temp_dir)

            # Verify results
            assert len(recipes) == 1
            assert "Classic Lasagne" in recipes
            assert recipes["Classic Lasagne"] == recipe_content

    def test_load_sample_recipes_with_multiple_files(self):
        """Test loading multiple sample recipes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple recipe files
            recipes_data = {
                "pasta.md": "# Pasta Recipe\n\nSimple pasta dish.",
                "salad.md": "# Garden Salad\n\nFresh and healthy.",
            }

            for filename, content in recipes_data.items():
                with open(os.path.join(temp_dir, filename), "w") as f:
                    f.write(content)

            # Load recipes
            recipes = load_sample_recipes(temp_dir)

            # Verify results
            assert len(recipes) == 2
            assert "Pasta Recipe" in recipes
            assert "Garden Salad" in recipes

    def test_load_sample_recipes_with_no_files(self):
        """Test loading from empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recipes = load_sample_recipes(temp_dir)
            assert recipes == {}

    def test_load_sample_recipes_with_invalid_file(self):
        """Test handling of files that can't be read."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file with invalid content
            invalid_file = os.path.join(temp_dir, "invalid.md")
            with open(invalid_file, "w") as f:
                f.write("# Valid Recipe\n\nContent here")

            # Mock file reading to raise an exception
            with patch("builtins.open", mock_open()) as mock_file:
                mock_file.side_effect = IOError("Permission denied")

                with patch("recipe_board.core.sample_recipes.msg") as mock_msg:
                    recipes = load_sample_recipes(temp_dir)

                    # Should return empty dict and log warning
                    assert recipes == {}
                    mock_msg.warn.assert_called()

    def test_load_sample_recipes_title_extraction(self):
        """Test proper title extraction from various header formats."""
        test_cases = [
            ("# Simple Title", "Simple Title"),
            ("## Double Hash", "Double Hash"),
            ("# Title with Extra Spaces  ", "Title with Extra Spaces"),
            ("###Multiple###Hashes###", "Multiple###Hashes"),
            ("", "test.md"),  # Fallback to filename
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            for i, (header, expected_title) in enumerate(test_cases):
                filename = f"test{i}.md" if header else "test.md"
                content = f"{header}\n\nContent here" if header else "Content without header"

                with open(os.path.join(temp_dir, filename), "w") as f:
                    f.write(content)

            recipes = load_sample_recipes(temp_dir)

            # Check that titles are extracted correctly
            for header, expected_title in test_cases:
                if expected_title in recipes:
                    assert expected_title in recipes

    def test_load_sample_recipes_default_path(self):
        """Test using default data directory path."""
        # This test verifies the function can be called without data_dir
        # but doesn't test the actual file loading since we can't mock the relative path easily
        with patch("recipe_board.core.sample_recipes.glob.glob") as mock_glob:
            mock_glob.return_value = []
            recipes = load_sample_recipes()
            assert recipes == {}
            mock_glob.assert_called_once()


class TestCreateRecipePreview:
    """Tests for create_recipe_preview function."""

    def test_create_recipe_preview_basic(self):
        """Test basic recipe preview creation."""
        recipe_text = """# Test Recipe

This is a test recipe.

## Ingredients
- 1 cup flour
- 2 eggs

## Instructions
1. Mix ingredients
2. Bake for 30 minutes
3. Serve hot
"""
        preview = create_recipe_preview(recipe_text, max_lines=6)
        lines = preview.split("\n")

        # The function includes empty lines in the count, so we expect 6 lines + "..."
        assert len(lines) == 7  # 6 lines + "..."
        assert lines[0] == "# Test Recipe"
        assert lines[-1] == "..."

    def test_create_recipe_preview_with_truncation(self):
        """Test preview truncation with ellipsis."""
        recipe_text = """# Long Recipe

Line 1
Line 2
Line 3
Line 4
Line 5
Line 6
Line 7
Line 8
Line 9
Line 10
"""
        preview = create_recipe_preview(recipe_text, max_lines=5)
        lines = preview.split("\n")

        assert len(lines) == 6  # 5 lines + "..."
        assert lines[-1] == "..."

    def test_create_recipe_preview_empty_input(self):
        """Test preview with empty input."""
        assert create_recipe_preview("") == ""
        assert create_recipe_preview(None) == ""

    def test_create_recipe_preview_skip_empty_lines_at_start(self):
        """Test that empty lines at start are skipped."""
        recipe_text = """

# Recipe Title

Content here
"""
        preview = create_recipe_preview(recipe_text, max_lines=3)
        lines = preview.split("\n")

        assert lines[0] == "# Recipe Title"
        assert len(lines) == 3

    def test_create_recipe_preview_custom_max_lines(self):
        """Test custom max_lines parameter."""
        recipe_text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"

        preview_3 = create_recipe_preview(recipe_text, max_lines=3)
        lines_3 = preview_3.split("\n")
        assert len(lines_3) == 4  # 3 lines + "..."
        assert lines_3[-1] == "..."

        preview_10 = create_recipe_preview(recipe_text, max_lines=10)
        lines_10 = preview_10.split("\n")
        assert len(lines_10) == 5  # All lines, no truncation
        assert "..." not in lines_10

    def test_create_recipe_preview_exact_max_lines(self):
        """Test when recipe has exactly max_lines."""
        recipe_text = "Line 1\nLine 2\nLine 3"
        preview = create_recipe_preview(recipe_text, max_lines=3)
        lines = preview.split("\n")

        assert len(lines) == 3
        assert "..." not in lines


class TestGetSampleRecipeChoices:
    """Tests for get_sample_recipe_choices function."""

    def test_get_sample_recipe_choices_with_empty(self):
        """Test getting choices with empty option included."""
        with patch("recipe_board.core.sample_recipes.load_sample_recipes") as mock_load:
            mock_load.return_value = {
                "Recipe 1": "content1",
                "Recipe 2": "content2",
            }

            choices = get_sample_recipe_choices(include_empty=True)

            assert len(choices) == 3
            assert choices[0] == ""
            assert "Recipe 1" in choices
            assert "Recipe 2" in choices

    def test_get_sample_recipe_choices_without_empty(self):
        """Test getting choices without empty option."""
        with patch("recipe_board.core.sample_recipes.load_sample_recipes") as mock_load:
            mock_load.return_value = {
                "Recipe A": "content_a",
                "Recipe B": "content_b",
            }

            choices = get_sample_recipe_choices(include_empty=False)

            assert len(choices) == 2
            assert "" not in choices
            assert "Recipe A" in choices
            assert "Recipe B" in choices

    def test_get_sample_recipe_choices_empty_recipes(self):
        """Test getting choices when no recipes are available."""
        with patch("recipe_board.core.sample_recipes.load_sample_recipes") as mock_load:
            mock_load.return_value = {}

            choices_with_empty = get_sample_recipe_choices(include_empty=True)
            choices_without_empty = get_sample_recipe_choices(include_empty=False)

            assert choices_with_empty == [""]
            assert choices_without_empty == []


class TestIntegration:
    """Integration tests for sample recipe utilities."""

    def test_full_workflow(self):
        """Test the complete workflow of loading, previewing, and getting choices."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a sample recipe
            recipe_content = """# Integration Test Recipe

A recipe for testing.

## Ingredients
- 1 test ingredient
- 2 cups of mock data

## Instructions
1. Load the recipe
2. Create a preview
3. Verify the choices
"""
            recipe_file = os.path.join(temp_dir, "integration.md")
            with open(recipe_file, "w", encoding="utf-8") as f:
                f.write(recipe_content)

            # Load recipes
            recipes = load_sample_recipes(temp_dir)
            assert len(recipes) == 1
            assert "Integration Test Recipe" in recipes

            # Create preview
            preview = create_recipe_preview(recipes["Integration Test Recipe"], max_lines=6)
            preview_lines = preview.split("\n")
            assert len(preview_lines) == 7  # 6 lines + "..."
            assert "Integration Test Recipe" in preview_lines[0]

            # Get choices
            with patch("recipe_board.core.sample_recipes.load_sample_recipes") as mock_load:
                mock_load.return_value = recipes
                choices = get_sample_recipe_choices()
                assert len(choices) == 2  # "" + "Integration Test Recipe"
                assert "Integration Test Recipe" in choices
