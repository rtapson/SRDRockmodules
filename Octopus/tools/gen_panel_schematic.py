"""Writes panel/OctopusPanel.kicad_sch (+ project, lib tables) for the button board.

The button board carries 8 Omron B3W-9 two-LED (red + green) illuminated tactile switches,
one per output jack, the preset display and the encoder, and talks to the main board over
I2C through a 6-pin JST-XH cable:
    1 +5V (LED anodes)  2 +3V3 (logic)  3 GND  4 SDA  5 SCL  6 INT
  U1 PCA9685 @0x40  LED0-7 = red of buttons 1-8, LED8-15 = green of buttons 1-8
  U3 MCP23017 @0x20 GPA0-6 + GPB0 = buttons 1-8, GPB1-3 = encoder A/B/push (all to GND
     when active), INTA (mirrored) = any change. GPA7/GPB7 are unused: Microchip's current
     datasheet makes them output-only.
  J2 Winstar WEA012864D-03 0.96" 128x64 SSD1306 OLED @0x3C, from +3V3
  SW9 Alps EC11E rotary encoder with push switch (10k pull-up + 10n per line)
The PCA9685 runs from 3.3 V with open-drain outputs (MODE2: INVRT=1, OUTDRV=0 per the
NXP datasheet's "direct LED connection"); the outputs are 5.5 V tolerant, so the LED
anodes sit on +5V. (There is no U2 any more: it drove the blue LEDs of the earlier CTS
RGB switches.)
Run: python tools/gen_panel_schematic.py
"""
import json
import pathlib
import shutil
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_panel_parts  # noqa: E402
import guard  # noqa: E402  (refuses to overwrite hand-edited files)
from schlib import Sheet  # noqa: E402

TOOLS = pathlib.Path(__file__).resolve().parent
PANEL = TOOLS.parent / "panel"
PROJECT = "OctopusPanel"
UUID_NS = "8d7b3c1e-4a2f-4b9e-9c6d-5e0f1a2b3c4d"
SHEET_UUID = str(uuid.uuid5(uuid.UUID(UUID_NS), "sheet"))

# LED currents from +5V, in Omron's recommended 12:20 red:green ratio for a clean amber,
# scaled down to keep the 5 V budget in hand: red Vf 1.8 V -> 330R ~9.7 mA,
# green Vf 2.1 V -> 180R ~16 mA. They're 4-resistor isolated arrays (Bourns CAT16-xxxJ4):
# RN1/RN2 = red of buttons 1-4 / 5-8, RN3/RN4 = green of buttons 1-4 / 5-8.
LED_R = {"R": "330", "G": "180"}
LED_RN = {("R", 0): "RN1", ("R", 1): "RN2", ("G", 0): "RN3", ("G", 1): "RN4"}

FOOTPRINTS = {
    "OctopusPanel:B3W-9_RG": "OctopusPanel:Omron_B3W-9_2LED_10x10",
    "Driver_LED:PCA9685PW": "Package_SO:TSSOP-28_4.4x9.7mm_P0.65mm",
    "Interface_Expansion:MCP23017x-x-SO": "Package_SO:SOIC-28W_7.5x17.9mm_P1.27mm",
    "Device:RotaryEncoder_Switch": "Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm",
    "Connector_Generic:Conn_01x04": "OctopusPanel:OLED_Winstar_WEA012864D-03",
    "Device:R": "Resistor_SMD:R_0805_2012Metric",
    "Device:R_Pack04": "Resistor_SMD:R_Array_Convex_4x0603",
    "Device:C": "Capacitor_SMD:C_0805_2012Metric",
    "Connector_Generic:Conn_01x06": "Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical",
}

CABLE = [("+5V", None), ("+3V3", None), ("GND", None), (None, "SDA"), (None, "SCL"), (None, "PANEL_INT")]


