# Octopus firmware

Teensy 4.1 firmware for the Octopus 16-line MIDI relay switcher. See `../README.md` for the hardware spec (pin map, BOM, wiring).

## Building and flashing

This is a [PlatformIO](https://platformio.org/) project. It compiles cleanly for `teensy41` but has **not been flashed to real hardware yet**.

1. PlatformIO is installed as a Python package (`pip install platformio`, or the [VS Code extension](https://platformio.org/platformio-ide)).
2. From this `firmware/` directory:
   ```bash
   pio run -e teensy41
   ```
3. To flash over USB (Teensy 4.1 plugged in):
   ```bash
   pio run -e teensy41 -t upload
   ```
   PlatformIO drives the Teensy Loader CLI automatically; you may need to tap the Teensy's reset button if it doesn't auto-reboot into the bootloader.
4. Serial monitor (for the config console below):
   ```bash
   pio device monitor -b 115200
   ```

## Lines

There are 16 independently switched lines, two per output jack:

| Lines | Jack contact | Teensy pins | Driver |
|---|---|---|---|
| 1-8 | jack 1-8 **tip** | 2-9 | ULN2803A U3 |
| 9-16 | jack 1-8 **ring** | 24-31 | ULN2803A U5 |

Each jack's sleeve is the common for both of its lines. Each line is a relay closing to NO or NC, set by that line's solder jumper on the board.

## Source layout

| File | Responsibility |
|---|---|
| `src/main.cpp` | `setup()`/`loop()`, wires the pieces together |
| `src/RelayBank.*` | Drives the 16 driver GPIOs; pin map matches `../README.md` |
| `src/PresetStore.*` | 128-preset table (16-bit pattern each) + MIDI channel, persisted in Teensy's emulated EEPROM |
| `src/MidiHandler.*` | Serial1 MIDI (5-pin DIN) via the FortySevenEffects MIDI library; Program Change recalls a preset, Control Change switches one line |
| `src/SerialConfig.*` | USB-serial text protocol to edit presets/channel live |
| `src/Panel.*` | Button panel over I2C0 (pins 18/19, INT on 22): PCA9685 x2 for the RGB LEDs, MCP23008 for the buttons |

## Button panel

The optional front-panel board has one RGB button per jack (see `../README.md`, "Button panel"):

- The LEDs mirror the relays: off = both lines off, red = tip, green = ring, blue = both.
- A short press (acts on release) steps that jack: off → red → green → blue → off.
- Holding a button 2 s saves all 16 lines into the last preset recalled by Program Change (0 until one arrives). All LEDs flash white and the console prints `panel: saved preset N`.
- At start-up the firmware probes the panel's three I2C chips. If any is missing it prints `button panel not found on I2C; running without it` and carries on, so the main board works standalone.

## MIDI behavior

- **Program Change 0-127** -> recalls preset N -> sets all 16 lines at once from its stored pattern.
- **Control Change 102-117** -> switches line 1-16 individually (value >= 64 = on). 102-119 are left undefined by the MIDI spec. A range like 20-35 would include CC 32 (Bank Select LSB), which many controllers send alongside program changes.
- MIDI channel is omni by default; set a fixed channel with the `CH=` config command below.

All presets default to all-off until configured. Presets are stored as 2 bytes each. The EEPROM format marker changed with the move from 8 to 16 lines, so a Teensy that ran the old 8-line firmware starts with blank presets rather than misread ones.

## Serial config console

Connect at 115200 baud over USB and type commands, one per line:

```
HELP                      show command list
DUMP                      list all non-empty presets and the current MIDI channel
P12=00110101 00000001     set preset 12: char i = line i+1. The first 8 are jack 1-8 TIPS,
                          the last 8 are jack 1-8 RINGS. This turns on tips 3, 4, 6, 8 and ring 8
CH=3                      pin the MIDI channel to 3 (0 = omni)
```

Spaces, `-` and `_` are ignored inside the pattern, so the tip/ring groups can be separated for readability. `DUMP` prints patterns the same way (tips, a space, rings).

Changes take effect immediately and are persisted to EEPROM, so presets survive power cycles and re-flashing.

## Known gaps / next steps

- No hardware-in-the-loop testing yet (no board built).
- USB-MIDI input was not requested (5-pin DIN only). It could be added alongside Serial1 MIDI later if wanted, since Teensy supports both simultaneously.
