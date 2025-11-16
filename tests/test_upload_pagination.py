import io
import csv

def make_csv_bytes(rows=2500):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["year", "make", "model", "sellingprice", "saledate"])
    for i in range(rows):
        writer.writerow([2000 + (i % 20), "Brand"+str(i%5), "Model"+str(i%10), 10000 + i, "2022-01-{:02d}".format((i % 28) + 1)])
    data = buf.getvalue().encode("utf-8")
    buf.close()
    return data


def test_upload_first_page_returns_dataset_id(client):
    data = {
        'file': (io.BytesIO(make_csv_bytes(1500)), 'cars.csv')
    }
    resp = client.post('/api/upload?page=1&page_size=1000', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    js = resp.get_json()
    assert 'dataset_id' in js
    assert js['current_page'] == 1
    assert js['page_size'] == 1000
    assert js['total_rows'] == 1500
    assert len(js['table_data']) == 1000


def test_upload_next_page_via_endpoint(client):
    # upload first
    data = {
        'file': (io.BytesIO(make_csv_bytes(2200)), 'cars.csv')
    }
    resp = client.post('/api/upload?page=1&page_size=1000', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    js = resp.get_json()
    ds = js['dataset_id']

    # page 2
    resp2 = client.post('/api/upload/page', json={'dataset_id': ds, 'page': 2, 'page_size': 1000})
    assert resp2.status_code == 200
    js2 = resp2.get_json()
    assert js2['current_page'] == 2
    assert len(js2['table_data']) == 1000

    # page 3 (partial)
    resp3 = client.post('/api/upload/page', json={'dataset_id': ds, 'page': 3, 'page_size': 1000})
    assert resp3.status_code == 200
    js3 = resp3.get_json()
    assert js3['current_page'] == 3
    assert len(js3['table_data']) == 200


