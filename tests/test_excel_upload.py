import io
from openpyxl import Workbook

def make_xlsx_bytes(rows=3):
    wb = Workbook()
    ws = wb.active
    ws.append(["year", "make", "model", "sellingprice"])
    for i in range(rows):
        ws.append([2020 + i, "Brand", f"Model{i}", 10000 + i])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_upload_excel_first_page(client):
    xlsx = make_xlsx_bytes(50)
    data = {'file': (io.BytesIO(xlsx), 'cars.xlsx')}
    resp = client.post('/api/upload?page=1&page_size=20', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    js = resp.get_json()
    assert js['total_rows'] == 50
    assert js['current_page'] == 1
    assert js['page_size'] == 20
    assert len(js['table_data']) == 20
    assert set(["year", "make", "model", "sellingprice"]).issubset(set(js['columns']))


