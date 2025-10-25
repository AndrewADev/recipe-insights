import sys
from pathlib import Path
# Add the src directory to the Python path for all tests
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
import time
from recipe_board.gradio_ui import create_ui
from recipe_board.core.state import RecipeSessionState
from recipe_board.core.recipe import Ingredient, Equipment, Action

# Use different port for test
GRADIO_PORT_TEST=7861

@pytest.fixture(scope="session")
def gradio_app():
    """Start Gradio app for testing"""
    app = create_ui()

    # Launch with prevent_thread_lock=True for testing
    app.launch(
        server_port=GRADIO_PORT_TEST,
        share=False,
        quiet=True,
        prevent_thread_lock=True  # Returns immediately, doesn't block
    )

    # Brief wait for startup
    time.sleep(1)

    yield app

    # Cleanup
    try:
        app.close()
    except (AttributeError, RuntimeError):
        pass  # Ignore cleanup errors in tests


@pytest.fixture
def basic_ingredient():
    """Fixture providing a basic ingredient for testing."""
    return Ingredient(
        name="flour",
        amount=2.0,
        unit="cups",
        modifiers=[],
        raw_text="2 cups flour"
    )


@pytest.fixture
def basic_equipment():
    """Fixture providing basic equipment for testing."""
    return Equipment(
        name="bowl",
        required=True,
        modifiers=None
    )


@pytest.fixture
def basic_recipe_state(basic_ingredient, basic_equipment):
    """Fixture providing a basic recipe state with one ingredient, equipment, and action."""
    state = RecipeSessionState()
    state.ingredients = [basic_ingredient]
    state.equipment = [basic_equipment]

    action = Action(
        name="mix",
        ingredient_ids=[basic_ingredient.id],
        equipment_id=basic_equipment.id
    )
    state.actions = [action]

    return state


@pytest.fixture
def multi_ingredient_state():
    """Fixture providing a recipe state with multiple ingredients and equipment."""
    state = RecipeSessionState()

    # Create ingredients
    ingredient1 = Ingredient(
        name="flour",
        amount=2.0,
        unit="cups",
        modifiers=[],
        raw_text="2 cups flour"
    )
    ingredient2 = Ingredient(
        name="salt",
        amount=1.0,
        unit="tsp",
        modifiers=[],
        raw_text="1 tsp salt"
    )
    state.ingredients = [ingredient1, ingredient2]

    # Create equipment
    equipment1 = Equipment(name="mixing bowl", required=True, modifiers="large")
    state.equipment = [equipment1]

    # Create action linking ingredients to equipment
    action1 = Action(
        name="mix",
        ingredient_ids=[ingredient1.id, ingredient2.id],
        equipment_id=equipment1.id
    )
    state.actions = [action1]

    return state
