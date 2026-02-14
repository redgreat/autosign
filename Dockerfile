FROM python:3.13.3-slim

WORKDIR /app

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

RUN apt-get update && apt-get install -y \
    gcc \
    tzdata \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/logs \
    && chown -R appuser:appuser /app

RUN if [ -f /app/conf/config.yml ]; then cp /app/conf/config.yml /app/config.yml; fi

COPY docker/supervisord.conf /etc/supervisor/supervisord.conf

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "python.*all_checkin.py" || exit 1

CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
