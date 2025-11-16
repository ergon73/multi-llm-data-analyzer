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


def make_large_csv_bytes(rows=2000):
    df = pd.DataFrame([
        {
            "year": 2015 + (i % 5),
            "make": "Make" + str(i % 3),
            "model": "Model" + str(i % 7),
            "trim": "Base",
            "body": "Sedan",
            "transmission": "auto",
            "vin": f"VIN{i:06d}",
            "state": "ca",
            "condition": float((i % 10) + 1),
            "odometer": 1000 * i,
            "color": "black",
            "interior": "gray",
            "seller": "dealer",
            "mmr": 10000 + i,
            "sellingprice": 12000 + i,
            "saledate": "2015-01-01",
        } for i in range(rows)
    ])
    bio = io.BytesIO(df.to_csv(index=False).encode("utf-8"))
    bio.seek(0)
    return bio


def test_upload_large_csv_is_limited(client):
    # page_size=1000, должен вернуться ровно 1000 строк
    resp = client.post(
        "/api/upload?page=1&page_size=1000",
        content_type="multipart/form-data",
        data={"file": (make_large_csv_bytes(5000), "big.csv")},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["table_data"]) == 1000
    assert data["total_rows"] >= 1000


def test_upload_invalid_extension_rejected(client):
    bad_file = io.BytesIO(b"not a real data")
    resp = client.post(
        "/api/upload",
        content_type="multipart/form-data",
        data={"file": (bad_file, "data.txt")},
    )
    assert resp.status_code == 400
    j = resp.get_json()
    assert "error" in j


def test_analyze_missing_fields_400(client):
    resp = client.post("/api/analyze", data=json.dumps({"provider": "openai"}), content_type="application/json")
    assert resp.status_code == 400


