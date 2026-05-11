FROM python:3.12-slim-bookworm AS base

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r ./requirements.txt

COPY app ./app

ENV PYTHONUNBUFFERED=1
WORKDIR /code

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
