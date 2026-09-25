"""Writes panel/OctopusPanel.kicad_sch (+ project, lib tables) for the button board.

The button board carries 8 CTS 228C RGB illuminated tactile switches (one per output
jack) and talks to the main board over I2C through a 6-pin JST-XH cable:
    1 +5V (LED anodes)  2 +3V3 (logic)  3 GND  4 SDA  5 SCL  6 INT
  U1 PCA9685 @0x40  LED0-7 = red of buttons 1-8, LED8-15 = green of buttons 1-8
  U2 PCA9685 @0x41  LED0-7 = blue of buttons 1-8 (LED8-15 unused)
  U3 MCP23008 @0x20 GP0-7 = buttons 1-8 (to GND when pressed), INT = any change
Both PCA9685s run from 3.3 V with open-drain outputs (MODE2: INVRT=1, OUTDRV=0 per
the NXP datasheet's "direct LED connection"); the outputs are 5.5 V tolerant, so the
LED anodes sit on +5V, which the 3.0-3.6 V blue LEDs need.
Run: python tools/gen_panel_schematic.py
"""
import json
import pathlib
import shutil
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_panel_parts  # noqa: E402
from schlib import Sheet  # noqa: E402

TOOLS = pathlib.Path(__file__).resolve().parent
PANEL = TOOLS.parent / "panel"
PROJECT = "OctopusPanel"
UUID_NS = "8d7b3c1e-4a2f-4b9e-9c6d-5e0f1a2b3c4d"
SHEET_UUID = str(uuid.uuid5(uuid.UUID(UUID_NS), "sheet"))

# LED current ~8 mA from +5V: red/green Vf ~2.0-2.1 V -> 390R, blue ~3.2 V -> 220R
LED_R = {"R": "390", "G": "390", "B": "220"}

FOOTPRINTS = {
    "OctopusPanel:CTS_228C_RGB": "OctopusPanel:CTS_228CMV_RGB",
    "Driver_LED:PCA9685PW": "Package_SO:TSSOP-28_4.4x9.7mm_P0.65mm",
    "Interface_Expansion:MCP23008-xSO": "Package_SO:SOIC-18W_7.5x11.6mm_P1.27mm",
    "Device:R": "Resistor_SMD:R_0805_2012Metric",
    "Device:C": "Capacitor_SMD:C_0805_2012Metric",
    "Connector_Generic:Conn_01x06": "Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical",
}

CABLE = [("+5V", None), ("+3V3", None), ("GND", None), (None, "SDA"), (None, "SCL"), (None, "PANEL_INT")]


