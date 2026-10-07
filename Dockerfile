FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ libspatialindex-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python scripts/download_data.py && python scripts/retrain.py

EXPOSE 8501
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
