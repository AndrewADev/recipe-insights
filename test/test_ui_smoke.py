
from conftest import test_port


def test_app_starts(gradio_app):
    """Smoke test - just verify the app is running"""
    import requests
    response = requests.get(f"http://localhost:{test_port}")
    assert response.status_code == 200
