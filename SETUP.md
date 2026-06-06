# picoBird Pro — Setup Guide

This guide walks you through setting up both devices from scratch.
Expect about **30–45 minutes** for the Pi 5 and **10 minutes** for the PicoCalc.

---

## What you need

### Hardware

| Item | Notes |
|---|---|
| Raspberry Pi 5 (4 GB or 8 GB) | 8 GB recommended for BirdNET |
| microSD card (32 GB+) | Class 10 / A1 or better |
| USB-C power supply (5 V / 5 A) | Official Pi 5 supply or a 27 W+ PD charger |
| Waveshare 2.9" e-ink display V2 | SPI interface, 296×128 px |
| 8 female-to-female jumper wires | For e-ink → Pi GPIO |
| Momentary push button | For the field reset button (any normally-open type) |
| 2 female-to-female jumper wires | Button → Pi GPIO |
| ClockworkPi PicoCalc | With Pico 2 W module fitted |
| Another computer | To flash cards and copy files |

### Accounts / keys

- **eBird API key** — free, get one at https://ebird.org/api/keygen
  (requires a free eBird account)

---

## Part 1 — Raspberry Pi 5

### Step 1 — Flash the SD card

1. Download **Raspberry Pi Imager** from https://www.raspberrypi.com/software/
2. Insert your microSD card
3. In the Imager:
   - **Device:** Raspberry Pi 5
   - **OS:** Raspberry Pi OS Lite (64-bit) — under *Raspberry Pi OS (other)*
   - **Storage:** your microSD card
4. Click the settings gear icon before writing:
   - Set a **hostname** (e.g. `picobird`)
   - Enable **SSH** with password authentication
   - Set a **username and password** (e.g. user `pi`)
   - Leave WiFi blank — we will use the Pi as an AP, not a client
5. Write the card, then insert it into the Pi 5

### Step 2 — First boot and SSH in

Connect the Pi 5 to your router via **Ethernet** for this step
(we need internet access to run the installer).

```bash
# From your computer:
ssh pi@picobird.local
# or use the Pi's ethernet IP if mDNS doesn't work on your network
```

### Step 3 — Clone the repo

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/beltkingfish/picobird-pro /opt/picobird-pro-src
```

### Step 4 — Run the installer

```bash
cd /opt/picobird-pro-src
sudo bash setup/install.sh
```

The installer will:
- Install Python, hostapd, dnsmasq, Pillow, RPi.GPIO, spidev
- Create the `picobird` service user
- Copy the server code to `/opt/picobird-pro`
- Set up the Python virtual environment
- Clone BirdNET-Analyzer to `/opt/BirdNET-Analyzer`
- Configure the `picoBirdPro` WiFi access point
- Enable SPI for the e-ink display
- Install and enable all systemd services
- Install the admin console auto-launch for physical console logins
- Set up passwordless `sudo` for service restart/stop (console only)

> The BirdNET clone can take a few minutes depending on your connection.

### Step 5 — Set your eBird API key

```bash
sudo systemctl edit picobird-pro
```

This opens a blank override file. Add exactly this (replace the key):

```ini
[Service]
Environment=EBIRD_API_KEY=your_key_here
```

Save and close (`Ctrl+O`, `Enter`, `Ctrl+X` in nano).

Repeat for the preflight service so taxonomy sync also has the key:

```bash
sudo systemctl edit picobird-pre
```

Add the same two lines, save.

### Step 6 — Wire up the e-ink display

With the Pi **powered off**, connect the Waveshare 2.9" V2 to the GPIO header
using jumper wires:

| E-ink label | Pi GPIO (BCM) | Physical pin |
|---|---|---|
| VCC | 3.3 V | Pin 1 |
| GND | GND | Pin 6 |
| DIN | GPIO 10 (MOSI) | Pin 19 |
| CLK | GPIO 11 (SCLK) | Pin 23 |
| CS | GPIO 8 (CE0) | Pin 24 |
| DC | GPIO 25 | Pin 22 |
| RST | GPIO 17 | Pin 11 |
| BUSY | GPIO 24 | Pin 18 |

### Step 7 — Wire up the reset button

Still with the Pi **powered off**, connect a momentary push button between
two GPIO pins:

| Button terminal | Pi GPIO (BCM) | Physical pin |
|---|---|---|
| Terminal A | GPIO 26 | Pin 37 |
| Terminal B | GND | Pin 39 |

No resistor needed — the Pi's internal pull-up is enabled by the software.
Mount the button somewhere accessible on your enclosure.

**What the button does:**

| Press type | Action |
|---|---|
| Short press (< 3 s) | Restarts the three picoBird services |
| Long press (≥ 3 s) | Full system reboot |

While restarting, the e-ink display shows "Restarting... Please wait"
and then refreshes with the live dashboard once everything is back up.

### Step 8 — First reboot

Disconnect Ethernet, then reboot:

```bash
sudo reboot
```

After ~30 seconds:
- The `picoBirdPro` WiFi network will appear
- The e-ink display will show the vitals dashboard
- The API server will be running on `192.168.4.1:5000`
- The reset button will be active

On **first boot only**, the preflight service will download the full eBird
taxonomy (~16,000 species) into the local database. This takes about 20 seconds
and only happens once.

### Step 9 — Verify the server is running

Connect your phone or laptop to the `picoBirdPro` WiFi (password: `fieldguide`),
then open a browser or run:

```bash
curl http://192.168.4.1:5000/api/ping
# Expected: {"status": "ok", "app": "picoBird Pro"}

