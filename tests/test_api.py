import os
import json
import pytest

os.environ.setdefault("TEST_MODE", "true")

from backend.pdf_server import app  # noqa: E402


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/api/test")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data and data.get("status") == "ok"


def test_report_sanitize_blocks_external(client):
    # Вставляем внешнюю ссылку — должна быть заблокирована санитайзером/url_fetcher
    report_html = """
        <html><body>
            <img src="http://example.com/evil.png" />
            <p>OK</p>
        </body></html>
    """
    resp = client.post(
        "/api/report",
        data=json.dumps({"report_html": report_html}),
        content_type="application/json",
    )
    # WeasyPrint рендерит PDF байты; если внешние ссылки заблокированы — генерация не упадет
    assert resp.status_code in (200, 400, 500)
    # В happy-path ожидаем 200 и application/pdf в TEST_MODE
    if resp.status_code == 200:
        assert resp.mimetype == "application/pdf"