def build():
    s = Sheet(PROJECT, SHEET_UUID, UUID_NS, FOOTPRINTS, paper="A3", title="Octopus button panel",
              comment="8x CTS 228C RGB switch, PCA9685 x2 + MCP23008 on I2C")
    s.custom("OctopusPanel:CTS_228C_RGB", gen_panel_parts.symbol_block("OctopusPanel:CTS_228C_RGB"))
    s.lib("Device.kicad_sym", "R", "Device:R")
    s.lib("Device.kicad_sym", "C", "Device:C")
    s.lib("Driver_LED.kicad_sym", "PCA9685PW", "Driver_LED:PCA9685PW")
    s.lib("Interface_Expansion.kicad_sym", "MCP23008-xSO", "Interface_Expansion:MCP23008-xSO")
    s.lib("Connector_Generic.kicad_sym", "Conn_01x06", "Connector_Generic:Conn_01x06")

    # ---- buttons + LED resistors, one row per button (button n drives jack n)
    for n in range(1, 9):
        y = 30 + (n - 1) * 32
        sw = s.place("OctopusPanel:CTS_228C_RGB", f"SW{n}", "228CMVARGBFDNR", 40, y)   # cap D, Natural
        s.net(sw["1"], f"BTN{n}")
        s.net(sw["2"], f"BTN{n}")
        s.pwr(sw["3"], "GND")
        s.pwr(sw["4"], "GND")
        s.pwr(sw["L3"], "+5V")                 # common anode
        for pin, col in (("L2", "R"), ("L4", "G"), ("L1", "B")):
            s.net(sw[pin], f"LED{n}_{col}")
        for i, col in enumerate("RGB"):
            r = s.place("Device:R", f"R{3 * (n - 1) + i + 1}", LED_R[col], 110 + i * 16, y)
            s.net(r["1"], f"LED{n}_{col}")    # cathode side
            s.net(r["2"], f"DRV{n}_{col}")    # driver output side

    # ---- LED drivers
    for ref, y, colors, addr0 in (("U1", 70, ("R", "G"), "GND"), ("U2", 180, ("B", None), "+3V3")):
        u = s.place("Driver_LED:PCA9685PW", ref, "PCA9685PW", 220, y)
        for ch in range(16):
            col = colors[ch // 8]
            pin = str({0: 6, 1: 7, 2: 8, 3: 9, 4: 10, 5: 11, 6: 12, 7: 13, 8: 15, 9: 16, 10: 17,
                       11: 18, 12: 19, 13: 20, 14: 21, 15: 22}[ch])
            if col:
                s.net(u[pin], f"DRV{ch % 8 + 1}_{col}")
            else:
                s.nc(u[pin])
        s.pwr(u["1"], addr0)                   # A0: U1 = 0x40, U2 = 0x41
        for a in ("2", "3", "4", "5", "24"):   # A1-A5
            s.pwr(u[a], "GND")
        s.pwr(u["23"], "GND")                  # /OE: outputs always enabled
        s.pwr(u["25"], "GND")                  # EXTCLK unused: internal oscillator
        s.net(u["26"], "SCL")
        s.net(u["27"], "SDA")
        s.pwr(u["28"], "+3V3")
        s.pwr(u["14"], "GND")

    # ---- button inputs
    x = s.place("Interface_Expansion:MCP23008-xSO", "U3", "MCP23008-xSO", 320, 70)
    for n in range(1, 9):
        s.net(x[str(9 + n)], f"BTN{n}")       # GP0..GP7 = pins 10..17
    s.net(x["1"], "SCL")
    s.net(x["2"], "SDA")
    for a in ("3", "4", "5"):                  # A2-A0 -> address 0x20
        s.pwr(x[a], "GND")
    s.pwr(x["6"], "+3V3")                      # /RESET held high
    s.net(x["8"], "PANEL_INT")
    s.nc(x["7"])
    s.pwr(x["18"], "+3V3")
    s.pwr(x["9"], "GND")

    # ---- cable to the main board
    j = s.place("Connector_Generic:Conn_01x06", "J1", "To main board J11", 320, 170)
    for i, (power, net) in enumerate(CABLE, 1):
        if power:
            end = s.pwr(j[str(i)], power)
            s.power("PWR_FLAG", *end)          # supplied from the main board over the cable
        else:
            s.net(j[str(i)], net)

    # ---- I2C pull-ups (the only ones on the bus) and decoupling
    for i, net in enumerate(("SDA", "SCL")):
        r = s.place("Device:R", f"R{25 + i}", "4.7k", 360 + i * 14, 170)
        s.pwr(r["1"], "+3V3")
        s.net(r["2"], net)
    caps = [("C1", "100n", "+3V3"), ("C2", "100n", "+3V3"), ("C3", "100n", "+3V3"),
            ("C4", "10u", "+3V3"), ("C5", "10u", "+5V")]
    for i, (ref, val, rail) in enumerate(caps):
        c = s.place("Device:C", ref, val, 220 + i * 16, 250)
        s.pwr(c["1"], rail)
        s.pwr(c["2"], "GND")

    # no mounting holes: the board slides into the groove in the case top/bottom

    s.write(PANEL / f"{PROJECT}.kicad_sch")


def write_project_files():
    main_pro = json.loads((TOOLS.parent / "Octopus.kicad_pro").read_text(encoding="utf-8"))
    pro = json.loads(json.dumps(main_pro))
    pro["meta"]["filename"] = f"{PROJECT}.kicad_pro"
    pro["sheets"] = [[SHEET_UUID, PROJECT]]
    pro["schematic"]["top_level_sheets"] = [{"filename": f"{PROJECT}.kicad_sch", "name": PROJECT, "uuid": SHEET_UUID}]
    default = next(c for c in pro["net_settings"]["classes"] if c["name"] == "Default")
    default.update(track_width=0.25, clearance=0.2)
    power = dict(default, name="Power", track_width=0.5, clearance=0.2, priority=1)
    pro["net_settings"]["classes"] = [default, power]
    pro["net_settings"]["netclass_patterns"] = [{"netclass": "Power", "pattern": p} for p in ("+5V", "+3V3", "GND")]
    path = PANEL / f"{PROJECT}.kicad_pro"
    if not path.exists():   # KiCad owns this file once the project has been opened
        path.write_text(json.dumps(pro, indent=2), encoding="utf-8")
    (PANEL / "fp-lib-table").write_text(
        '(fp_lib_table\n\t(version 7)\n\t(lib (name "OctopusPanel") (type "KiCad") (uri "${KIPRJMOD}/OctopusPanel.pretty") (options "") (descr "Octopus button board parts"))\n)\n',
        encoding="utf-8")
    (PANEL / "sym-lib-table").write_text(
        '(sym_lib_table\n\t(version 7)\n\t(lib (name "OctopusPanel") (type "KiCad") (uri "${KIPRJMOD}/OctopusPanel.kicad_sym") (options "") (descr "Octopus button board parts"))\n)\n',
        encoding="utf-8")
    board = PANEL / f"{PROJECT}.kicad_pcb"
    if not board.exists():
        shutil.copy(TOOLS / "board_template.kicad_pcb", board)


if __name__ == "__main__":
    PANEL.mkdir(exist_ok=True)
    gen_panel_parts.main()
    write_project_files()
    build()
    print("wrote", PANEL / f"{PROJECT}.kicad_sch")
