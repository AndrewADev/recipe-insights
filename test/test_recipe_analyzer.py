from recipe_board.agents.recipe_analyzer import parse_ingredients_from_section

lasagne_ingredients = """
## Ingredients

- 12 lasagne sheets (dried or fresh)
- 500g ground beef (or mix of beef and pork)
- 1 large onion, finely diced
- 3 cloves garlic, minced
- 400g can crushed tomatoes
- 2 tbsp tomato paste
- 1 tsp dried oregano
"""


def test_parse_ingredients():
    ingredients = parse_ingredients_from_section(lasagne_ingredients)

    # Should parse 7 ingredients
    assert len(ingredients) == 7

    # Test first ingredient: "12 lasagne sheets (dried or fresh)"
    assert ingredients[0].amount == 12
    assert ingredients[0].unit is None
    assert 'lasagne sheets' in ingredients[0].name
    assert ingredients[0].raw_text == '12 lasagne sheets (dried or fresh)'

    # Test ingredient with unit: "500g ground beef (or mix of beef and pork)"
    beef_ingredient = next(ing for ing in ingredients if 'beef' in ing.name)
    assert beef_ingredient.amount == 500
    assert beef_ingredient.unit == 'g'
    assert beef_ingredient.name == 'ground beef'
    assert (
        'mix' in beef_ingredient.modifiers or 'pork' in beef_ingredient.modifiers
    )  # parenthetical content

    # Test ingredient with tablespoon unit: "2 tbsp tomato paste"
    paste_ingredient = next(ing for ing in ingredients if 'tomato paste' in ing.name)
    assert paste_ingredient.amount == 2
    assert paste_ingredient.unit == 'tbsp'

    # Test ingredient with teaspoon unit: "1 tsp dried oregano"
    oregano_ingredient = next(ing for ing in ingredients if 'oregano' in ing.name)
    assert oregano_ingredient.amount == 1
    assert oregano_ingredient.unit == 'tsp'
    assert 'dried' in oregano_ingredient.modifiers

    # Verify all ingredients have raw_text preserved
    for ingredient in ingredients:
        assert ingredient.raw_text is not None
        assert len(ingredient.raw_text.strip()) > 0
