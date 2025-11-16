def test_report_html_too_large_rejected(client):
    # Сгенерировать HTML больше лимита (200_000 байт в сервере)
    big = "<p>" + ("x" * 210_000) + "</p>"
    resp = client.post('/api/report', json={'report_html': big})
    assert resp.status_code == 400
    js = resp.get_json()
    assert 'error' in js


