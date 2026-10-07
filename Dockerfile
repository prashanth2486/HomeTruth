FROM node:22-bookworm-slim AS web
WORKDIR /src
COPY web/package.json ./
COPY web/ ./
RUN npm install && npm run build

FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ libspatialindex-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=web /src/dist ./web/dist
RUN python scripts/download_data.py && python scripts/retrain.py && python scripts/build_catalog.py

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
