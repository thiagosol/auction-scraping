FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    libnss3 \
    libatk1.0-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcups2 \
    libxss1 \
    cron \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG DB_USER
ARG DB_PASS
ARG DB_HOST

ENV DB_USER=$DB_USER
ENV DB_PASS=$DB_PASS
ENV DB_HOST=$DB_HOST

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -c "from pyppeteer import chromium_downloader; chromium_downloader.download_chromium()"

COPY cronjob /etc/cron.d/auction_scraping
RUN chmod 0644 /etc/cron.d/auction_scraping && crontab /etc/cron.d/auction_scraping

RUN chmod +x /app/run.sh

CMD ["cron", "-f"]
