#!/usr/bin/env bash
# picoBird Pro — Pi 5 full setup script
# Run as root on a fresh Raspberry Pi OS Lite (64-bit) image.
#
# Boot sequence installed:
#   hostapd + dnsmasq       — WiFi AP 'picoBirdPro'
#   picobird-pre.service    — one-shot DB init + taxonomy sync
#   picobird-pro.service    — Flask/Gunicorn API on :5000
#   picobird-vitals.service — e-ink dashboard (30 s refresh)
#   picobird-button.service — physical GPIO reset button watcher
#   /etc/profile.d          — admin console on physical console login

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

PROJECT_DIR="/opt/picobird-pro"
DATA_DIR="/var/lib/picobird-pro"
SERVICE_USER="picobird"

AP_SSID="picoBirdPro"
AP_PASS="fieldguide"
AP_IP="192.168.4.1"
WIFI_IF="wlan0"

echo "====================================================="
echo " picoBird Pro — Pi 5 setup"
echo "====================================================="

# ---------------------------------------------------------------------------
echo ""
echo "==> [1/9] Installing system packages"
# ---------------------------------------------------------------------------
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    hostapd dnsmasq \
    git ffmpeg \
    libopenblas-dev \
    libopenjp2-7 libjpeg-dev libfreetype-dev \
    fonts-dejavu-core \
    python3-rpi.gpio python3-spidev

# ---------------------------------------------------------------------------
echo ""
echo "==> [2/9] Creating service user '$SERVICE_USER'"
# ---------------------------------------------------------------------------
id -u "$SERVICE_USER" &>/dev/null || useradd -r -s /sbin/nologin "$SERVICE_USER"
usermod -aG spi,gpio "$SERVICE_USER" 2>/dev/null || true

# ---------------------------------------------------------------------------
echo ""
echo "==> [3/9] Setting up project directory"
# ---------------------------------------------------------------------------
mkdir -p "$PROJECT_DIR" "$DATA_DIR"
rsync -a --delete "$REPO_DIR/server/" "$PROJECT_DIR/server/"
rsync -a "$REPO_DIR/setup/preflight.py" "$PROJECT_DIR/setup/preflight.py"
chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR" "$DATA_DIR"

# ---------------------------------------------------------------------------
echo ""
echo "==> [4/9] Installing Python dependencies"
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
echo "==> [5/9] Installing BirdNET-Analyzer"
# ---------------------------------------------------------------------------
if [ ! -d /opt/BirdNET-Analyzer ]; then
    git clone --depth 1 https://github.com/kahst/BirdNET-Analyzer /opt/BirdNET-Analyzer
    "$PROJECT_DIR/venv/bin/pip" install -r /opt/BirdNET-Analyzer/requirements.txt -q
else
    echo "    Already installed, skipping clone."
fi

# ---------------------------------------------------------------------------
echo ""
echo "==> [6/9] Configuring WiFi Access Point (hostapd + dnsmasq)"
# ---------------------------------------------------------------------------
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
echo "==> [7/9] Enabling hostapd + dnsmasq"
# ---------------------------------------------------------------------------
systemctl unmask hostapd 2>/dev/null || true
systemctl enable hostapd dnsmasq

# ---------------------------------------------------------------------------
echo ""
echo "==> [8/9] Installing picoBird Pro systemd services"
# ---------------------------------------------------------------------------
for svc in picobird-pre picobird-pro picobird-vitals picobird-button; do
    cp "$SCRIPT_DIR/${svc}.service" /etc/systemd/system/
    sed -i "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|" \
        /etc/systemd/system/${svc}.service
done

systemctl daemon-reload
systemctl enable picobird-pre picobird-pro picobird-vitals picobird-button

# ---------------------------------------------------------------------------
echo ""
echo "==> [9/9] Installing local admin console"
# ---------------------------------------------------------------------------
cp "$SCRIPT_DIR/picobird-console.sh" /etc/profile.d/picobird-console.sh
chmod +x /etc/profile.d/picobird-console.sh

chmod o+x "$PROJECT_DIR/venv/bin/python"
chmod o+x "$PROJECT_DIR/venv/bin/python3" 2>/dev/null || true

SUDOERS_FILE="/etc/sudoers.d/picobird-console"
cat > "$SUDOERS_FILE" <<'EOF'
# picoBird Pro — allow any local user to manage picoBird services
ALL ALL=(root) NOPASSWD: /bin/systemctl restart picobird-pro picobird-vitals picobird-pre
ALL ALL=(root) NOPASSWD: /bin/systemctl stop picobird-pro picobird-vitals picobird-pre
ALL ALL=(root) NOPASSWD: /bin/systemctl start picobird-pro picobird-vitals picobird-pre
EOF
chmod 0440 "$SUDOERS_FILE"

echo ""
echo "====================================================="
echo " Setup complete!"
echo ""
echo " Boot sequence (fully automatic on every startup):"
echo "   hostapd + dnsmasq  →  WiFi AP 'picoBirdPro' up"
echo "   picobird-pre        →  DB init, taxonomy sync"
echo "   picobird-pro        →  Flask API on :5000"
echo "   picobird-vitals     →  e-ink dashboard"
echo "   picobird-button     →  GPIO 26 reset button"
echo ""
echo " Physical console login → admin console auto-launches"
echo " SSH login             → normal bash (unaffected)"
echo " Type 'picobird-console' to reopen the console"
echo ""
echo " Before first boot, set your eBird API key:"
echo "   sudo systemctl edit picobird-pro"
echo "   sudo systemctl edit picobird-pre"
echo "   Add under [Service]:"
echo "     Environment=EBIRD_API_KEY=your_key_here"
echo ""
echo " Then reboot: sudo reboot"
echo "====================================================="
