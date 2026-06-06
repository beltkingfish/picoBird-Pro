# picoBird Pro

A two-device birding field guide:

| Device | Role |
|---|---|
| **Raspberry Pi 5** (8 GB) | Backend server: SQLite, eBird API, BirdNET sound ID, WiFi AP |
| **ClockworkPi PicoCalc** (Pico 2 W + ILI9488 320×320) | Client terminal: display + keyboard, talks to Pi 5 over WiFi |

---

## Architecture

```
PicoCalc  ───[WiFi 192.168.4.x]───>  Pi 5 AP (192.168.4.1:5000)
  MicroPython client                     Flask / SQLite / BirdNET
  - species search (paginated)           - eBird taxonomy cache
  - log observations                     - life list (auto-updated)
  - browse life list                     - session management
  - sound ID (I2S mic optional)          - BirdNET-Analyzer inference
```

---

## Repository layout

```
picoBirdPro/
├── server/                   # Pi 5 — Python / Flask
│   ├── main.py               # App factory, blueprint registration
│   ├── database.py           # SQLite schema + query helpers
│   ├── ebird_api.py          # eBird API v2 client (cached)
│   ├── birdnet.py            # BirdNET-Analyzer subprocess wrapper
│   └── api/
│       ├── species.py         # Search, sync taxonomy, nearby
│       ├── observations.py    # CRUD for logged birds
│       ├── sessions.py        # Birding session management
│       ├── lifelist.py        # Life list + stats
│       └── sound.py           # WAV upload → BirdNET detections
├── client/                   # PicoCalc — MicroPython
│   ├── main.py               # Boot: connect WiFi, launch UI
│   ├── lib/
│   │   ├── ili9488.py        # ILI9488 SPI display driver
│   │   ├── keyboard.py       # STM32 I2C keyboard driver
│   │   ├── sdcard.py         # SD card SPI driver
│   │   └── http_client.py    # Minimal HTTP client (no urequests needed)
│   └── app/
│       ├── screen.py          # Display helper, colour palette, text utils
│       ├── ui.py              # Screen-stack UI manager
│       └── screens/
│           ├── home.py         # Main menu
│           ├── search.py       # Species search (paginated)
│           ├── species_detail.py # Detail view + quick-log
│           ├── observe.py      # Quick-log observation
│           ├── lifelist.py     # Life list browser
│           ├── sessions.py     # Session management
│           └── sound.py        # Sound ID (I2S mic → BirdNET)
└── setup/
    ├── install.sh              # Pi 5 setup (hostapd, dnsmasq, venv, BirdNET)
    └── picobird-pro.service    # systemd unit
```

---

## Pi 5 Setup

### 1. Flash & SSH in

Flash Raspberry Pi OS Lite (64-bit) to an SD card. Boot, SSH in.

### 2. Clone the repo

```bash
git clone https://github.com/beltkingfish/picobird-pro /opt/picobird-pro-src
```

### 3. Run the installer

```bash
cd /opt/picobird-pro-src
sudo bash setup/install.sh
```

This will:
- Install `hostapd` + `dnsmasq` and configure the `wlan0` AP (`picoBirdPro` / `fieldguide`)
- Clone BirdNET-Analyzer to `/opt/BirdNET-Analyzer`
- Create a Python venv with Flask + Gunicorn
- Install and enable the `picobird-pro` systemd service

### 4. Set your eBird API key

```bash
sudo systemctl edit picobird-pro
```

Add:
```ini
[Service]
Environment=EBIRD_API_KEY=your_key_here
```

### 5. Start the server

```bash
sudo systemctl start picobird-pro
sudo systemctl status picobird-pro
```

### 6. Sync the eBird taxonomy

```bash
curl -X POST http://localhost:5000/api/species/sync
```

This loads ~16,000 species into the local SQLite FTS index. Takes ~20 s on first run.

---

## PicoCalc Setup

### 1. Flash MicroPython

Flash the latest [MicroPython for Pico 2 W](https://micropython.org/download/RPI_PICO2_W/) to the PicoCalc.

### 2. Copy client files

Copy the entire `client/` directory to the root of the Pico using [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html) or Thonny:

```bash
mpremote connect /dev/ttyACM0 cp -r client/. :
```

### 3. Verify wiring

Check `client/main.py` pin constants match your PicoCalc:

| Constant | Default | Notes |
|---|---|---|
| `SPI_ID` | 0 | SPI bus for display |
| `DISP_CS/DC/RST/BL` | 5/6/7/8 | ILI9488 chip-select, D/C, reset, backlight |
| `KBD_SDA/SCL` | 20/21 | I2C to STM32 keyboard |

### 4. Boot

Power cycle the PicoCalc. It will:
1. Init the display
2. Connect to the `picoBirdPro` AP
3. Launch the main menu

---

## API Reference (Pi 5)

| Method | Path | Description |
|---|---|---|
| GET | `/api/ping` | Health check |
| GET | `/api/species/search?q=robin&page=0` | FTS species search |
| GET | `/api/species/<code>` | Species detail |
| POST | `/api/species/sync` | Sync full eBird taxonomy |
| GET | `/api/species/nearby?lat=&lng=&dist=25` | Nearby species from eBird |
| GET | `/api/observations/` | List observations |
| POST | `/api/observations/` | Log an observation |
| PATCH | `/api/observations/<id>` | Update observation |
| DELETE | `/api/observations/<id>` | Delete observation |
| GET | `/api/sessions/` | List sessions |
| POST | `/api/sessions/` | Start a session |
| PATCH | `/api/sessions/<id>/end` | End a session |
| GET | `/api/sessions/<id>/summary` | Session summary |
| GET | `/api/lifelist/` | Life list (paginated) |
| GET | `/api/lifelist/check/<code>` | Lifer check |
| GET | `/api/lifelist/stats` | Life list stats |
| POST | `/api/sound/identify` | WAV → BirdNET detections |

---

## Sound ID

The PicoCalc Sound ID screen requires an I2S microphone (e.g. INMP441) wired to:
- SCK → GP10, WS → GP11, SD → GP12

Without a mic the screen shows a friendly error; all other features still work.

The Pi 5 runs BirdNET-Analyzer as a subprocess. Results are returned ranked by confidence.

---

## WiFi credentials

| Setting | Default |
|---|---|
| SSID | `picoBirdPro` |
| Password | `fieldguide` |
| Pi 5 IP | `192.168.4.1` |
| Server port | `5000` |

Change in `setup/install.sh` (AP side) and `client/main.py` (PicoCalc side).

---

## License

MIT
