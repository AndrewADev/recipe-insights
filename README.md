---
title: Recipe Insights
emoji: 📉
colorFrom: yellow
colorTo: purple
sdk: gradio
sdk_version: 5.33.1
app_file: src/main.py
pinned: false
python_version: 3.13
tags:
  - agent-demo-track
license: apache-2.0
short_description: AI-powered insights into Recipe Dependencies!
---
# Recipe Insights

A tool to help hobbyist chefs discover and better understand the implicit dependencies in recipes they’d like to cook or bake.

**Notice**: Includes generated sample recipes that have not been tested/verified in the real world and may contain mistakes or improper instructions. Please use common sense and follow all applicable food and appliance safety recommendations when cooking!

## Development

Internally, the project uses `uv`. So setting up looks like:

```shell
# Install dependencies
uv sync

# Run the application
uv run recipe-insights
```

Set up pre-commit with:
```shell
uv run pre-commit
```

### Updating `requirements.txt` (after dependency updates)

The project uses `uv` for package management internally. To run on HuggingFace, however, a `requirements.txt` is required for now. You can update it with the following command:
```shell
uv pip freeze | grep -v "file://" > requirements.txt
```

#### Additional updates

Note that updates to `gradio` and `python` need to also be reflected in the HuggingFace Space configuration meta at the top of this file.

## Additional information

The project source is [hosted on GitHub](https://github.com/AndrewADev/recipe-insights), with updates pushed to a [Hugging Face Space](https://huggingface.co/spaces/AndrewADev/recipe-insights).
