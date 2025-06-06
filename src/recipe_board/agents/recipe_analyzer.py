from smolagents.tools import tool
from typing import List, Optional
from recipe_board.core.recipe import Ingredient

import spacy
from spacy.matcher import Matcher


def setup_ingredient_parser():
    # TODO: Multilingual model load
    nlp = spacy.load('en_core_web_lg')  # or "de_core_news_lg" for German

    # Create matcher for ingredient patterns
    matcher = Matcher(nlp.vocab)

    # Common cooking units
    units = [
        'cup',
        'cups',
        'tbsp',
        'tsp',
        'tablespoon',
        'tablespoons',
        'teaspoon',
        'teaspoons',
        'g',
        'kg',
        'ml',
        'l',
        'oz',
        'lb',
        'lbs',
    ]

    # Pattern for amount + unit + ingredient
    # e.g., "2 tbsp olive oil", "500g ground beef"
    patterns = [
        # Number + unit + ingredient
        [
            {'LIKE_NUM': True},
            {'LOWER': {'IN': units}},
            {'POS': {'IN': ['NOUN', 'ADJ']}, 'OP': '+'},
        ],
        # Fraction + unit + ingredient
        [
            {'TEXT': {'REGEX': r'\d+/\d+'}},
            {'LOWER': {'IN': units}},
            {'POS': {'IN': ['NOUN', 'ADJ']}, 'OP': '+'},
        ],
        # Just number + ingredient (implicit unit)
        [{'LIKE_NUM': True}, {'POS': {'IN': ['NOUN', 'ADJ']}, 'OP': '+'}],
    ]

    for i, pattern in enumerate(patterns):
        matcher.add(f"INGREDIENT_{i}", [pattern])

    return nlp, matcher


def extract_amount(span) -> Optional[float]:
    """Extract numerical amount from spaCy span"""
    for token in span:
        if token.like_num:
            try:
                return float(token.text)
            except ValueError:
                pass
        # Handle fractions like "1/2"
        if '/' in token.text:
            try:
                parts = token.text.split('/')
                return float(parts[0]) / float(parts[1])
            except:
                pass
    return None


def extract_unit(span) -> Optional[str]:
    """Extract unit from spaCy span"""
    units = {
        'cup',
        'cups',
        'tbsp',
        'tsp',
        'tablespoon',
        'tablespoons',
        'teaspoon',
        'teaspoons',
        'g',
        'kg',
        'ml',
        'l',
        'oz',
        'lb',
        'lbs',
    }

    for token in span:
        if token.text.lower() in units:
            return token.text.lower()
    return None


def extract_ingredient_name(span, amount, unit) -> str:
    """Extract the actual ingredient name, excluding amount and unit"""
    tokens = []
    for token in span:
        # Skip amounts and units
        if (
            token.like_num
            or (amount and token.text == str(amount))
            or (unit and token.text.lower() == unit)
        ):
            continue
        tokens.append(token.text)

    return ' '.join(tokens).strip()


def extract_modifiers(original_line: str, span) -> List[str]:
    """Extract preparation modifiers (diced, chopped, etc.)"""
    modifiers = []

    # Common cooking modifiers
    cooking_modifiers = {
        'diced',
        'chopped',
        'minced',
        'sliced',
        'grated',
        'crushed',
        'fresh',
        'dried',
        'ground',
        'whole',
        'fine',
        'coarse',
        'large',
        'small',
        'medium',
        'finely',
        'roughly',
    }

    doc = span.doc
    for token in doc:
        if token.text.lower() in cooking_modifiers:
            modifiers.append(token.text.lower())

    return modifiers


