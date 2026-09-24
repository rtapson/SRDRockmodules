# Octopus firmware

Teensy 4.1 firmware for the Octopus 8-relay MIDI switcher. See `../README.md` for the hardware spec (pin map, BOM, wiring).

## Building and flashing

This is a [PlatformIO](https://platformio.org/) project. Neither PlatformIO nor arduino-cli was available in the environment this was written in, so **this has not yet been compiled or flashed to real hardware** — treat it as a first draft to build and bring up.

1. Install PlatformIO (either the [VS Code extension](https://platformio.org/platformio-ide) or the CLI: `pip install platformio` / `pipx install platformio`).
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

## Source layout

| File | Responsibility |
|---|---|
| `src/main.cpp` | `setup()`/`loop()`, wires the pieces together |
| `src/RelayBank.*` | Drives the 8 GPIO -> ULN2803A pins; pin map matches `../README.md` |
| `src/PresetStore.*` | 128-preset table + MIDI channel, persisted in Teensy's emulated EEPROM |
| `src/MidiHandler.*` | Serial1 MIDI (5-pin DIN) via the FortySevenEffects MIDI library; Program Change recalls a preset, Control Change toggles one relay |
| `src/SerialConfig.*` | USB-serial text protocol to edit presets/channel live |

## MIDI behavior

- **Program Change 0-127** -> recalls preset N -> sets all 8 relays at once from its stored pattern.
- **Control Change 20-27** -> toggles relay 1-8 individually (value >= 64 = on).
- MIDI channel is omni by default; set a fixed channel with the `CH=` config command below.

All presets default to `00000000` (everything off) until configured.

## Serial config console

Connect at 115200 baud over USB and type commands, one per line:

```
HELP              show command list
DUMP              list all non-empty presets and the current MIDI channel
P12=00110101      set preset 12's pattern (char i = relay i+1, so this turns on relays 3 and 4)
CH=3              pin the MIDI channel to 3 (0 = omni)
```

Changes take effect immediately and are persisted to EEPROM, so presets survive power cycles and re-flashing.

## Known gaps / next steps

- Not yet compiled — first `pio run` may surface library-version issues to fix.
- No bounds/hardware-in-the-loop testing yet (no board built).
- USB-MIDI input was not requested for v1 (5-pin DIN only) — could be added alongside Serial1 MIDI later if wanted, since Teensy supports both simultaneously.
