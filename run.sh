#!/bin/bash

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "🚀 Executando scraping..."

/etc/openvpn/openvpn.sh python3 /app/scraping.py

log "✅ Scraping finalizado!"
