# Мини-система сбора и анализа данных для ПО «Погодная станция»

Проект генерирует осмысленные погодные показания (температура, влажность, давление, ветер, шум), сохраняет их в MySQL и позволяет анализировать через Redash (дашборд с 3+ визуализациями).

## ER-диаграмма БД
```mermaid
erDiagram
    station ||--o{ reading : "1 station -> many readings"

    station {
        INT id PK
        VARCHAR city
        VARCHAR address
    }

    reading {
        BIGINT id PK
        INT station_id FK
        DECIMAL temperature_c
        DECIMAL humidity_pct
        DECIMAL pressure_hpa
        DECIMAL wind_speed_mps
        DECIMAL noise_db
        DATETIME created_at
    }
Таблица reading содержит индекс idx_station_time (station_id, created_at) для быстрых запросов по станции и времени.

Требования:

Docker + Docker Compose
Свободные порты: 80, 3306, 5000


Запуск проекта:
1)Клонируй репозиторий: 
git clone <https://github.com/DDLST/Weather-station-analytics.git>
cd weather-station-analytics

2) Создай .env из примера и замени пароли:
cp .env.example .env

3) Запусти сервисы:
docker compose -f docker-compose.yaml up -d --build

4) Один раз инициализируй Redash:
docker compose -f docker-compose.yaml run --rm redash_server create_db

Redash

Открой в браузере: http://<IP_сервера> (первый запуск попросит создать пользователя)
Подключение MySQL как Data Source

Settings → Data Sources → New Data Source → MySQL:

Host: mysql
Port: 3306
Database: weather_station
User: ws_user
Password: пароль из .env

Скриншоты:
screenshots/Найстройкасхем1.png
screenshots/Найстройкасхем3.png
screenshots/Настройкасхем4.png
screenshots/ИТОГСХЕМ.png

Остановка:
docker compose -f docker-compose.yaml down

Важные замечания:
Что было изменено в проекте (на VDS Ubuntu)
1) docker-compose.yaml — оптимизация Redash под слабый сервер (2 GB RAM)

Чтобы Redash не “съедал” всю оперативную память и не вызывал таймауты в интерфейсе, мы уменьшили количество процессов:

В сервисе redash_server:

REDASH_WEB_WORKERS уменьшили с 4 до 1

В сервисе redash_worker:

WORKERS_COUNT уменьшили с 2 до 1

QUEUES сократили до:

"queries,scheduled_queries,schemas"
(убрали лишние очереди вроде periodic,emails,default, чтобы снизить нагрузку)

Это снизило потребление RAM/CPU и стабилизировало работу Redash.

2) Управление генератором данных (контейнер generator)

Во время настройки Redash и выполнения первых запросов генератор временно останавливали, чтобы он не нагружал MySQL и не ухудшал отклик системы:

Остановка генератора:
docker compose stop generator

После настройки запросов/визуализаций генератор включили обратно:
Запуск генератора:
docker compose start generator