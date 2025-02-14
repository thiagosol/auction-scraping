#!/bin/bash

echo "🔄 Iniciando conexão VPN..."

openvpn --config /etc/openvpn/credentials.ovpn --auth-user-pass /etc/openvpn/auth.txt --daemon

VPN_CONNECTED=0
for i in {1..10}; do
    sleep 5  # Espera 5 segundos antes de testar a conexão
    echo "🔍 Verificando conexão VPN... (tentativa $i/10)"
    
    # Testa se o IP externo mudou (indicando que a VPN conectou)
    VPN_IP=$(curl -s --max-time 5 ifconfig.me)
    if [[ -n "$VPN_IP" ]]; then
        echo "✅ VPN conectada com IP: $VPN_IP"
        VPN_CONNECTED=1
        break
    fi
done

if [[ $VPN_CONNECTED -eq 0 ]]; then
    echo "❌ Falha ao conectar à VPN!"
    exit 1
fi

exec "$@"
