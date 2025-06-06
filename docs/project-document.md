# Project document

This document contains the most important features and goals of the project.

## Overview

I want to develop an AI agent to help hobbyist chefs discover and better understand the implicit dependencies in recipes they’d like to cook or bake. In its initial iterations, it will focus on providing solid 'dependency detection', and making this information known to the user (ideally via visualization). Successive iterations will build out the 'intelligence' of the tool when dealing with recipes (better understanding implication of certain steps, ingredients, etc), as well as offer more features to help make recipe prep operate more smoothly (some initial ideas include accounting for multiple chefs or assistants, allow more efficient scheduling of recipe tasks, etc.).

## MVP Features

The main features of a first pass/MVP are planned to include:

* Understanding (semi-structured) recipes (e.g. via NLU)
* Parsing out ingredients (most listed explicitly), as well as parsing and *inferring* the utensils, cookware, and appliances that are required or helpful for the recipe
* Tracking the use of ingredients throughout the recipe
  * Amounts used
  * state changes (clean, slice/dice/season/etc, cook/saute/fry/etc, garnish/server/etc)
* Tracking dependencies within the recipe
  * E.g. that vegetables must be washed, prepared (possibly with intermediate steps), before being cooked, added to dish
  * E.g. that a sauce should be prepared before a meat can be cooked (if the recipe calls for it)
* Does basic resource tracking and resource capacity planning
  * Ex: that need at least one frying pan (estimate size), a pot, etc
  * Ex: Determine that need at least two mixing bowls needed
  * Ex: Determine if resources can be used in tandem, or if they are needed simultaneously
* Print out basic DAG or similar workflow–like diagrams with the dependencies visualized
  * Also ‚swimlane‘ format
* Allow for fallback to user choices (when low confidence, ambiguity)
  * Human-in-the-loop
  * Thumbs up/down for individual responses (e.g. as override)


### Additional details

#### Data input (for recipes)

* Text-based recipe input (copy/paste)
* Encourage users to follow basic standardized format initially
* Support common recipe formats with increasing flexibility over iterations (as time permits)

#### Error Handling & Human Feedback

Ideas to handle ambiguity and improve user experience when error conditions occur.

Use a Human-in-the-Loop Strategy:

* Implement thumbs up/down feedback buttons for key inferences (equipment needs, dependencies, resource estimates)
* Store user corrections in feedback database for future model improvements
* Leverage observability (**LangFuse**  annotation?)  features for structured feedback collection
* Display confidence scores for uncertain predictions to guide user review

Graceful Degradation:

* Show parsing confidence levels to users
* Allow manual override/editing of extracted information
* Fallback to basic ingredient lists when complex parsing fails

### Future iterations (potentially post MVP-submission)

Later versions would be extended to:

* Better understanding the actions commonly requested in recipes to improve scheduling/allocation suggestions, for instance
* Account for multiple chefs or helpers during preparation
* Estimate time needed for individual tasks, as well as calculate project length estimates based on number of chefs or helpers
* Be extensible, with users adding own kitchen appliances, prep times, etc
* Read recipes from pictures or screenshots (multi-modal)
  * especially including OCR

## Technical details

### Technical requirements

* Includes unit tests, integration tests to achieve a high degree of test coverage
* Incorporates observability tools (LangFuse?), especially for observing and debugging LLM calls

### Tech stack (firm)

* Main language is Python
* Uses Gradio for the UI
* Uses transformers for pipelines
  * Inference performed via appropriate models, including LLMs, if appropriate
* Inference is planned to run on Huggingface or a similar hosted service, though it would be good to investigate local alternatives (such as for a dev and debug loop)
* Uses uv for package management
* Uses git for source control

### Tech stack (open/suggestions):

* NetworkX for dependency modelling
* PuLP for constrained optimization (capacity constraints and similar)

### Model Selection & NLP Pipeline

Hybrid Approach (Recommended for MVP):

* **spaCy + multilingual models** for core NLP tasks (ingredient extraction, quantity parsing, basic entity recognition)
  * German support: `de_core_news_lg`
  * English support: `en_core_web_lg`
  * Multilingual fallback: `xx_ent_wiki_sm`
* **LLM API calls (Claude/GPT-4 mini)** for complex reasoning tasks (dependency inference, equipment identification, state tracking)
* **Additional models to evaluate:**
  * `distilbert-base-multilingual-cased` for step classification
  * `facebook/bart-large-mnli` for zero-shot cooking action recognition
  * `deepset/gbert-base` for German-specific tasks

**Rationale:** Fast local inference for basic parsing + LLM power for complex reasoning. Multilingual by default and hackathon-friendly timeline.
