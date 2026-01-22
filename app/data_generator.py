import os
import time
import math
import random
from datetime import datetime, timezone

import mysql.connector


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def connect_with_retry(max_tries: int = 60, sleep_sec: float = 2.0):
    host = os.getenv("MYSQL_HOST", "mysql")
    port = env_int("MYSQL_PORT", 3306)
    db = os.getenv("MYSQL_DATABASE", "weather_station")
    user = os.getenv("MYSQL_USER", "ws_user")
    password = os.getenv("MYSQL_PASSWORD", "password")

    last_err = None
    for _ in range(max_tries):
        try:
            conn = mysql.connector.connect(
                host=host, port=port, database=db, user=user, password=password
            )
            if conn.is_connected():
                return conn
        except Exception as e:
            last_err = e
            time.sleep(sleep_sec)
    raise RuntimeError(f"Could not connect to MySQL: {last_err}")


def ensure_schema(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS station (
            id INT AUTO_INCREMENT PRIMARY KEY,
            city VARCHAR(64) NOT NULL,
            address VARCHAR(128) NOT NULL
        ) ENGINE=InnoDB;
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS reading (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            station_id INT NOT NULL,
            temperature_c DECIMAL(5,2) NOT NULL,
            humidity_pct DECIMAL(5,2) NOT NULL,
            pressure_hpa DECIMAL(6,2) NOT NULL,
            wind_speed_mps DECIMAL(5,2) NOT NULL,
            noise_db DECIMAL(5,2) NOT NULL,
            created_at DATETIME NOT NULL,
            INDEX idx_station_time (station_id, created_at),
            CONSTRAINT fk_station FOREIGN KEY (station_id) REFERENCES station(id)
                ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB;
        """
    )


def seed_stations(cur, desired_count: int):
    # Примерные ОСМЫСЛЕННЫЕ данные,которые  мы будем использовать - 100 процентов) 
    presets = [
        ("Владивосток", "ул. Светланская, д. 25"),
        ("Калининград", "Ленинский проспект, д. 12"),
        ("Санкт-Петербург", "Невский проспект, д. 88"),
        ("Москва", "ул. Тверская, д. 14"),
        ("Казань", "ул. Баумана, д. 7"),
        ("Нижний Новгород", "ул. Большая Покровская, д. 21"),
        ("Екатеринбург", "проспект Ленина, д. 50"),
        ("Новосибирск", "Красный проспект, д. 35"),
        ("Красноярск", "проспект Мира, д. 90"),
        ("Иркутск", "ул. Карла Маркса, д. 18"),
        ("Уфа", "ул. Ленина, д. 5"),
        ("Самара", "ул. Куйбышева, д. 42"),
    ]
    random.shuffle(presets)

    cur.execute("SELECT COUNT(*) FROM station;")
    count = cur.fetchone()[0]
    if count >= desired_count:
        return

    to_add = desired_count - count
    for city, addr in presets[:to_add]:
        cur.execute(
            "INSERT INTO station (city, address) VALUES (%s, %s);",
            (city, addr),
        )


# Посмотрев прогноз погоды написал различные данные , в зависимости от города разумаеется
CITY_BASE = {
    "Владивосток": {"t": -6.0, "h": 78.0, "p": 1018.0, "w": 6.2},
    "Калининград": {"t": -1.5, "h": 82.0, "p": 1011.0, "w": 5.5},
    "Санкт-Петербург": {"t": -2.5, "h": 83.0, "p": 1012.0, "w": 5.0},
    "Москва": {"t": -4.0, "h": 75.0, "p": 1014.0, "w": 3.4},
    "Казань": {"t": -8.5, "h": 73.0, "p": 1015.0, "w": 4.1},
    "Нижний Новгород": {"t": -7.5, "h": 76.0, "p": 1015.0, "w": 3.7},
    "Екатеринбург": {"t": -10.5, "h": 70.0, "p": 1016.0, "w": 3.6},
    "Новосибирск": {"t": -18.0, "h": 66.0, "p": 1019.0, "w": 2.7},
    "Красноярск": {"t": -16.0, "h": 67.0, "p": 1017.0, "w": 2.9},
    "Иркутск": {"t": -20.0, "h": 62.0, "p": 1021.0, "w": 2.4},
    "Уфа": {"t": -11.0, "h": 72.0, "p": 1016.0, "w": 3.9},
    "Самара": {"t": -9.0, "h": 71.0, "p": 1015.0, "w": 4.0},
}


def diurnal_wave(now_utc: datetime) -> float:
    # Суточная синусоида [-1..1] - интересные данные нашел)
    hour = now_utc.hour + now_utc.minute / 60.0
    return math.sin(2 * math.pi * hour / 24.0)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

# Поискав в интернете интересные методы вычисления погоды, вдохновился и стал использовать в своем проекте.
def generate(city: str, now_utc: datetime):
    base = CITY_BASE.get(city, {"t": -7.0, "h": 72.0, "p": 1015.0, "w": 3.5})
    wave = diurnal_wave(now_utc)

    # Температура: суточное колебание + небольшой шум
    temp = base["t"] + 3.0 * wave + random.gauss(0, 0.6)

    # Влажность: чаще выше ночью (обратно волне) + шум
    humidity = base["h"] - 8.0 * wave + random.gauss(0, 2.2)
    humidity = clamp(humidity, 20.0, 100.0)

    # Давление: вокруг базы, небольшая “дрожь”
    pressure = base["p"] + random.gauss(0, 1.3)

    # Ветер: неотрицательный, иногда порывы
    wind = max(0.0, random.gauss(base["w"], 1.1))
    if random.random() < 0.06:
        wind += random.uniform(3.0, 9.0)

    # Шум: зависит от ветра + городская добавка
    noise = 32.0 + 2.0 * wind + random.gauss(0, 5.0)
    if city in ("Москва", "Санкт-Петербург"):
        noise += 12.0
    elif city in ("Новосибирск", "Екатеринбург", "Казань"):
        noise += 6.0
    noise = clamp(noise, 20.0, 120.0)

    return float(temp), float(humidity), float(pressure), float(wind), float(noise)


def main():
    interval = env_float("GENERATION_INTERVAL_SECONDS", 2.0)
    stations_count = env_int("STATIONS_COUNT", 8)

    conn = connect_with_retry()
    conn.autocommit = True
    cur = conn.cursor()

    ensure_schema(cur)
    seed_stations(cur, stations_count)

    cur.execute("SELECT id, city FROM station ORDER BY id;")
    stations = cur.fetchall()
    print(f"Generator started. stations={len(stations)} interval={interval}s")

    insert_sql = """
        INSERT INTO reading
            (station_id, temperature_c, humidity_pct, pressure_hpa, wind_speed_mps, noise_db, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
    """

    while True:
        now = datetime.now(timezone.utc).replace(tzinfo=None)  # сохраняем как naive UTC
        utcnow = datetime.utcnow()
        for station_id, city in stations:
            t, h, p, w, n = generate(city, utcnow)
            cur.execute(insert_sql, (station_id, t, h, p, w, n, now))
        time.sleep(interval)


if __name__ == "__main__":
    main()
