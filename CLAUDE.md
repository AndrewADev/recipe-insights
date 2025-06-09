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
- Test UI functionality: `uv run pytest -k ui_smoke`

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

## Development Workflow
- **IMPORTANT**: Always run `uv run pre-commit run --all-files` before finishing any task to ensure code quality standards are met
- **UI Changes**: When modifying the UI, verify functionality with `uv run pytest -k ui_smoke` to ensure the interface loads correctly

### User Data Privacy Checklist
Before finishing any task that involves logging or data handling:
- [ ] Check for logging statements that include user input, recipe content, or parsed data
- [ ] Ensure `safe_log_user_data()` is used for any logs containing user data
- [ ] Verify error messages don't expose user recipe content
- [ ] Test logging behavior with `RB_ALLOW_USER_DATA_LOGS=false` (default)
- [ ] Review feedback/storage systems for user data exposure

### Code Review Guidelines
For pull requests, reviewers should check:

**🔍 User Data Privacy Review:**
- [ ] New logging statements use `safe_log_user_data()` when logging user content
- [ ] Exception handlers don't expose user data in error messages
- [ ] Database/file storage doesn't persist user data without consent
- [ ] Debug output doesn't include recipe text, ingredient names, or user input
- [ ] API responses don't leak user data in error details

**⚠️ Red Flags to Watch For:**
- Direct logging of variables like `recipe_text`, `user_input`, `parsed_data`
- Exception messages that include `str(e)` when `e` could contain user data
- Print statements or debug logs with user content
- File storage that saves complete user recipes/inputs
- Error responses that echo back user input
