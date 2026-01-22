FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir mysql-connector-python==8.3.0

COPY data_generator.py /app/data_generator.py

CMD ["python", "data_generator.py"]