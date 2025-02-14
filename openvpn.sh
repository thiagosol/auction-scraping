#!/bin/bash

echo "🔄 Verificando conexão VPN..."

if ip a show tun0 up > /dev/null 2>&1; then
    echo "✅ VPN já está conectada!"
else
    echo "🔄 Iniciando VPN..."

    openvpn --config /etc/openvpn/credentials.ovpn --auth-user-pass /etc/openvpn/auth.txt --log /var/log/openvpn.log --verb 4 &

    sleep 5
    while ! ip a show tun0 up > /dev/null 2>&1; do
        echo "⏳ Aguardando VPN conectar..."
        sleep 2
    done

    echo "✅ VPN conectada!"
fi
