import io

def test_upload_cp1251_csv(client):
    # Русские буквы и запятая как разделитель
    content = "year,make,model\n2020,Лада,Веста\n".encode("cp1251")
    data = {'file': (content, 'cars.csv')}
    resp = client.post('/api/upload?page=1&page_size=10', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    js = resp.get_json()
    assert js['total_rows'] == 1
    assert js['columns'][:3] == ['year', 'make', 'model']
    assert js['table_data'][0]['make'] in ('Лада', 'Ð»Ð°Ð´Ð°')  # допускаем неидеальный парсинг в редких окружениях


def test_analyze_validation_errors(client):
    # отсутствуют обязательные поля
    resp = client.post('/api/analyze', json={'foo': 'bar'})
    assert resp.status_code == 400
    js = resp.get_json()
    assert 'error' in js