curl http://192.168.4.1:5000/api/lifelist/stats
# Expected: {"total_species": 0, "by_family": []}
```

If you see those responses, the Pi 5 is fully set up.

---

## Part 2 — PicoCalc

### Step 10 — Flash MicroPython onto the Pico 2 W

1. Download the latest **MicroPython for Pico 2 W** UF2 file from
   https://micropython.org/download/RPI_PICO2_W/
2. Hold the **BOOTSEL** button on the Pico 2 W while plugging it into your
   computer via USB
3. It will appear as a USB drive called `RPI-RP2`
4. Drag the UF2 file onto that drive
5. The Pico will reboot automatically into MicroPython

### Step 11 — Install mpremote

On your computer:

```bash
pip install mpremote
```

Verify the PicoCalc is detected:

```bash
mpremote connect list
# Should show something like: /dev/ttyACM0  (Linux/Mac) or COM3 (Windows)
```

### Step 12 — Copy client files to the PicoCalc

From the root of this repo:

```bash
mpremote connect /dev/ttyACM0 cp -r client/. :
```

Replace `/dev/ttyACM0` with your port from Step 11.

This copies everything in `client/` — `main.py`, `lib/`, and `app/` —
to the root of the Pico's filesystem.

### Step 13 — Verify the pin constants

Open `client/main.py` and check the hardware constants at the top of the file
match your PicoCalc's wiring:

```python
SPI_ID   = 0
SPI_SCK  = 2
SPI_MOSI = 3
SPI_MISO = 4
DISP_CS  = 5
DISP_DC  = 6
DISP_RST = 7
DISP_BL  = 8

KBD_I2C  = 0
KBD_SDA  = 20
KBD_SCL  = 21
```

These match the standard PicoCalc schematic. If your board differs, edit
the values before copying the file.

### Step 14 — Boot the PicoCalc

Power cycle the PicoCalc (or press its reset button). With the Pi 5 already
running, the PicoCalc will:

1. Show the picoBird Pro splash screen
2. Scan for the `picoBirdPro` WiFi network
3. Connect and display the assigned IP address
4. Confirm the server is reachable
5. Launch the main menu

If it can't find the Pi 5, it will say so on screen and tell you to press
RESET to try again.

---

## Using the app

### PicoCalc navigation

| Key | Action |
|---|---|
| Arrow keys | Move between menu items / results |
| Enter | Select / confirm |
| Esc | Go back |
| Type letters | Search (on search screens) |
| Backspace | Delete last character |

### Pi 5 admin console

When a keyboard and monitor are plugged into the Pi 5 and you log in,
the admin console launches automatically:

```
 picoBird Pro — Admin Console                               14:32:01

 IP: 192.168.4.1   up 3h 22m   CPU 44°C   RAM 38%
 ──────────────────────────────────────────────────
 Services
   ● API Server         running
   ● E-ink Display      running
   ● Preflight          running
   ● Reset Button       running
   ● WiFi AP            running (2 clients)
 ──────────────────────────────────────────────────
 Birding
   Server ●   BirdNET ●
   Lifers 247   Obs today 12
   Last: American Robin  14:28
 ──────────────────────────────────────────────────
 [R] Restart   [S] Stop   [T] Sync   [L] Logs   [Q] Exit
