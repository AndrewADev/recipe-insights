import pytest
from conftest import GRADIO_PORT_TEST

@pytest.mark.skip(reason="Unknown issue causing timeout")
def test_app_starts(gradio_app):
    """Smoke test - just verify the app is running"""
    import requests
    response = requests.get(f"http://localhost:{GRADIO_PORT_TEST}")
    assert response.status_code == 200
