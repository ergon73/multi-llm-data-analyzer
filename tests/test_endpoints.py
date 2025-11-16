import io
import os
import json
import pandas as pd
import pytest

os.environ.setdefault("TEST_MODE", "true")

from backend.pdf_server import app  # noqa: E402


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def make_csv_bytes(rows=5):
    df = pd.DataFrame([
        {
            "year": 2015, "make": "Kia", "model": "Sorento", "trim": "LX", "body": "SUV",
            "transmission": "automatic", "vin": "5xy", "state": "ca", "condition": 5.0,
            "odometer": 10000, "color": "white", "interior": "black", "seller": "dealer",
            "mmr": 20000, "sellingprice": 21000, "saledate": "2015-01-01"
        } for _ in range(rows)
    ])
    bio = io.BytesIO()
    bio.write(df.to_csv(index=False).encode("utf-8"))
    bio.seek(0)
    return bio


def test_upload_csv_basic(client):
    data = {
        "file": (make_csv_bytes(), "cars.csv")
    }
    resp = client.post("/api/upload?page=1&page_size=3", content_type="multipart/form-data", data=data)
    assert resp.status_code == 200
    payload = resp.get_json()
    assert "table_data" in payload and len(payload["table_data"]) == 3
    assert "basic_analysis" in payload


def test_analyze_stub(client):
    payload = {
        "provider": "openai",
        "model": "gpt-4.1",
        "table_data": [
            {"year": 2015, "make": "Kia", "sellingprice": 21000, "saledate": "2015-01-01"},
            {"year": 2016, "make": "Kia", "sellingprice": 22000, "saledate": "2016-01-01"},
        ]
    }
    resp = client.post("/api/analyze", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "analysis" in data and isinstance(data["analysis"], str)


def test_fill_missing_ai(client):
    table = [
        {"make": "Kia", "model": "Sorento", "color": "black"},
        {"make": "Kia", "model": "Sorento", "color": ""},  # пропуск
    ]
    payload = {
        "table_data": table,
        "columns": ["make", "model", "color"],
        "missing_info": {"color": 1}
    }
    resp = client.post("/api/fill-missing-ai", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "recommendations" in data and "color" in data["recommendations"]
    assert isinstance(data["recommendations"]["color"], list)


