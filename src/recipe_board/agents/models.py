import os
from huggingface_hub import InferenceClient
from .prompts import parse_equipment_prompt
from wasabi import msg

model = os.environ["HF_MODEL"]


def parse_recipe_equipment(recipe: str):
    try:

        hf_client = InferenceClient(
            provider="hf-inference",
            api_key=os.environ["HF_TOKEN"],
        )
    except Exception as e:
        # TODO: retries?
        msg.fail("error creating client:  {e}")

    result = hf_client.text_generation(parse_equipment_prompt + recipe, model=model)

    if result is None or result == "":
        msg.warn("No result returned!")

    return result
