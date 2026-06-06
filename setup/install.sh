#!/usr/bin/env bash
# picoBird Pro — Pi 5 full setup script
# Run as root on a fresh Raspberry Pi OS Lite (64-bit) image.
#
# What this does:
#   1. Installs system packages (Python, hostapd, dnsmasq, Pillow deps)
#   2. Creates the 'picobird' service user
#   3. Copies server code to /opt/picobird-pro
#   4. Creates Python venv + installs dependencies
#   5. Clones BirdNET-Analyzer
#   6. Configures hostapd + dnsmasq WiFi AP
#   7. Installs and enables four systemd services:
#        picobird-pre.service    — one-shot boot preflight (DB init, taxonomy)
#        picobird-pro.service    — Flask/Gunicorn API server
#        picobird-vitals.service — e-ink vitals display
#   8. Adds RPi.GPIO + spidev + Pillow for the e-ink display

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

PROJECT_DIR="/opt/picobird-pro"
DATA_DIR="/var/lib/picobird-pro"
SERVICE_USER="picobird"

AP_SSID="picoBirdPro"
AP_PASS="fieldguide"
AP_IP="192.168.4.1"
WIFI_IF="wlan0"   # change to wlan1 if using a USB dongle for the AP

echo "====================================================="
echo " picoBird Pro — Pi 5 setup"
echo "====================================================="

# ---------------------------------------------------------------------------
echo ""
echo "==> [1/8] Installing system packages"
# ---------------------------------------------------------------------------
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    hostapd dnsmasq \
    git ffmpeg \
    libatlas-base-dev \
    libopenjp2-7 libjpeg-dev libfreetype6-dev \
    fonts-dejavu-core \
    python3-rpi.gpio python3-spidev

# ---------------------------------------------------------------------------
echo ""
echo "==> [2/8] Creating service user '$SERVICE_USER'"
# ---------------------------------------------------------------------------
id -u "$SERVICE_USER" &>/dev/null || useradd -r -s /sbin/nologin "$SERVICE_USER"
# Allow picobird to access SPI and GPIO
usermod -aG spi,gpio "$SERVICE_USER" 2>/dev/null || true

# ---------------------------------------------------------------------------
echo ""
echo "==> [3/8] Setting up project directory"
# ---------------------------------------------------------------------------
mkdir -p "$PROJECT_DIR" "$DATA_DIR"
rsync -a --delete "$REPO_DIR/server/" "$PROJECT_DIR/server/"
rsync -a          "$REPO_DIR/setup/preflight.py" "$PROJECT_DIR/setup/preflight.py"
chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR" "$DATA_DIR"

# ---------------------------------------------------------------------------
echo ""
echo "==> [4/8] Installing Python dependencies"
# ---------------------------------------------------------------------------
python3 -m venv "$PROJECT_DIR/venv"
"$PROJECT_DIR/venv/bin/pip" install --upgrade pip -q
"$PROJECT_DIR/venv/bin/pip" install \
    flask>=3.0 \
    requests>=2.31 \
    gunicorn>=21.2 \
    RPi.GPIO \
    spidev \
    Pillow -q

# ---------------------------------------------------------------------------
echo ""
echo "==> [5/8] Installing BirdNET-Analyzer"
# ---------------------------------------------------------------------------
if [ ! -d /opt/BirdNET-Analyzer ]; then
    git clone --depth 1 https://github.com/kahst/BirdNET-Analyzer /opt/BirdNET-Analyzer
    "$PROJECT_DIR/venv/bin/pip" install -r /opt/BirdNET-Analyzer/requirements.txt -q
else
    echo "    Already installed, skipping clone."
fi

# ---------------------------------------------------------------------------
echo ""
echo "==> [6/8] Configuring WiFi Access Point (hostapd + dnsmasq)"
# ---------------------------------------------------------------------------

# Static IP for the AP interface
if ! grep -q "interface $WIFI_IF" /etc/dhcpcd.conf 2>/dev/null; then
    cat >> /etc/dhcpcd.conf <<EOF

# picoBird Pro AP
interface $WIFI_IF
    static ip_address=$AP_IP/24
    nohook wpa_supplicant
EOF
fi

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

[ -f /etc/dnsmasq.conf ] && mv /etc/dnsmasq.conf /etc/dnsmasq.conf.bak
cat > /etc/dnsmasq.conf <<EOF
interface=$WIFI_IF
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
EOF

# Enable SPI for the e-ink display
if ! grep -q "^dtparam=spi=on" /boot/firmware/config.txt 2>/dev/null; then
    echo "dtparam=spi=on" >> /boot/firmware/config.txt
    echo "    SPI enabled in config.txt (reboot required)"
fi

# ---------------------------------------------------------------------------
echo ""
echo "==> [7/8] Enabling system services"
# ---------------------------------------------------------------------------
systemctl unmask hostapd 2>/dev/null || true
systemctl enable hostapd dnsmasq

# ---------------------------------------------------------------------------
echo ""
echo "==> [8/8] Installing picoBird Pro systemd services"
# ---------------------------------------------------------------------------
cp "$SCRIPT_DIR/picobird-pre.service"    /etc/systemd/system/
cp "$SCRIPT_DIR/picobird-pro.service"    /etc/systemd/system/
cp "$SCRIPT_DIR/picobird-vitals.service" /etc/systemd/system/

# Point the services at the installed location
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|" \
    /etc/systemd/system/picobird-pro.service \
    /etc/systemd/system/picobird-vitals.service

systemctl daemon-reload
systemctl enable picobird-pre picobird-pro picobird-vitals

echo ""
echo "====================================================="
echo " Setup complete!"
echo ""
echo " Boot sequence (automatic on every startup):"
echo "   hostapd + dnsmasq  →  WiFi AP 'picoBirdPro' up"
echo "   picobird-pre        →  DB init, taxonomy sync"
echo "   picobird-pro        →  Flask API on :5000"
echo "   picobird-vitals     →  e-ink dashboard refresh"
echo ""
echo " Before first boot, set your eBird API key:"
echo "   sudo systemctl edit picobird-pro picobird-pre"
echo "   Add under [Service]:"
echo "     Environment=EBIRD_API_KEY=your_key_here"
echo ""
echo " Then reboot:"
echo "   sudo reboot"
echo "====================================================="
