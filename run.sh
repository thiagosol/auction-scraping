#!/bin/bash

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

. /etc/openvpn/openvpn.sh

log "🚀 Executando scraping..."

python3 /app/scraping.py

log "✅ Scraping finalizado!"
