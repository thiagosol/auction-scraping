#!/bin/bash

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "🔄 Verificando conexão VPN..."

if ip a show tun0 up > /dev/null 2>&1; then
    log "✅ VPN já está conectada!"
else
    log "🔄 Iniciando VPN..."

    openvpn --config /etc/openvpn/credentials.ovpn --auth-user-pass /etc/openvpn/auth.txt --verb 4 > /proc/1/fd/1 2>&1 &

    sleep 5
    while ! ip a show tun0 up > /dev/null 2>&1; do
        log "⏳ Aguardando VPN conectar..."
        sleep 2
    done

    log "✅ VPN conectada!"
fi
