import os
import io
import pytest

os.environ.setdefault("TEST_MODE", "true")
os.environ.pop("API_KEY", None)  # отключаем auth для тестов

from backend.pdf_server import app  # noqa: E402


@pytest.fixture()
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


