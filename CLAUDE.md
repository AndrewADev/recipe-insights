# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Package Management
- Install dependencies: `uv sync`
- Run application: `uv run recipe-board` or `uv run python -m recipe-board.main`
- Install dev dependencies: `uv sync --group dev`

### Code Quality
- Run pre-commit hooks: `uv run pre-commit run --all-files`
- Install pre-commit: `uv run pre-commit install`

### Testing
- Run all tests: `uv run pytest`
- Run specific test file: `uv run pytest test/test_recipe_analyzer.py`
- Run with verbose output: `uv run pytest -v`

## Architecture Overview

This is an AI-powered recipe analysis tool that helps hobbyist chefs understand dependencies, resource requirements, and workflow optimization in recipes.

### Core Architecture
- **Core Models** (`src/recipe-board/core/`): Pydantic data models for recipes, ingredients, equipment, and steps
- **Agents** (`src/recipe-board/agents/`): AI-powered analysis components using smolagents framework
- **NLP Pipeline**: Hybrid approach using spaCy for basic parsing + LLM calls for complex reasoning

### Key Components

#### Data Models (`core/recipe.py`)
- `Ingredient`: Structured ingredient representation with amounts, units, modifiers, and state tracking
- `Equipment`: Kitchen tools and appliances with size estimates and requirements
- `RecipeStep`: Individual recipe instructions with dependencies, timing, and resource needs
- `IngredientState`: Enum for tracking ingredient transformations (raw → cleaned → chopped → cooked)

#### AI Agents (`agents/`)
- `recipe_analyzer.py`: spaCy-based ingredient parsing with pattern matching for amounts, units, and modifiers
- `recipe_parser.py`: Additional parsing capabilities (to be implemented)

### Technology Stack
- **Language**: Python 3.13+
- **Package Manager**: uv
- **Core Dependencies**: Pydantic, smolagents, spaCy
- **NLP Models**:
  - English: `en_core_web_lg`
  - German: `de_core_news_lg` (planned)
  - Multilingual fallback: `xx_ent_wiki_sm`
- **Future UI**: Gradio (planned)
- **Future Dependencies**: NetworkX for dependency modeling, PuLP for optimization

### Development Notes
- Uses multilingual NLP approach for recipe parsing
- Human-in-the-loop feedback system planned for ambiguous cases
- Focuses on dependency detection and resource optimization
- Test data available in `data/` directory with sample recipes
