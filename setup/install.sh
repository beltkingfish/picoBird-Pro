#!/usr/bin/env bash
# picoBird Pro — Pi 5 setup script
# Run as root on a fresh Raspberry Pi OS Lite (64-bit) image.
set -euo pipefail

PROJECT_DIR="/opt/picobird-pro"
DATA_DIR="/var/lib/picobird-pro"
SERVICE_USER="picobird"
AP_SSID="picoBirdPro"
AP_PASS="fieldguide"
AP_IP="192.168.4.1"
WIFI_IF="wlan0"   # change to wlan1 if using a USB dongle for the AP

echo "==> Installing system packages"
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    hostapd dnsmasq \
    git ffmpeg \
    libatlas-base-dev  # NumPy dependency for BirdNET

echo "==> Creating service user"
id -u "$SERVICE_USER" &>/dev/null || useradd -r -s /sbin/nologin "$SERVICE_USER"

echo "==> Setting up project directory"
mkdir -p "$PROJECT_DIR" "$DATA_DIR"
cp -r "$(dirname "$0")/../server" "$PROJECT_DIR/"
chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR" "$DATA_DIR"

echo "==> Installing Python dependencies"
python3 -m venv "$PROJECT_DIR/venv"
"$PROJECT_DIR/venv/bin/pip" install --upgrade pip -q
"$PROJECT_DIR/venv/bin/pip" install -r "$PROJECT_DIR/server/requirements.txt" -q

echo "==> Installing BirdNET-Analyzer"
if [ ! -d /opt/BirdNET-Analyzer ]; then
    git clone --depth 1 https://github.com/kahst/BirdNET-Analyzer /opt/BirdNET-Analyzer
    "$PROJECT_DIR/venv/bin/pip" install -r /opt/BirdNET-Analyzer/requirements.txt -q
fi

# ---------------------------------------------------------------------------
# WiFi Access Point (hostapd + dnsmasq)
# ---------------------------------------------------------------------------
echo "==> Configuring hostapd"
cat > /etc/hostapd/hostapd.conf <<EOF
interface=$WIFI_IF
driver=nl80211
ssid=$AP_SSID
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$AP_PASS
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF
sed -i 's|#DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

echo "==> Configuring dnsmasq"
mv /etc/dnsmasq.conf /etc/dnsmasq.conf.bak 2>/dev/null || true
cat > /etc/dnsmasq.conf <<EOF
interface=$WIFI_IF
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
EOF

echo "==> Setting static IP for $WIFI_IF"
cat >> /etc/dhcpcd.conf <<EOF

interface $WIFI_IF
    static ip_address=$AP_IP/24
    nohook wpa_supplicant
EOF

echo "==> Enabling services"
systemctl unmask hostapd
systemctl enable hostapd dnsmasq

# ---------------------------------------------------------------------------
# systemd service
# ---------------------------------------------------------------------------
echo "==> Installing picoBird Pro systemd service"
cp "$(dirname "$0")/picobird-pro.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable picobird-pro

echo ""
echo "====================================================="
echo " Setup complete!"
echo " Set your eBird API key before starting the service:"
echo "   sudo systemctl edit picobird-pro"
echo "   Add: [Service]"
echo "        Environment=EBIRD_API_KEY=your_key_here"
echo " Then: sudo systemctl start picobird-pro"
echo "====================================================="
