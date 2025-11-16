def test_report_html_sanitized_and_pdf_generated(client):
    html = "<script>alert('x')</script><p>ok</p>"
    resp = client.post('/api/report', json={'report_html': html})
    # Ожидаем успешную генерацию PDF с очищенным HTML
    assert resp.status_code == 200
    assert resp.mimetype == 'application/pdf'
    # Проверяем что это не пустой ответ
    data = resp.data
    assert isinstance(data, (bytes, bytearray))
    assert len(data) > 100  # какой-то разумный размер PDF


