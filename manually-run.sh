#!/bin/bash

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "🚀 Inicio da execução manual do scraping..." > /proc/1/fd/1 2>&1

. /app/run.sh > /proc/1/fd/1 2>&1 &

log "✅ Fim da execução manual do scraping..." > /proc/1/fd/1 2>&1
