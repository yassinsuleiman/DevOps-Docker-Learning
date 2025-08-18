# Stage 1: Build Stage
FROM python:3.8-slim as Build

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libmariadb-dev \
    pkg-config

COPY . .

RUN pip install flask mysqlclient

# Stage 2: Production Stage
FROM python:3.8-slim

WORKDIR /app

COPY --from=Build /app /app

EXPOSE 5002

CMD ["python", "app.py"]