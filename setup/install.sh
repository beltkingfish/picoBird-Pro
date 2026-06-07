#!/usr/bin/env bash
# picoBird Pro — Pi 5 setup wizard
# Run as root on a fresh Raspberry Pi OS Lite (64-bit) image.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

PROJECT_DIR="/opt/picobird-pro"
DATA_DIR="/var/lib/picobird-pro"
SERVICE_USER="picobird"
WIFI_IF="wlan0"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ask() {
    # ask <variable> <prompt> [default]
    local var="$1" prompt="$2" default="${3:-}"
    while true; do
        if [ -n "$default" ]; then
            read -rp "$prompt [$default]: " value </dev/tty
            value="${value:-$default}"
        else
            read -rp "$prompt: " value </dev/tty
        fi
        if [ -n "$value" ]; then
            eval "$var=\"$value\""
            return
        fi
        echo "  This field is required."
    done
}

ask_optional() {
    local var="$1" prompt="$2" default="${3:-}"
    if [ -n "$default" ]; then
        read -rp "$prompt [$default]: " value </dev/tty
        eval "$var=\"${value:-$default}\""
    else
        read -rp "$prompt (leave blank to skip): " value </dev/tty
        eval "$var=\"$value\""
    fi
}

ask_secret() {
    # Like ask but hides input
    local var="$1" prompt="$2"
    while true; do
        read -rsp "$prompt: " value </dev/tty
        echo
        if [ -n "$value" ]; then
            eval "$var=\"$value\""
            return
        fi
        echo "  This field is required."
    done
}

print_header() {
    echo ""
    echo "====================================================="
    echo " $1"
    echo "====================================================="
    echo ""
}

gen_password() {
    # 12-char alphanumeric random default (avoids ambiguous chars).
    tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 12
}

