#!/bin/bash

echo "🔗 Verificando conexão VPN..."

if ! pgrep -x "openvpn" > /dev/null
then
    echo "🌍 Conectando à VPN..."
    openvpn --config /etc/openvpn/credentials.ovpn --daemon
else
    echo "✅ VPN já conectada!"
fi

sleep 5

exec "$@"
