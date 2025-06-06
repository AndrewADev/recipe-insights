import pytest
from recipe_board.agents.recipe_parser import get_ingredients_section


def test_get_ingredients_section():
    """Test extraction of ingredients section from full recipe text."""

    # Test with complete recipe including multiple sections
    full_recipe = """
# Classic Lasagne Recipe

A delicious Italian dish perfect for family dinners.

## Ingredients

- 12 lasagne sheets (dried or fresh)
- 500g ground beef (or mix of beef and pork)
- 1 large onion, finely diced
- 3 cloves garlic, minced
- 400g can crushed tomatoes
- 2 tbsp tomato paste
- 1 tsp dried oregano

## Instructions

1. Preheat the oven to 180°C.
2. Cook the lasagne sheets according to package directions.
3. Brown the ground beef in a large pan.

## Notes

This recipe serves 6-8 people.
"""

    result = get_ingredients_section(full_recipe)

    # Should extract just the ingredients section
    assert result is not None
    assert result.startswith('## Ingredients')
    assert '12 lasagne sheets' in result
    assert '500g ground beef' in result
    assert '1 tsp dried oregano' in result

    # Should NOT include content from other sections
    assert 'Preheat the oven' not in result
    assert 'This recipe serves' not in result
    assert '## Instructions' not in result
    assert '## Notes' not in result


def test_get_ingredients_section_no_ingredients():
    """Test when recipe has no ingredients section."""

    recipe_no_ingredients = """
# Simple Recipe

## Instructions

1. Just follow these steps.

## Notes

Some helpful tips.
"""

    result = get_ingredients_section(recipe_no_ingredients)
    assert result is None


def test_get_ingredients_section_ingredients_at_end():
    """Test when ingredients section is at the end of the recipe."""

    recipe_ingredients_last = """
# Recipe Title

## Instructions

1. Do something first.
2. Then do this.

## Ingredients

- 1 cup flour
- 2 eggs
- 1 tsp salt
"""

    result = get_ingredients_section(recipe_ingredients_last)

    assert result is not None
    assert result.startswith('## Ingredients')
    assert '1 cup flour' in result
    assert '2 eggs' in result
    assert '1 tsp salt' in result
    assert 'Do something first' not in result


def test_get_ingredients_section_empty_ingredients():
    """Test when ingredients section exists but is empty."""

    recipe_empty_ingredients = """
# Recipe

## Ingredients

## Instructions

1. Follow these steps.
"""

    result = get_ingredients_section(recipe_empty_ingredients)

    assert result is not None
    assert result == '## Ingredients'


def test_get_ingredients_section_case_variations():
    """Test different case variations of ingredients header."""

    # The current implementation expects exact "## Ingredients"
    # This test documents the current behavior
    recipe_lowercase = """
# Recipe

## ingredients

- 1 cup flour

## Instructions

1. Mix ingredients.
"""

    result = get_ingredients_section(recipe_lowercase)
    # Current implementation is case-sensitive, so this should return None
    assert result is None