def build():
    s = Sheet(PROJECT, SHEET_UUID, UUID_NS, FOOTPRINTS, paper="A3", title="Octopus button panel",
              comment="8x Omron B3W-9 red/green switch, PCA9685 + MCP23017, OLED, encoder on I2C")
    s.custom("OctopusPanel:B3W-9_RG", gen_panel_parts.symbol_block("OctopusPanel:B3W-9_RG"))
    s.lib("Device.kicad_sym", "R", "Device:R")
    s.lib("Device.kicad_sym", "R_Pack04", "Device:R_Pack04")
    s.lib("Device.kicad_sym", "C", "Device:C")
    s.lib("Driver_LED.kicad_sym", "PCA9685PW", "Driver_LED:PCA9685PW")
    s.lib("Interface_Expansion.kicad_sym", "MCP23017x-x-SO", "Interface_Expansion:MCP23017x-x-SO")
    s.lib("Device.kicad_sym", "RotaryEncoder_Switch", "Device:RotaryEncoder_Switch")
    s.lib("Connector_Generic.kicad_sym", "Conn_01x04", "Connector_Generic:Conn_01x04")
    s.lib("Connector_Generic.kicad_sym", "Conn_01x06", "Connector_Generic:Conn_01x06")

    # ---- buttons, one row per button (button n drives jack n)
    for n in range(1, 9):
        y = 30 + (n - 1) * 32
        sw = s.place("OctopusPanel:B3W-9_RG", f"SW{n}", "B3W-9000-RG2N", 40, y)
        s.net(sw["1"], f"BTN{n}")
        s.net(sw["2"], f"BTN{n}")
        s.pwr(sw["3"], "GND")
        s.pwr(sw["4"], "GND")
        s.pwr(sw["A1"], "+5V")                 # red anode
        s.pwr(sw["A2"], "+5V")                 # green anode
        s.net(sw["K1"], f"LED{n}_R")
        s.net(sw["K2"], f"LED{n}_G")

    # ---- LED resistor arrays: element k (pins k / 9-k) serves the k-th button of its four
    for (col, half), ref in LED_RN.items():
        rn = s.place("Device:R_Pack04", ref, LED_R[col], 110 + (col == "G") * 40, 60 + half * 110)
        for k in range(1, 5):
            n = 4 * half + k
            s.net(rn[str(k)], f"LED{n}_{col}")          # cathode side
            s.net(rn[str(9 - k)], f"DRV{n}_{col}")      # driver output side

    # ---- LED driver
    u = s.place("Driver_LED:PCA9685PW", "U1", "PCA9685PW", 220, 70)
    for ch in range(16):
        pin = str({0: 6, 1: 7, 2: 8, 3: 9, 4: 10, 5: 11, 6: 12, 7: 13, 8: 15, 9: 16, 10: 17,
                   11: 18, 12: 19, 13: 20, 14: 21, 15: 22}[ch])
        s.net(u[pin], f"DRV{ch % 8 + 1}_{'RG'[ch // 8]}")
    for a in ("1", "2", "3", "4", "5", "24"):  # A0-A5 -> address 0x40
        s.pwr(u[a], "GND")
    s.pwr(u["23"], "GND")                      # /OE: outputs always enabled
    s.pwr(u["25"], "GND")                      # EXTCLK unused: internal oscillator
    s.net(u["26"], "SCL")
    s.net(u["27"], "SDA")
    s.pwr(u["28"], "+3V3")
    s.pwr(u["14"], "GND")

    # ---- button + encoder inputs (MCP23017; GPA7/GPB7 unused, see the docstring)
    x = s.place("Interface_Expansion:MCP23017x-x-SO", "U3", "MCP23017", 320, 80)
    inputs = {"21": "BTN1", "22": "BTN2", "23": "BTN3", "24": "BTN4", "25": "BTN5", "26": "BTN6",
              "27": "BTN7", "1": "BTN8", "2": "ENC_A", "3": "ENC_B", "4": "ENC_SW"}
    for pin, net in inputs.items():
        s.net(x[pin], net)
    for pin in ("28", "5", "6", "7", "8", "19", "11", "14"):   # GPA7, GPB4-7, INTB, NC, NC
        s.nc(x[pin])
    s.net(x["12"], "SCL")
    s.net(x["13"], "SDA")
    for a in ("15", "16", "17"):               # A0-A2 -> address 0x20
        s.pwr(x[a], "GND")
    s.pwr(x["18"], "+3V3")                     # /RESET held high
    s.net(x["20"], "PANEL_INT")                # INTA, mirrored to cover both ports
    s.pwr(x["9"], "+3V3")
    s.pwr(x["10"], "GND")

    # ---- OLED module (I2C 0x3C; the bus pull-ups are R25/R26)
    d = s.place("Connector_Generic:Conn_01x04", "J2", "WEA012864D-03 OLED", 390, 60)
    s.pwr(d["1"], "+3V3")                      # VCC (2.8-5.2 V; 12 mA typ)
    s.pwr(d["2"], "GND")
    s.net(d["3"], "SCL")
    s.net(d["4"], "SDA")

    # ---- rotary encoder with push switch; RC per line: 10k pull-up to 3V3, 10n to GND
    e = s.place("Device:RotaryEncoder_Switch", "SW9", "EC11E15204A3", 330, 240)
    s.net(e["A"], "ENC_A")
    s.net(e["B"], "ENC_B")
    s.pwr(e["C"], "GND")
    s.net(e["S1"], "ENC_SW")
    s.pwr(e["S2"], "GND")
    for i, net in enumerate(("ENC_A", "ENC_B", "ENC_SW")):
        r = s.place("Device:R", f"R{3 + i}", "10k", 365 + i * 16, 222)
        s.pwr(r["1"], "+3V3")
        s.net(r["2"], net)
        c = s.place("Device:C", f"C{5 + i}", "10n", 365 + i * 16, 262)
        s.net(c["1"], net)
        s.pwr(c["2"], "GND")

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
        r = s.place("Device:R", f"R{1 + i}", "4.7k", 360 + i * 14, 170)
        s.pwr(r["1"], "+3V3")
        s.net(r["2"], net)
    caps = [("C1", "100n", "+3V3"), ("C2", "100n", "+3V3"),        # U1, U3
            ("C3", "10u", "+3V3"), ("C4", "10u", "+5V")]
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
        guard.record(board)            # a fresh empty board: gen_panel_pcb.py may fill it


OUTPUTS = [PANEL / f"{PROJECT}.kicad_sch", PANEL / "fp-lib-table", PANEL / "sym-lib-table"]

if __name__ == "__main__":
    guard.check(*OUTPUTS, *gen_panel_parts.OUTPUTS)    # before writing anything
    PANEL.mkdir(exist_ok=True)
    gen_panel_parts.main()
    write_project_files()
    build()
    guard.record(*OUTPUTS)
    print("wrote", PANEL / f"{PROJECT}.kicad_sch")
