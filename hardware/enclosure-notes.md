# Pi 5 + E-ink Enclosure — Hardware Reference

This file has the exact PCB and module dimensions you need before opening
your CAD tool. All measurements in **millimetres** unless noted.

---

## Raspberry Pi 5

| Dimension | Value |
|---|---|
| PCB size | 85 × 56 mm |
| PCB thickness | 1.5 mm |
| Mounting holes | M2.5, 3.5 mm from each corner (58 × 49 mm hole-to-hole) |
| Tallest component (USB-C port) | ~7 mm above PCB |
| USB-A ports protrude | ~15 mm beyond PCB edge |
| USB-C power | short edge (left) |
| GPIO header | 2×20 pin, 5 mm tall, along long edge |
| Active cooler (official) | 38 × 38 × 30 mm footprint over CPU |

**Minimum internal clearance needed:** ~85 × 56 × 40 mm (with active cooler)

---

## Waveshare 2.9" V2 E-ink Display

| Dimension | Value |
|---|---|
| Active area | 66.9 × 29.06 mm |
| Module PCB | 89 × 37.32 mm |
| Thickness (module only) | ~1.2 mm |
| Mounting holes | M2, 3 mm from corners |
| FPC cable length | ~100 mm |
| Driver board (HAT adapter) | 65 × 30.2 mm |
| Resolution | 296 × 128 px |
| Interface | SPI (see wiring table below) |

### GPIO wiring (BCM numbers)

| E-ink pin | Pi 5 GPIO | Physical pin |
|---|---|---|
| VCC | 3.3 V | Pin 1 |
| GND | GND | Pin 6 |
| DIN (MOSI) | GPIO 10 | Pin 19 |
| CLK (SCLK) | GPIO 11 | Pin 23 |
| CS | GPIO 8 | Pin 24 |
| DC | GPIO 25 | Pin 22 |
| RST | GPIO 17 | Pin 11 |
| BUSY | GPIO 24 | Pin 18 |

---

## Suggested enclosure layout

```
  Top view (not to scale)

  ┌──────────────────────────────────────────────────┐
  │                                                │
  │  ┌──────────────────────────┐  E-INK WINDOW  │
  │  │    Raspberry Pi 5         │  [296 × 128px] │
  │  │    85 × 56 mm             │  ┌─────────┐   │
  │  │                           │  │ 67×29 mm│   │
  │  │    [cooler on top]         │  └─────────┘   │
  │  └──────────────────────────┘                │
  │                                                │
  └──────────────────────────────────────────────────┘

  Side view:

  ┌ top lid (3 mm wall) ──────────────────────────┐
  ├──────────────────────────────────────────────────┤  <- cooler fan vent (louvre)
  │  Pi 5 PCB + cooler  ~40 mm                    │
  │  standoffs 5 mm from base                     │
  └ base (3 mm wall) ───────────────────────────┘
```

### Recommended overall enclosure size

| Axis | Value | Reason |
|---|---|---|
| Width | 160 mm | Pi 85 + e-ink PCB 89 + 3 mm gap + walls |
| Depth | 70 mm  | Pi 56 + walls + port clearance |
| Height | 55 mm  | Pi + cooler 40 + standoffs 5 + walls 6 |

If you route the USB-A and USB-C ports to the outside (recommended for charging
in the field), add a 20 mm deep port alcove on the left short edge.

---

## Port cutouts

| Port | Cutout size | Location |
|---|---|---|
| USB-C power | 10 × 5 mm | Left short edge |
| USB-A × 2 | 15 × 7 mm each | Left short edge |
| microSD | 15 × 3 mm | Right short edge |
| USB 3.0 × 2 | 15 × 7 mm each | Left short edge |
| 3.5 mm audio | 7 mm Ø circle | Right short edge |
| Fan exhaust | 38 × 10 mm louvre | Top |

---

## Power in the field

The Pi 5 needs **5 V / 5 A** (25 W) at the USB-C port. Options:

| Option | Capacity | Runtime est. |
|---|---|---|
| Anker 737 (24 000 mAh / 140 W) | 24 Ah @ 5 V = 120 Wh | ~4.5 h |
| Anker 733 (10 000 mAh / 65 W)  | 10 Ah @ 5 V = 50 Wh  | ~2 h |
| PD-capable USB-C powerbank (any) | depends | depends |

Choose a powerbank that supports USB-C PD output at 5 V / 5 A or 9 V / 3 A
(Pi 5 uses PD negotiation).

If mounting the powerbank inside the enclosure, budget an extra
20–30 mm of depth or a separate lower compartment.

---

## CAD starting points

| Tool | Notes |
|---|---|
| **Onshape** (free, browser) | Good beginner choice; parametric; exports STL |
| **FreeCAD** (free, desktop) | Open-source; steeper learning curve |
| **Fusion 360** (free for hobbyists) | Most polish; great for organic shapes |

### Workflow tips

1. Start with a Pi 5 STEP file — search “Raspberry Pi 5 STEP” on GrabCAD or
   the official Raspberry Pi hardware repo (`raspberrypi/documentation`).
2. Import the STEP as a reference body; build walls around it.
3. Cut port holes as sketched rectangles extruded through the wall face.
4. Add M2.5 boss inserts (4 mm OD, 3.5 mm tall) aligned to the Pi mounting holes.
5. For the e-ink window, leave a 1.5 mm lip on the inside for the module to
   rest against, and a thin (0.8 mm) clear PETG or acrylic window glued over it.
6. Print in PETG (better heat tolerance than PLA for a backpack in summer).
7. Infill: 30 %, 3 perimeters, 0.2 mm layer height.
