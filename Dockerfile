FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["sh", "-c", "mkdir -p /data /data/cache /data/exports /app/logs && for file in stock_trade_calendar.csv stock_basic.csv data.parquet; do if [ ! -f \"/data/$file\" ] && [ -f \"/app/data/$file\" ]; then cp \"/app/data/$file\" \"/data/$file\"; fi; done && python -c \"from utils.db_helper import init_db; init_db()\" && exec streamlit run app.py --server.port \"${PORT:-8501}\" --server.address 0.0.0.0 --server.headless true"]