```

| Key | Action |
|---|---|
| Q | Exit console — drops to normal bash shell |
| R | Restart all picoBird services |
| S | Stop all picoBird services |
| T | Trigger an eBird taxonomy sync |
| L | Show last 20 lines of the server log |

The console **only** auto-launches on a physical login (keyboard + HDMI).
SSH sessions see a normal bash prompt, unchanged.

To reopen the console from bash:
```bash
picobird-console
```

### Field reset button

| Press type | What happens |
|---|---|
| Short press (< 3 s) | Services restart; e-ink shows "Restarting..." then refreshes |
| Long press (≥ 3 s) | Full system reboot |

---

## Troubleshooting

### Pi 5 — checking service status

```bash
# SSH in, then:
sudo systemctl status picobird-pre
sudo systemctl status picobird-pro
sudo systemctl status picobird-vitals
sudo systemctl status picobird-button

# View live logs:
sudo journalctl -fu picobird-pro
```

### Pi 5 — WiFi AP not appearing

```bash
sudo systemctl status hostapd
sudo journalctl -u hostapd
```

If hostapd is masked:
```bash
sudo systemctl unmask hostapd
sudo systemctl start hostapd
```

### Pi 5 — manually trigger a taxonomy sync

```bash
curl -X POST http://192.168.4.1:5000/api/species/sync
# Returns: {"synced": 16xxx}
```

### Pi 5 — e-ink display not updating

- Check SPI is enabled: `ls /dev/spidev*` should show `/dev/spidev0.0`
- If missing: `sudo raspi-config` → Interface Options → SPI → Enable, reboot
- Check wiring against Step 6
- Check the vitals service: `sudo systemctl status picobird-vitals`

### Pi 5 — reset button not responding

- Check wiring: one leg to GPIO 26 (physical pin 37), other to GND (pin 39)
- Check the button service: `sudo systemctl status picobird-button`
- Test the GPIO manually:
  ```bash
  python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP); print(GPIO.input(26))"
  # Should print 1 (high). Press button — should print 0 if wired correctly.
  ```

### Pi 5 — admin console not launching on login

- Verify HDMI is connected before the Pi boots
- Check the profile script: `cat /etc/profile.d/picobird-console.sh`
- Try launching manually: `picobird-console`
- If permission error: `sudo chmod o+x /opt/picobird-pro/venv/bin/python`

### PicoCalc — stuck on "Scanning..."

- Make sure the Pi 5 is fully booted first (e-ink display should show the dashboard)
- The PicoCalc scans 8 times with backoff before giving up (~30 seconds total)
- Press RESET on the PicoCalc to try again

### PicoCalc — copying files fails

```bash
# Try specifying the port explicitly:
mpremote connect /dev/ttyACM0 ls

# If permission denied on Linux:
sudo usermod -aG dialout $USER
# then log out and back in
```

### Two PicoCalcs at once

Both devices can connect and log simultaneously — the server handles concurrent
requests and SQLite WAL mode queues any simultaneous writes safely.

Note: observations, sessions, and the life list are **shared** between all
connected devices.

---

## WiFi credentials

| Setting | Default |
|---|---|
| Network name (SSID) | `picoBirdPro` |
| Password | `fieldguide` |
| Pi 5 IP address | `192.168.4.1` |
| Server port | `5000` |

To change these, edit `setup/install.sh` (AP side) and `client/main.py`
(PicoCalc side), then re-run the installer and re-copy the client files.

---

## Updating

### Pi 5

```bash
cd /opt/picobird-pro-src
git pull
sudo bash setup/install.sh
sudo systemctl restart picobird-pro picobird-vitals picobird-button
```

### PicoCalc

```bash
cd /path/to/picobird-pro
git pull
mpremote connect /dev/ttyACM0 cp -r client/. :
```
