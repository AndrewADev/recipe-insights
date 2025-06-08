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
        return "{}"

    # Try to parse as JSON and format nicely
    try:
        import json
        import re

        # Strip markdown code blocks if present
        clean_result = result.strip()
        if clean_result.startswith("```json"):
            clean_result = re.sub(r"```json\s*", "", clean_result)
        if clean_result.startswith("```"):
            clean_result = re.sub(r"```\s*", "", clean_result)
        if clean_result.endswith("```"):
            clean_result = re.sub(r"\s*```$", "", clean_result)

        parsed = json.loads(clean_result)
        return json.dumps(parsed, indent=2)
    except json.JSONDecodeError:
        # Fallback to raw result if not valid JSON
        msg.warn("Response is not valid JSON, returning raw result")
        return result
