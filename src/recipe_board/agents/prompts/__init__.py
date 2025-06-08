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
Here are some examples:

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

Actions from recipes step:
```
actions=[
  Action(name="combine")
]
```

"""


parse_equipment_prompt = f"""
{briefing}

Now, you will assist one such chef by performing the following parsing the equipment from the recipe.

Please return the equipment, ingredients, and actions in the form of an array of Pydantic models:
```
equipment = [
  Equipment(
      name="Stand mixer",
      required=False,
      modifiers="dough hook attachment"
  )
  # Additional equipment...
]
```

{examples}

IMPORTANT:
* DO NOT ADD ANY STEPS TO THE USER'S TEXT OR YOU WILL BE FIRED!

Now, please return the equipment from the following recipe:
"""
