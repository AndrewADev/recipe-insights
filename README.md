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

## Technical Background (Hackathon)

This project takes a hybrid approach to LLM-integration, combining structured prompting with agentic workflows for complex recipe analysis:

**🔍 Two-Stage AI Pipeline:**
- **Stage 1**: Direct LLM calls with structured prompts to extract ingredients, equipment, and cooking actions from recipe text (works well with LLM's strong semantic understanding)
- **Stage 2**: Agentic workflow using [smolagents](https://github.com/huggingface/smolagents) framework with specialized tools to analyze dependencies between extracted entities

**🛠️ Key Technical Features:**
- **Hybrid NLP approach** combining spaCy methods with LLM reasoning for robust parsing
- **Interactive network visualization** using graph theory to display relationships between ingredients→actions→equipment.
- **State management** with progress tracking and error handling throughout the parsing pipeline

**📋 User Experience:**
The "How To" tab provides a comprehensive walkthrough of the application flow: sample recipe selection → parsing → dependency analysis → interactive graph visualization → export capabilities. This creates an intuitive experience for hobbyist chefs to understand their recipe's hidden structure and dependencies.

The application showcases how agentic AI workflows can break down complex NLP tasks into manageable, tool-assisted steps while maintaining transparency and user control throughout the process.

### Explanation videos

Unfortunately sound capture wasn't working properly with Gradio capture, so these are without sound. See the above description, as well as the "How to" tab in the application to get an idea of how to use the app.

**Part 1**

https://github.com/user-attachments/assets/31ba6146-5570-4dd2-a1f3-6358e6c3716f


**Part 2**

https://github.com/user-attachments/assets/4de8d2c2-f990-4c51-9522-781b4bf948fa



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

The project source is [hosted on GitHub](https://github.com/AndrewADev/recipe-insights), with updates pushed to a [Hugging Face Space](https://huggingface.co/spaces/Agents-MCP-Hackathon/recipe-insights).