detect_wifi_iface() {
    # Echo the first wireless interface, or empty if none.
    local iface
    for iface in /sys/class/net/*/wireless; do
        [ -e "$iface" ] && basename "$(dirname "$iface")" && return 0
    done
    # Fallback: any wlan* device
    ip -o link show 2>/dev/null | grep -oE 'wlan[0-9]+' | head -1
}

validate_ebird_key() {
    # Format check + one live API call. Returns 0 if valid, 1 otherwise.
    local key="$1"
    if ! printf '%s' "$key" | grep -qE '^[A-Za-z0-9]+$'; then
        echo "  Invalid format — eBird keys are alphanumeric."
        return 1
    fi
    echo "  Testing key against the eBird API..."
    local code
    code=$(curl -s -o /dev/null -w '%{http_code}' -m 8 \
        -H "X-eBirdApiToken: $key" \
        "https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=json&cat=species&locale=en&spp=norcar" \
        2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        echo "  Key validated."
        return 0
    fi
    if [ "$code" = "000" ]; then
        echo "  Could not reach eBird (offline?). Skipping live check."
        return 0   # don't block offline installs
    fi
    echo "  eBird rejected the key (HTTP $code)."
    return 1
}

# ---------------------------------------------------------------------------
# Welcome
# ---------------------------------------------------------------------------
clear
print_header "picoBird Pro — Pi 5 Setup Wizard"
cat <<'EOF'
Welcome! This wizard will set up your Pi 5 as a picoBird Pro
field guide server. It will:

  • Create a WiFi hotspot the PicoCalc connects to
  • Install the picoBird Pro API server
  • Load the full eBird species database (~17,000 species)
  • Set up BirdNET sound identification
  • Configure everything to start automatically on boot

This will take about 10-20 minutes depending on your
internet connection speed.

Press Enter to continue, or Ctrl+C to cancel.
EOF
read -r </dev/tty

# ---------------------------------------------------------------------------
# Gather settings
# ---------------------------------------------------------------------------
print_header "Step 1 of 3 — eBird API Key"
cat <<'EOF'
picoBird Pro uses the eBird API to load bird species data.
A free API key is required.

To get your key:
  1. Create a free account at https://ebird.org
  2. Visit https://ebird.org/api/keygen
  3. Copy the key shown on that page

EOF
ask EBIRD_API_KEY "Enter your eBird API key"
while ! validate_ebird_key "$EBIRD_API_KEY"; do
    ask EBIRD_API_KEY "Re-enter your eBird API key"
done

print_header "Step 2 of 3 — WiFi Hotspot Settings"
cat <<'EOF'
The Pi 5 will create a WiFi hotspot that your PicoCalc
connects to in the field. You can use the defaults below
or choose your own name and password.

EOF
ask AP_SSID "Hotspot name (SSID)" "picoBirdPro"
DEFAULT_AP_PASS="$(gen_password)"
echo "A strong random password has been generated. Press Enter to accept it,"
echo "or type your own (minimum 8 characters)."
while true; do
    ask AP_PASS "Hotspot password" "$DEFAULT_AP_PASS"
    if [ "${#AP_PASS}" -ge 8 ]; then
        break
    fi
    echo "  Password must be at least 8 characters."
done
AP_IP="192.168.4.1"

print_header "Step 3 of 3 — Confirm Settings"
cat <<EOF
Ready to install with these settings:

  eBird API key : ${EBIRD_API_KEY:0:6}****** (hidden for security)
  WiFi hotspot  : $AP_SSID
  WiFi password : (set; shown again at the end)
  Pi 5 IP       : $AP_IP

EOF
read -rp "Proceed with installation? [Y/n]: " confirm </dev/tty
confirm="${confirm:-Y}"
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

# ---------------------------------------------------------------------------
echo ""
echo "==> [0/9] Pre-flight checks"
# ---------------------------------------------------------------------------
# Disk space — BirdNET + venv + taxonomy need a few GB.
AVAIL_KB=$(df -Pk /opt 2>/dev/null | awk 'NR==2 {print $4}')
REQUIRED_KB=5000000  # ~5 GB
if [ -n "$AVAIL_KB" ] && [ "$AVAIL_KB" -lt "$REQUIRED_KB" ]; then
    echo "Error: insufficient disk space on /opt."
    echo "  Available: $((AVAIL_KB / 1000)) MB   Required: ~5000 MB"
    echo "  Use a 32 GB+ SD card and re-run."
    exit 1
fi
echo "    Disk space OK ($((AVAIL_KB / 1000)) MB free)."

# WiFi interface — don't assume wlan0.
DETECTED_IF="$(detect_wifi_iface)"
if [ -z "$DETECTED_IF" ]; then
    echo "Error: no WiFi interface found. A WiFi adapter is required for the AP."
    exit 1
fi
WIFI_IF="$DETECTED_IF"
echo "    Using WiFi interface: $WIFI_IF"

# ---------------------------------------------------------------------------
echo ""
echo "==> [1/9] Installing system packages"
echo "    (This may take a few minutes...)"
# ---------------------------------------------------------------------------
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    python3-rpi.gpio python3-spidev \
    hostapd dnsmasq \
    git ffmpeg \
    alsa-utils \
    libopenblas-dev \
    libopenjp2-7 libjpeg-dev libfreetype-dev \
    fonts-dejavu-core
echo "    Done."

# ---------------------------------------------------------------------------
echo ""
echo "==> [2/9] Creating service user"
# ---------------------------------------------------------------------------
id -u "$SERVICE_USER" &>/dev/null || useradd -r -s /sbin/nologin "$SERVICE_USER"
usermod -aG spi,gpio "$SERVICE_USER" 2>/dev/null || true
echo "    Done."

# ---------------------------------------------------------------------------
echo ""
echo "==> [3/9] Setting up project directory"
# ---------------------------------------------------------------------------
mkdir -p "$PROJECT_DIR/setup" "$DATA_DIR"
rsync -a --delete "$REPO_DIR/server/" "$PROJECT_DIR/server/"
rsync -a "$REPO_DIR/setup/preflight.py" "$PROJECT_DIR/setup/preflight.py"
chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR" "$DATA_DIR"
echo "    Done."

# ---------------------------------------------------------------------------
echo ""
echo "==> [4/9] Installing Python dependencies"
echo "    (This may take a few minutes...)"
# ---------------------------------------------------------------------------
if [ ! -f "$PROJECT_DIR/venv/bin/python" ]; then
    python3 -m venv --system-site-packages "$PROJECT_DIR/venv"
fi
"$PROJECT_DIR/venv/bin/pip" install --upgrade pip -q
"$PROJECT_DIR/venv/bin/pip" install \
    flask>=3.0 \
    requests>=2.31 \
    gunicorn>=21.2 \
    Pillow -q
echo "    Done."

# ---------------------------------------------------------------------------
echo ""
echo "==> [5/9] Installing BirdNET-Analyzer"
echo "    (This can take 5-10 minutes on first install...)"
# ---------------------------------------------------------------------------
if [ ! -d /opt/BirdNET-Analyzer ]; then
    git clone --depth 1 https://github.com/kahst/BirdNET-Analyzer /opt/BirdNET-Analyzer
else
    echo "    Already installed, skipping download."
fi
if ! "$PROJECT_DIR/venv/bin/pip" install /opt/BirdNET-Analyzer -q; then
    echo ""
    echo "    Warning: BirdNET-Analyzer failed to install (needed for Sound ID)."
    echo "    Everything else will still work. Retry later with:"
    echo "      $PROJECT_DIR/venv/bin/pip install /opt/BirdNET-Analyzer"
    read -rp "    Continue without Sound ID? [Y/n]: " bn_ok </dev/tty
    bn_ok="${bn_ok:-Y}"
    if [[ ! "$bn_ok" =~ ^[Yy]$ ]]; then
        echo "Installation aborted. Fix BirdNET and re-run."
        exit 1
    fi
fi
echo "    Done."

# ---------------------------------------------------------------------------
echo ""
echo "==> [6/9] Configuring WiFi hotspot"
# ---------------------------------------------------------------------------

# Tell NetworkManager to leave wlan0 alone so hostapd can own it.
# Works regardless of whether NM is installed.
mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/picobird-unmanaged.conf <<EOF
[keyfile]
unmanaged-devices=interface-name:$WIFI_IF
EOF

# Assign the static AP IP via a dedicated systemd service.
# This is more reliable than dhcpcd.conf on modern Pi OS (Debian Bookworm/Trixie)
# which uses NetworkManager instead of dhcpcd.
cat > /etc/systemd/system/picobird-wlan-ip.service <<EOF
[Unit]
Description=Assign static IP to $WIFI_IF for picoBird Pro AP
After=network.target
Before=hostapd.service dnsmasq.service

[Service]
Type=oneshot
ExecStart=/sbin/ip addr replace $AP_IP/24 dev $WIFI_IF
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# Also write dhcpcd.conf entry for systems that still use dhcpcd
if [ -f /etc/dhcpcd.conf ] && ! grep -q "interface $WIFI_IF" /etc/dhcpcd.conf; then
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
wpa_pairwise=CCMP
rsn_pairwise=CCMP
EOF
# Contains the WiFi passphrase — keep it root-only.
chown root:root /etc/hostapd/hostapd.conf
chmod 600 /etc/hostapd/hostapd.conf
sed -i 's|#DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

# Back up an existing dnsmasq.conf only the first time (idempotent re-runs).
if [ -f /etc/dnsmasq.conf ] && [ ! -f /etc/dnsmasq.conf.bak ]; then
    mv /etc/dnsmasq.conf /etc/dnsmasq.conf.bak
fi
cat > /etc/dnsmasq.conf <<EOF
interface=$WIFI_IF
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
EOF

if ! grep -q "^dtparam=spi=on" /boot/firmware/config.txt 2>/dev/null; then
    echo "dtparam=spi=on" >> /boot/firmware/config.txt
fi
echo "    Done."

# ---------------------------------------------------------------------------
echo ""
echo "==> [7/9] Enabling hotspot services"
# ---------------------------------------------------------------------------
systemctl unmask hostapd 2>/dev/null || true
systemctl daemon-reload
systemctl enable picobird-wlan-ip hostapd dnsmasq
# Reload NM so it picks up the unmanaged config immediately
systemctl reload NetworkManager 2>/dev/null || true
echo "    Done."

# ---------------------------------------------------------------------------
echo ""
echo "==> [8/9] Installing picoBird Pro services"
# ---------------------------------------------------------------------------
for svc in picobird-pre picobird-pro picobird-vitals picobird-button; do
    cp "$SCRIPT_DIR/${svc}.service" /etc/systemd/system/
    sed -i "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|" \
        /etc/systemd/system/${svc}.service
done

# Write the eBird API key directly into service overrides
# so the user never needs to edit config files manually.
for svc in picobird-pro picobird-pre; do
    mkdir -p /etc/systemd/system/${svc}.service.d
    cat > /etc/systemd/system/${svc}.service.d/override.conf <<EOF
[Service]
Environment=EBIRD_API_KEY=$EBIRD_API_KEY
# Set AUDIO_DEVICE to override auto-detection of the USB mic (e.g. hw:1,0).
# Leave empty to auto-detect the first USB audio capture device.
Environment=AUDIO_DEVICE=
EOF
    # Contains the eBird API key — keep it root-only.
    chown root:root /etc/systemd/system/${svc}.service.d/override.conf
    chmod 600 /etc/systemd/system/${svc}.service.d/override.conf
done

# Create log files with correct ownership (0640: not world-readable —
# access logs contain connected-device IPs).
touch /var/log/picobird-pro-access.log /var/log/picobird-pro-error.log
chown picobird:picobird /var/log/picobird-pro-access.log /var/log/picobird-pro-error.log
chmod 640 /var/log/picobird-pro-access.log /var/log/picobird-pro-error.log

# Log rotation so logs can't fill the SD card over time.
cat > /etc/logrotate.d/picobird-pro <<'EOF'
/var/log/picobird-pro-*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 picobird picobird
}
EOF

systemctl daemon-reload
systemctl enable picobird-pre picobird-pro picobird-vitals picobird-button
echo "    Done."

# ---------------------------------------------------------------------------
echo ""
echo "==> [9/9] Installing admin console"
# ---------------------------------------------------------------------------
cp "$SCRIPT_DIR/picobird-console.sh" /etc/profile.d/picobird-console.sh
chmod +x /etc/profile.d/picobird-console.sh

# Run the admin console as the picobird user via a wrapper, instead of making
# the venv interpreter world-executable.
cat > /usr/local/bin/picobird-console <<EOF
#!/bin/bash
exec sudo -u $SERVICE_USER PYTHONPATH=$PROJECT_DIR $PROJECT_DIR/venv/bin/python -m server.console "\$@"
EOF
chmod 0755 /usr/local/bin/picobird-console

# Scope privileged actions to a dedicated group instead of all users.
groupadd -f picobird-console
SUDOERS_FILE="/etc/sudoers.d/picobird-console"
cat > "$SUDOERS_FILE" <<'EOF'
# Console admins may control picoBird services without a password.
%picobird-console ALL=(root) NOPASSWD: /bin/systemctl restart picobird-pro picobird-vitals picobird-pre
%picobird-console ALL=(root) NOPASSWD: /bin/systemctl stop picobird-pro picobird-vitals picobird-pre
%picobird-console ALL=(root) NOPASSWD: /bin/systemctl start picobird-pro picobird-vitals picobird-pre
# Allow the console wrapper to run the TUI as the service user.
%picobird-console ALL=(picobird) NOPASSWD: /opt/picobird-pro/venv/bin/python -m server.console
EOF
chmod 0440 "$SUDOERS_FILE"

# Add the default login user (uid 1000, if present) to the console group so the
# admin console works out of the box when a monitor/keyboard is attached.
DEFAULT_USER="$(id -un 1000 2>/dev/null || true)"
if [ -n "$DEFAULT_USER" ]; then
    usermod -aG picobird-console "$DEFAULT_USER" 2>/dev/null || true
fi
echo "    Done."

# ---------------------------------------------------------------------------
print_header "Setup Complete!"
cat <<EOF
Your picoBird Pro Pi 5 is ready. Here's what was configured:

  WiFi hotspot  : $AP_SSID
  WiFi password : $AP_PASS
  Pi 5 address  : $AP_IP
  eBird API key : configured

On every boot the Pi 5 will automatically:
  1. Start the '$AP_SSID' WiFi hotspot
  2. Load the bird species database
  3. Start the picoBird Pro API server
  4. Start the e-ink display dashboard

Next step — reboot the Pi 5:

  sudo reboot

After rebooting, the '$AP_SSID' WiFi network will appear
within about 30 seconds.

On your PicoCalc, edit client/config.json to match:
  "ap_ssid":     "$AP_SSID"
  "ap_password": "$AP_PASS"
Then copy the client/ folder to the PicoCalc and power it on.
EOF
