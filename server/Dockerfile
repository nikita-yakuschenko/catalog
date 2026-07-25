FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='ru', use_gpu=False, show_log=False)"

COPY . /app/server
WORKDIR /app/server

ENV PYTHONPATH=/app/server
ENV STORAGE_DIR=/app/storage
ENV OUTPUT_DIR=/app/output
ENV TEMPLATES_DIR=/app/templates
ENV OCR_ENABLED=true
ENV OCR_LANG=ru

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
