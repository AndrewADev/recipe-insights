import sys
from pathlib import Path
# Add the src directory to the Python path for all tests
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
import threading
import time
from recipe_board.gradio_ui import create_ui

# Use different port for test
test_port=7861

@pytest.fixture(scope="session")
def gradio_app():
    """Start Gradio app for testing"""
    app = create_ui()

    # Launch with prevent_thread_lock=True for testing
    app.launch(
        server_port=test_port,
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
    except:
        pass  # Ignore cleanup errors in tests
