FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_DEBUG=0 \
    DJANGO_ALLOWED_HOSTS=.hf.space,localhost,127.0.0.1,testserver \
    DJANGO_MEDIA_ROOT=/tmp/smart-crop-ai-media \
    PORT=7860

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-space.txt .
RUN pip install --upgrade pip && pip install -r requirements-space.txt

COPY . .

RUN chmod +x /app/space-entrypoint.sh

EXPOSE 7860

CMD ["/app/space-entrypoint.sh"]
