FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    chromium \
    chromium-driver \
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
    vim \
    openvpn \
    curl \
    iproute2 \
    libxml2 \
    libxslt1.1 \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG DB_POSTGRES_USER
ARG DB_POSTGRES_PASS
ARG SERVER_IP

ENV DB_POSTGRES_USER=$DB_POSTGRES_USER
ENV DB_POSTGRES_PASS=$DB_POSTGRES_PASS
ENV SERVER_IP=$SERVER_IP

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY cronjob /etc/cron.d/auction_scraping

RUN sed -i "s|DB_USER=.*|DB_USER=${DB_POSTGRES_USER}|" /etc/cron.d/auction_scraping && \
    sed -i "s|DB_PASS=.*|DB_PASS=${DB_POSTGRES_PASS}|" /etc/cron.d/auction_scraping && \
    sed -i "s|DB_HOST=.*|DB_HOST=${SERVER_IP}|" /etc/cron.d/auction_scraping

RUN chmod 0644 /etc/cron.d/auction_scraping && crontab /etc/cron.d/auction_scraping

ENV CHROMIUM_PATH="/usr/bin/chromium"

RUN mkdir -p /etc/openvpn
COPY openvpn.sh /etc/openvpn/openvpn.sh
RUN chmod +x /etc/openvpn/openvpn.sh

RUN chmod +x /app/run.sh
RUN chmod +x /app/manually-run.sh

CMD ["cron", "-f"]
