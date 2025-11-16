def test_upload_unsupported_format(client):
    data = {
        'file': (b'not-a-real', 'file.txt')
    }
    resp = client.post('/api/upload?page=1&page_size=1000', data=data, content_type='multipart/form-data')
    assert resp.status_code == 400
    js = resp.get_json()
    assert 'error' in js


def test_upload_page_invalid_dataset_id(client):
    resp = client.post('/api/upload/page', json={'dataset_id': 'nonexistent', 'page': 1, 'page_size': 1000})
    assert resp.status_code == 400
    js = resp.get_json()
    assert 'error' in js


def test_upload_page_out_of_range(client):
    # upload small dataset
    csv_bytes = b"year,make\n2020,A\n"
    data = {'file': (csv_bytes, 'cars.csv')}
    resp = client.post('/api/upload?page=1&page_size=1000', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    ds = resp.get_json()['dataset_id']

    # request far page should return empty page but 200
    resp2 = client.post('/api/upload/page', json={'dataset_id': ds, 'page': 5, 'page_size': 1000})
    assert resp2.status_code == 200
    js2 = resp2.get_json()
    assert js2['current_page'] == 5
    assert js2['table_data'] == []


def test_report_blocks_external_refs(client):
    # should error if external refs are attempted (we raise in url_fetcher)
    html = '<img src="http://example.com/image.png">'
    resp = client.post('/api/report', json={'report_html': html})
    # Central handler returns 500 in this case
    assert resp.status_code == 500
    js = resp.get_json()
    assert 'error' in js