def extract_ingredient_from_line(line: str, nlp, matcher) -> Optional[Ingredient]:
    import re

    doc = nlp(line)

    # Extract amount using spaCy's number detection
    amount = None
    for token in doc:
        if token.like_num:
            try:
                amount = float(token.text)
                break
            except ValueError:
                # Handle fractions
                if '/' in token.text:
                    try:
                        parts = token.text.split('/')
                        amount = float(parts[0]) / float(parts[1])
                        break
                    except:
                        pass

    # Extract unit using spaCy analysis - look for tokens that are likely units
    unit = None
    units = {
        'cup',
        'cups',
        'tbsp',
        'tsp',
        'tablespoon',
        'tablespoons',
        'teaspoon',
        'teaspoons',
        'g',
        'kg',
        'ml',
        'l',
        'oz',
        'lb',
        'lbs',
    }

    for token in doc:
        if token.text.lower() in units:
            unit = token.text.lower()
            break

    # Use spaCy to identify modifiers and ingredient name
    modifiers = []
    ingredient_tokens = []

    # Extract parenthetical content as modifiers using regex + spaCy parsing
    paren_matches = re.findall(r'\(([^)]+)\)', line)
    for paren_content in paren_matches:
        paren_doc = nlp(paren_content)
        for token in paren_doc:
            if token.pos_ in [
                'ADJ',
                'NOUN',
                'VERB',
            ]:  # Adjectives, nouns, or past participles
                modifiers.append(token.text.lower())

    # Remove parenthetical content for main parsing
    clean_line = re.sub(r'\([^)]+\)', '', line).strip()
    clean_doc = nlp(clean_line)

    for token in clean_doc:
        # Skip numbers and units we already extracted
        if token.like_num or token.text.lower() in units:
            continue

        # Adjectives describing preparation/state are modifiers
        if token.pos_ == 'ADJ':
            modifiers.append(token.text.lower())
        # Past participles often describe preparation (e.g., "chopped", "diced")
        elif token.tag_ in ['VBN', 'VBD'] and token.dep_ in ['amod', 'acl']:
            modifiers.append(token.text.lower())
        # Nouns and proper nouns are likely part of ingredient name
        elif token.pos_ in ['NOUN', 'PROPN']:
            ingredient_tokens.append(token.text)
        # Include some adjectives that are part of ingredient names (e.g., "olive" in "olive oil")
        elif (
            token.pos_ == 'ADJ'
            and token.dep_ in ['compound', 'amod']
            and token.head.pos_ in ['NOUN', 'PROPN']
        ):
            ingredient_tokens.append(token.text)

    # Build ingredient name from identified tokens
    name = ' '.join(ingredient_tokens).strip()

    # If we didn't get a good name, fall back to a simpler approach
    if not name:
        # Take everything that's not a number or known unit
        fallback_tokens = []
        for token in clean_doc:
            if (
                not token.like_num
                and token.text.lower() not in units
                and token.pos_ not in ['PUNCT']
            ):
                fallback_tokens.append(token.text)
        name = ' '.join(fallback_tokens).strip()

    return Ingredient(
        amount=amount,
        unit=unit,
        name=name,
        modifiers=list(set(modifiers)),  # Remove duplicates
        raw_text=line,
    )


@tool
def parse_ingredients_from_section(ingredients_text: str) -> List[Ingredient]:
    """
    Parse a recipe ingredients section and extract structured ingredient data.

    This tool analyzes ingredient text (typically from a recipe) and extracts:
    - Ingredient amounts (numbers and fractions)
    - Measurement units (cups, tbsp, grams, etc.)
    - Ingredient names
    - Preparation modifiers (diced, chopped, fresh, etc.)

    Args:
        ingredients_text (str): Raw text containing ingredient list, typically with bullet points or dashes.
                               Example: "- 2 cups flour\n- 500g ground beef\n- 1 large onion, diced"

    Returns:
        List[Ingredient]: List of structured ingredient objects containing:
            - amount: numerical quantity (float or None)
            - unit: measurement unit (str or None)
            - name: ingredient name (str)
            - modifiers: preparation descriptors (List[str])
            - raw_text: original text line (str)

    Examples:
        >>> parse_ingredients_from_section("- 2 tbsp olive oil\n- 1 large onion, diced")
        [Ingredient(amount=2.0, unit="tbsp", name="olive oil", modifiers=[], raw_text="2 tbsp olive oil"),
         Ingredient(amount=1.0, unit=None, name="large onion", modifiers=["large", "diced"], raw_text="1 large onion, diced")]
    """
    nlp, matcher = setup_ingredient_parser()

    ingredients = []

    # Split by lines and process each ingredient line
    lines = ingredients_text.split('\n')

    for line in lines:
        # Skip headers and empty lines
        if line.startswith('#') or not line.strip() or not line.strip().startswith('-'):
            continue

        # Clean up the line (remove bullet points)
        clean_line = line.strip().lstrip('- •*').strip()

        ingredient = extract_ingredient_from_line(clean_line, nlp, matcher)
        if ingredient:
            ingredients.append(ingredient)

    return ingredients


# class DependencyAnalyzer(BaseTool):
#     """Identifies step dependencies and timing constraints"""
#     name = "dependency_analysis"
#     description = "Determines which recipe steps depend on others"

#     def _run(self, recipe_steps: List[RecipeStep]) -> Dict:
#         # LLM reasoning for dependency extraction
#         pass
