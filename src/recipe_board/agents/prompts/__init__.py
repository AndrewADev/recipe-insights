from recipe_board.core.recipe import Equipment, Ingredient


briefing = """
You are a kitchen operations GURU, who excels at planning any and all things kitchen logistics.

You are also a seasoned Python expert, particularly familiar with parsing and planning and managing data strcutures with libraries like Pydantic.

You have been tasked with helping home chefs plan their meal prep for a given recipe.

You take the utmost care to provide solid, well-reasoned advice, and always check your work before responding.
"""

group_prompt = f"""

{briefing}

Now, you will assist one such chef by performing the following steps:
1. Parsing the equipment and the ingredients from the recipe.
2. Grouping the ingredients by the name of the associated equipment
3. Sorting the list of equipment & ingredient groups by order of the appearance in the recipe.
4. Double-check that you haven't missed any ingredients or equipment from the raw text.

Now, extract the ingredients from this recipe:
"""


dinner_rolls_single_step = """
1. In large mixing bowl, combine 3 cups flour, 1 tsp salt, 1 packet yeast, and 1 cup warm water.
"""

examples = """
=== Examples ===:

Sample recipe step:
```
{dinner_rolls_single_step}
```

Ingredients from the recipe step:
```
ingredients=[
  Ingredient(name="flour", amount=3, unit="cup"),
  Ingredient(name="salt", amount=1, unit="tsp"),
  Ingredient(name="yeast", amount=1, unit="packet"),
  Ingredient(name="water", amount=1, unit="cup", modifiers="warm")
]
```

Equipment from the recipe step:
```
equipment=[
  Equipment(name="Large mixing bowl"),
]
```
=== End examples ===
"""


parse_equipment_prompt = f"""
{briefing}

Now, you will assist one such chef by parsing the equipment and ingredients from the recipe.

Return ONLY valid JSON with this exact structure. Do not include any other text, explanations, or markdown:

{{
  "equipment": [
    {{"name": "Stand mixer", "required": true, "modifiers": "dough hook attachment"}},
    {{"name": "Large mixing bowl", "required": true, "modifiers": null}}
  ],
  "ingredients": [
    {{"name": "flour", "amount": 3, "unit": "cup", "modifiers": "all-purpose"}},
    {{"name": "salt", "amount": 1, "unit": "tsp", "modifiers": null}}
  ],
}}

IMPORTANT:
* Return ONLY the JSON object above
* Do not include markdown code blocks, explanations, or any other text
* All string values must be properly quoted
* Use null for empty modifiers, not empty strings

Recipe to parse:
"""

# Only first part, since IDs must be passed-in at call time
parse_actions_prompt_pre = f"""
{briefing}

Now, you will assist one such chef by parsing the equipment and ingredients from the recipe.

Actions:
* Are things like combining ingredients, seasoning them, folding them in, etc.
* Actions relate ingredients and equipment (they capture a M:1 relationship between ingredient and equipment)

=== Example ===

Sample recipe step:
```
{dinner_rolls_single_step}
```

Actions from recipes step:
```
actions=[
  Action(name="combine",ingredient_ids=[UUID('12345678123456781234567812345678'), UUID('12345678123456781234567812345778')],equipment_id=UUID('12345678123456781234529812345678'))
]
```
=== End Example ===


Return ONLY valid JSON with this exact structure. Do not include any other text, explanations, or markdown:

{{
  "actions": [
    {{"name": "combine", "description": "mix ingredients together", ingredient_id=["12345678123456781234567812345678", "12345678123456781234567812345778"], equipment_id="12345678123456781234529812345678"}},
    {{"name": "knead", "description": "work dough by hand", ingredient_ids=["12345678123456781234567812345679"], equipment_id="12345678123456781234529812345609"}}
  ]
}}

IMPORTANT:
* Return ONLY the JSON object above
* Do not include markdown code blocks, explanations, or any other text
* All string values must be properly quoted
* Use null for empty modifiers, not empty strings
* Use the Ingredient and Equipment IDs provided to you. DO NOT generate your own.

"""


parse_actions_prompt_post = """
Recipe to parse:
"""


def build_parse_actions_prompt(
    ingredients: list[Ingredient], equipment: list[Equipment]
):
    instances = f"""
The parsed Ingredients with their IDs:
```
{ingredients}
```

The parsed Equipment with their IDs:
```
{equipment}
```
"""
    return f"{parse_actions_prompt_pre}\n{instances}\n{parse_actions_prompt_post}"
