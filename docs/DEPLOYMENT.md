# Руководство по развертыванию

## Содержание
1. [Локальная разработка](#локальная-разработка)
2. [Production развертывание](#production-развертывание)
3. [Docker развертывание](#docker-развертывание)
4. [Безопасность](#безопасность)
5. [Мониторинг и логирование](#мониторинг-и-логирование)
6. [Масштабирование](#масштабирование)

---

## Локальная разработка

### Требования
- Python 3.11-3.12
- Node.js 18+
- npm или yarn

### Backend

```bash
# Создание виртуального окружения
python -m venv .venv

# Активация (Windows)
.\.venv\Scripts\Activate.ps1

# Активация (Linux/Mac)
source .venv/bin/activate

# Установка зависимостей
pip install -r backend/requirements.txt

# Копирование примера конфигурации
copy env.example .env  # Windows
cp env.example .env    # Linux/Mac

# Редактирование .env файла (добавьте свои ключи API)
# Запуск сервера
python backend/pdf_server.py
```

Backend будет доступен на `http://localhost:5000`

### Frontend

```bash
cd frontend

# Установка зависимостей
npm install

# Создание .env файла (опционально)
echo "REACT_APP_API_URL=http://localhost:5000" > .env
echo "REACT_APP_API_KEY=your_api_key" >> .env

# Запуск dev сервера
npm start
```

Frontend будет доступен на `http://localhost:3000`

---

## Production развертывание

### Требования для production
- Сервер с Ubuntu 20.04+ или аналогичный Linux
- Python 3.11-3.12
- Node.js 18+ (для сборки frontend)
- Nginx (рекомендуется)
- SSL сертификат (Let's Encrypt)

### Шаг 1: Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python и зависимостей
sudo apt install python3.11 python3.11-venv python3-pip nginx certbot python3-certbot-nginx

# Установка Node.js (для сборки frontend)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### Шаг 2: Развертывание Backend

```bash
# Создание пользователя для приложения
sudo useradd -m -s /bin/bash appuser
sudo su - appuser

# Клонирование репозитория
git clone <your-repo-url> /home/appuser/vcb03
cd /home/appuser/vcb03

# Создание виртуального окружения
python3.11 -m venv .venv
source .venv/bin/activate

# Установка зависимостей
pip install -r backend/requirements.txt

# Создание production .env файла
cp env.example .env
nano .env  # Отредактируйте файл
```

**Важно для production:** Установите следующие переменные в `.env`:

```bash
# ОБЯЗАТЕЛЬНО для production
TEST_MODE=false
API_KEY=<сильный_случайный_ключ_минимум_32_символа>

# LLM провайдеры (хотя бы один)
OPENAI_API_KEY=<ваш_ключ>
# или
YANDEX_FOLDER_ID=<ваш_folder_id>
YANDEX_API_KEY=<ваш_ключ>
# или
GIGACHAT_CREDENTIALS=<ваши_credentials>
GIGACHAT_CERT_PATH=russian_trusted_root_ca.cer
GIGACHAT_VERIFY_SSL_CERTS=true

# Rate limiting (опционально, настройте под нагрузку)
RATE_LIMIT_WINDOW_SEC=60
RATE_LIMIT_MAX_REQ=100

# Кэш анализа
ANALYSIS_CACHE_TTL_SEC=3600
ANALYSIS_CACHE_MAX=512

# Очистка временных файлов (минуты)
TEMP_CLEANUP_AGE_MIN=60
```

### Шаг 3: Создание systemd сервиса для Backend

Создайте файл `/etc/systemd/system/vcb03-backend.service`:

```ini
[Unit]
Description=VCb03 Backend API
After=network.target

[Service]
Type=simple
User=appuser
WorkingDirectory=/home/appuser/vcb03
Environment="PATH=/home/appuser/vcb03/.venv/bin"
ExecStart=/home/appuser/vcb03/.venv/bin/python backend/pdf_server.py
Restart=always
RestartSec=10

# Безопасность
NoNewPrivileges=true
PrivateTmp=true

# Логирование
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vcb03-backend

[Install]
WantedBy=multi-user.target
```

Запуск сервиса:

```bash
sudo systemctl daemon-reload
sudo systemctl enable vcb03-backend
sudo systemctl start vcb03-backend
sudo systemctl status vcb03-backend
```

### Шаг 4: Сборка и развертывание Frontend

```bash
cd /home/appuser/vcb03/frontend

# Установка зависимостей
npm install

# Создание production .env
echo "REACT_APP_API_URL=https://your-domain.com/api" > .env.production
echo "REACT_APP_API_KEY=<тот_же_ключ_что_и_в_backend>" >> .env.production

# Сборка production версии
npm run build

# Копирование в директорию для Nginx
sudo mkdir -p /var/www/vcb03
sudo cp -r build/* /var/www/vcb03/
sudo chown -R www-data:www-data /var/www/vcb03
```

### Шаг 5: Настройка Nginx

Создайте файл `/etc/nginx/sites-available/vcb03`:

```nginx
# Редирект HTTP на HTTPS
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS конфигурация
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL сертификаты (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL настройки безопасности
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Логирование
    access_log /var/log/nginx/vcb03-access.log;
    error_log /var/log/nginx/vcb03-error.log;

    # Frontend (статичные файлы)
    root /var/www/vcb03;
    index index.html;

    # API проксирование на backend
    location /api {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Таймауты для больших файлов
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Максимальный размер загружаемого файла
        client_max_body_size 100M;
    }

    # Frontend (SPA routing)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Безопасность заголовки
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
}
```

Активация конфигурации:

```bash
sudo ln -s /etc/nginx/sites-available/vcb03 /etc/nginx/sites-enabled/
sudo nginx -t  # Проверка конфигурации
sudo systemctl reload nginx
```

### Шаг 6: Получение SSL сертификата

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
sudo systemctl reload nginx
```

Certbot автоматически обновит конфигурацию Nginx и настроит автоматическое обновление сертификата.

---

## Docker развертывание

### Production Docker Compose

Создайте файл `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
    environment:
      TEST_MODE: "false"
      FLASK_DEBUG: "0"
      API_KEY: "${API_KEY}"
      OPENAI_API_KEY: "${OPENAI_API_KEY}"
      YANDEX_FOLDER_ID: "${YANDEX_FOLDER_ID}"
      YANDEX_API_KEY: "${YANDEX_API_KEY}"
      GIGACHAT_CREDENTIALS: "${GIGACHAT_CREDENTIALS}"
      GIGACHAT_CERT_PATH: "${GIGACHAT_CERT_PATH:-russian_trusted_root_ca.cer}"
      GIGACHAT_VERIFY_SSL_CERTS: "${GIGACHAT_VERIFY_SSL_CERTS:-true}"
      RATE_LIMIT_WINDOW_SEC: "${RATE_LIMIT_WINDOW_SEC:-60}"
      RATE_LIMIT_MAX_REQ: "${RATE_LIMIT_MAX_REQ:-100}"
      ANALYSIS_CACHE_TTL_SEC: "${ANALYSIS_CACHE_TTL_SEC:-3600}"
      ANALYSIS_CACHE_MAX: "${ANALYSIS_CACHE_MAX:-512}"
      TEMP_CLEANUP_AGE_MIN: "${TEMP_CLEANUP_AGE_MIN:-60}"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/test"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - vcb03-network

  frontend:
    build:
      context: ./frontend
      args:
        REACT_APP_API_URL: "${REACT_APP_API_URL:-https://your-domain.com/api}"
    restart: unless-stopped
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - vcb03-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    restart: unless-stopped
    depends_on:
      - backend
      - frontend
    networks:
      - vcb03-network

networks:
  vcb03-network:
    driver: bridge
```

Запуск:

```bash
# Создание .env файла с production переменными
cp env.example .env.prod
# Отредактируйте .env.prod

# Запуск
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Просмотр логов
docker compose -f docker-compose.prod.yml logs -f
```

---

## Безопасность

### Обязательные настройки для production

1. **API_KEY обязателен**
   ```bash
   TEST_MODE=false
   API_KEY=<сильный_случайный_ключ>
   ```

2. **Не храните секреты в Git**
   - `.env` файлы должны быть в `.gitignore`
   - Используйте переменные окружения или секреты Docker/Kubernetes

3. **HTTPS обязателен**
   - Все соединения должны быть через HTTPS
   - Используйте Let's Encrypt для бесплатных сертификатов

4. **Rate Limiting**
   - Настройте `RATE_LIMIT_MAX_REQ` под вашу нагрузку
   - Мониторьте блокировки в логах

5. **Ограничение размера файлов**
   - Максимальный размер файла: 100 МБ (настроено в Flask)
   - При необходимости увеличьте в `backend/pdf_server.py`

### Рекомендации по безопасности

- Регулярно обновляйте зависимости: `pip list --outdated`
- Используйте firewall (ufw) для ограничения доступа
- Настройте автоматические бэкапы данных
- Мониторьте логи на подозрительную активность
- Используйте отдельного пользователя для запуска приложения (не root)

---

## Мониторинг и логирование

### Просмотр логов Backend

```bash
# Systemd логи
sudo journalctl -u vcb03-backend -f

# Docker логи
docker compose logs -f backend
```

### Просмотр логов Nginx

```bash
sudo tail -f /var/log/nginx/vcb03-access.log
sudo tail -f /var/log/nginx/vcb03-error.log
```

### Мониторинг производительности

Рекомендуется использовать:
- **Prometheus + Grafana** для метрик
- **Sentry** для отслеживания ошибок
- **ELK Stack** для централизованного логирования

### Healthcheck endpoint

Backend предоставляет endpoint для проверки здоровья:

```bash
curl https://your-domain.com/api/test
```

Ответ:
```json
{
  "status": "ok",
  "message": "Сервер работает!",
  "timestamp": "2024-12-19T12:00:00",
  "version": "1.0"
}
```

---

## Масштабирование

### Горизонтальное масштабирование Backend

Для увеличения производительности можно запустить несколько экземпляров backend за load balancer:

```nginx
upstream backend_servers {
    least_conn;
    server localhost:5000;
    server localhost:5001;
    server localhost:5002;
}

location /api {
    proxy_pass http://backend_servers;
    # ... остальные настройки proxy
}
```

**Важно:** При горизонтальном масштабировании:
- Rate limiting будет работать независимо на каждом сервере
- Кэш анализа не будет общим между серверами
- Временные файлы хранятся локально на каждом сервере

Для решения этих проблем рассмотрите использование:
- Redis для общего rate limiting и кэша
- Общее хранилище файлов (S3, NFS)

### Вертикальное масштабирование

Увеличьте ресурсы сервера:
- CPU: для обработки больших файлов
- RAM: для кэширования DataFrame (Excel/PDF)
- Disk: для временных файлов

---

## Troubleshooting

### Backend не запускается

1. Проверьте логи: `sudo journalctl -u vcb03-backend -n 50`
2. Проверьте переменные окружения в `.env`
3. Убедитесь что порт 5000 свободен: `sudo netstat -tulpn | grep 5000`

### Frontend не подключается к Backend

1. Проверьте `REACT_APP_API_URL` в `.env.production`
2. Проверьте CORS настройки в `backend/pdf_server.py`
3. Проверьте что Nginx правильно проксирует `/api` запросы

### SSL сертификат не работает

1. Проверьте что домен указывает на ваш сервер: `dig your-domain.com`
2. Убедитесь что порты 80 и 443 открыты в firewall
3. Проверьте конфигурацию Nginx: `sudo nginx -t`

---

## Поддержка

При возникновении проблем:
1. Проверьте логи (см. раздел "Мониторинг")
2. Убедитесь что все переменные окружения установлены правильно
3. Проверьте что все зависимости установлены
4. Создайте issue в репозитории с описанием проблемы и логами
