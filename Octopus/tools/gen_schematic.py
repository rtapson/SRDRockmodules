"""Generates Octopus.kicad_sch (+ Octopus.kicad_sym / sym-lib-table) from scratch.

The schematic is authored here as code rather than by hand-editing the KiCad
s-expression file directly, since the layout/wiring is entirely mechanical
(8 near-identical relay channels). Adjust the layout constants and per-section
code below, then run:

    python gen_schematic.py

Requires KiCad 10 installed at the path in LIBDIR (used to pull real symbol
definitions for Device:R, Isolator:6N138, Relay:G5V-1, etc. so the cached
lib_symbols exactly match KiCad's own library data). Re-running overwrites
Octopus.kicad_sch/.kicad_sym/sym-lib-table -- any manual edits made directly
in the KiCad GUI (component repositioning, added parts, footprint
assignments) will be lost, so treat this script as the source of truth while
still iterating on the design, and stop running it once you start doing
layout/footprint work by hand in KiCad.

Verify after regenerating:
    "<kicad>/bin/kicad-cli.exe" sch erc --severity-all Octopus.kicad_sch
"""
import re, uuid, pathlib
from collections import defaultdict

LIBDIR = pathlib.Path(r"C:/Program Files/KiCad/10.0/share/kicad/symbols")
OUT = pathlib.Path(__file__).resolve().parent.parent / "Octopus.kicad_sch"
PROJECT = "Octopus"
SHEET_UUID = "9e3c88f1-2947-4d19-8b1e-a1133b50f23f"

def U():
    return str(uuid.uuid4())

# ------------------------------------------------------------ lib extraction
def extract_symbol_block(text, name):
    marker = f'\t(symbol "{name}"'
    start = text.find(marker + "\n")
    if start == -1:
        raise ValueError(f"symbol {name} not found")
    depth = 0
    i = start
    n = len(text)
    began = False
    while i < n:
        c = text[i]
        if c == '(':
            depth += 1; began = True
        elif c == ')':
            depth -= 1
            if began and depth == 0:
                return text[start:i+1]
        i += 1
    raise ValueError("unbalanced")

def list_pins(block):
    pins = {}
    for m in re.finditer(r'\(pin (\w+) (\w+)\s*\n\s*\(at ([\-0-9.]+) ([\-0-9.]+) (\d+)\)', block):
        etype, style, x, y, angle = m.groups()
        tail = block[m.end():m.end()+400]
        num = re.search(r'\(number "([^"]*)"', tail)
        pins[num.group(1)] = {"x": float(x), "y": float(y), "angle": int(angle)}
    return pins

LIB_CACHE = {}

def load_lib_symbol(libfile, symname, libid):
    if libid in LIB_CACHE:
        return LIB_CACHE[libid]
    text = (LIBDIR / libfile).read_text(encoding="utf-8")
    block = extract_symbol_block(text, symname)
    pins = list_pins(block)
    renamed = block.replace(f'\t(symbol "{symname}"', f'\t(symbol "{libid}"', 1)
    LIB_CACHE[libid] = (renamed, pins)
    return LIB_CACHE[libid]

def load_power_symbol(name):
    return load_lib_symbol("power.kicad_sym", name, f"power:{name}")

# --------------------------------------------------------------- custom part
TEENSY_LIBID = "Octopus:Teensy4_1_Partial"
TEENSY_BASENAME = "Teensy4_1_Partial"
_gpio = [2,3,4,5,6,7,8,9]          # lines 1-8  (jack tips)  -> ULN2803A U3
_gpio_b = [24,25,26,27,28,29,30,31]  # lines 9-16 (jack rings) -> ULN2803A U5
# Each group listed high-to-low top-to-bottom so each pin lines up with the ULN2803A
# input it drives (see the channel mapping below).
GROUP_B_DY = 25.4                    # group B / U5 sit this far below group A / U3
TEENSY_RIGHT = {str(n): (15.24, 5.08 - i*2.54) for i, n in enumerate(reversed(_gpio))}
TEENSY_RIGHT.update({str(n): (15.24, 5.08 - GROUP_B_DY - i*2.54) for i, n in enumerate(reversed(_gpio_b))})
TEENSY_LEFT = {
    "VIN": (-15.24, 12.7),
    "G1":  (-15.24, 7.62),
    "3V3": (-15.24, 2.54),
    "G2":  (-15.24, -7.62),
    "0":   (-15.24, -12.7),
    "18":  (-15.24, -17.78),   # I2C0 SDA -> button panel
    "19":  (-15.24, -22.86),   # I2C0 SCL -> button panel
    "22":  (-15.24, -27.94),   # button panel interrupt (MCP23008 INT, open-drain)
}
TEENSY_PINS = {**TEENSY_RIGHT, **TEENSY_LEFT}
TEENSY_PIN_NAMES = {"VIN": "VIN", "G1": "GND", "G2": "GND", "3V3": "3V3", "0": "RX1",
                     "18": "SDA0", "19": "SCL0", "22": "IO22",
                     **{str(n): f"IO{n}" for n in _gpio + _gpio_b}}

def build_teensy_block(top_name):
    lines = []
    lines.append(f'\t(symbol "{top_name}"')
    lines.append('\t\t(pin_names (offset 1.016))')
    lines.append('\t\t(exclude_from_sim no)')
    lines.append('\t\t(in_bom yes)')
    lines.append('\t\t(on_board yes)')
    lines.append('\t\t(in_pos_files yes)')
    lines.append('\t\t(duplicate_pin_numbers_are_jumpers no)')
    lines.append('\t\t(property "Reference" "U" (at 0 19.5 0) (effects (font (size 1.27 1.27))))')
    lines.append('\t\t(property "Value" "Teensy4_1_Partial" (at 0 -43 0) (effects (font (size 1.27 1.27))))')
    lines.append('\t\t(property "Footprint" "" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))')
    lines.append('\t\t(property "Description" "Teensy 4.1 module -- reduced pinout showing only the pins used by the Octopus design (VIN, 3V3, 2x GND, MIDI RX1, 16x relay-driver GPIO). The physical board has many more pins available on its header for future expansion." (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))')
    lines.append(f'\t\t(symbol "{TEENSY_BASENAME}_0_1"')
    lines.append('\t\t\t(rectangle (start -12.7 17.78) (end 12.7 -40.64)')
    lines.append('\t\t\t\t(stroke (width 0.254) (type default)) (fill (type background)))')
    lines.append('\t\t)')
    lines.append(f'\t\t(symbol "{TEENSY_BASENAME}_1_1"')
    for num, (lx, ly) in TEENSY_PINS.items():
        angle = 0 if lx < 0 else 180
        nm = TEENSY_PIN_NAMES[num]
        lines.append(f'\t\t\t(pin passive line (at {lx:g} {ly:g} {angle}) (length 2.54)')
        lines.append(f'\t\t\t\t(name "{nm}" (effects (font (size 1.27 1.27))))')
        lines.append(f'\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27)))))')
    lines.append('\t\t)')
    lines.append('\t\t(embedded_fonts no)')
    lines.append('\t)')
    return "\n".join(lines)

# --------------------------------------------------------------- generation
components_text = []
wires = []          # list of ((x1,y1),(x2,y2))
forced_junctions = set()  # wire endpoints landing mid-wire; need an explicit junction to connect
no_connects = []          # intentionally unused pins
power_flag_text = []
pwr_counter = [100]

def add_wire(p1, p2):
    if p1 == p2:
        return
    wires.append((p1, p2))

def wire_path(points):
    for a, b in zip(points, points[1:]):
        add_wire(a, b)

def route(p1, p2, via="hv"):
    if p1[0] == p2[0] or p1[1] == p2[1]:
        add_wire(p1, p2)
        return
    mid = (p2[0], p1[1]) if via == "hv" else (p1[0], p2[1])
    add_wire(p1, mid)
    add_wire(mid, p2)

UUID_NS = uuid.UUID("5f0c1e2a-8d3b-4c6e-9a71-0c7a0c7a0c7a")

def stable_uuid(key):
    # deterministic per reference designator, so PCB footprint links survive regeneration
    return str(uuid.uuid5(UUID_NS, key))

FOOTPRINTS = {
    "Connector:Screw_Terminal_01x02": "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
    "Device:Polyfuse_Small": "Fuse:Fuse_Bourns_MF-RHT070",
    "Converter_DCDC:R-78E5.0-0.5": "Converter_DCDC:Converter_DCDC_RECOM_R-78E-0.5_THT",
    "Device:C_Polarized": "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm",
    "Connector:DIN-5": "Connector_JST:JST_XH_B5B-XH-A_1x05_P2.50mm_Vertical",
    "Device:R": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    "Device:D": "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal",
    "Isolator:6N138": "Package_DIP:DIP-8_W7.62mm",
    "Transistor_Array:ULN2803A": "Package_DIP:DIP-18_W7.62mm",
    "Relay:G5V-1": "Relay_THT:Relay_SPDT_Omron_G5V-1",
    "Device:LED": "LED_THT:LED_D3.0mm",
    "Connector_Audio:AudioJack3": "Octopus:Jack_6.35mm_Switchcraft_RN112BPC_Horizontal",
    "Jumper:SolderJumper_3_Bridged12": "Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm",
    "Octopus:Teensy4_1_Partial": "Octopus:Teensy41_Socketed",
    "Mechanical:MountingHole": "MountingHole:MountingHole_3.2mm_M3",
    "Connector_Generic:Conn_01x06": "Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical",
}
# LED resistors stand upright so each relay/LED/resistor cell fits the 19.05 mm jack pitch.
LED_R_FOOTPRINT = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical"

def place(libid, ref, value, x, y, pins_local, show_value=True, ref_hidden=False, value_dy=-6, in_bom=True, footprint=None):
    """pins_local: dict num -> (lx,ly). Returns sheet pin positions dict."""
    inst_uuid = stable_uuid(ref)
    footprint = footprint or FOOTPRINTS.get(libid, "")
    lines = []
    lines.append('\t(symbol')
    lines.append(f'\t\t(lib_id "{libid}")')
    lines.append(f'\t\t(at {x:g} {y:g} 0)')
    lines.append('\t\t(unit 1)')
    lines.append('\t\t(exclude_from_sim no)')
    lines.append(f'\t\t(in_bom {"yes" if in_bom else "no"})')
    lines.append('\t\t(on_board yes)')
    lines.append('\t\t(dnp no)')
    lines.append(f'\t\t(uuid "{inst_uuid}")')
    ref_hide = ' (hide yes)' if ref_hidden else ''
    lines.append(f'\t\t(property "Reference" "{ref}" (at {x:g} {y+6:g} 0){ref_hide} (effects (font (size 1.27 1.27))))')
    lines.append(f'\t\t(property "Value" "{value}" (at {x:g} {y+value_dy:g} 0) (effects (font (size 1.27 1.27))))')
    lines.append(f'\t\t(property "Footprint" "{footprint}" (at {x:g} {y:g} 0) (show_name no) (hide yes) (effects (font (size 1.27 1.27))))')
    pin_uuids = {}
    for num in pins_local:
        pu = stable_uuid(f"{ref}/pin/{num}")
        pin_uuids[num] = pu
        lines.append(f'\t\t(pin "{num}" (uuid "{pu}"))')
    lines.append('\t\t(instances')
    lines.append(f'\t\t\t(project "{PROJECT}"')
    lines.append(f'\t\t\t\t(path "/{SHEET_UUID}"')
    lines.append(f'\t\t\t\t\t(reference "{ref}")')
    lines.append('\t\t\t\t\t(unit 1)')
    lines.append('\t\t\t\t)')
    lines.append('\t\t\t)')
    lines.append('\t\t)')
    lines.append('\t)')
    components_text.append("\n".join(lines))
    sheet_pins = {}
    for num, (lx, ly) in pins_local.items():
        sheet_pins[num] = (round(x + lx, 4), round(y - ly, 4))
    return sheet_pins

def power_flag(kind, x, y):
    libid = f"power:{kind}"
    if libid not in LIB_CACHE:
        load_power_symbol(kind)
    pwr_counter[0] += 1
    ref = f"#PWR{pwr_counter[0]:03d}"
    place(libid, ref, kind, x, y, {"1": (0, 0)}, ref_hidden=True, value_dy=(-4 if kind == "GND" else 4))

def pins_of(libfile, symname, libid):
    _, pins = load_lib_symbol(libfile, symname, libid)
    return {num: (p["x"], p["y"]) for num, p in pins.items()}

# preload libs / pin tables
R_PINS   = pins_of("Device.kicad_sym", "R", "Device:R")
D_PINS   = pins_of("Device.kicad_sym", "D", "Device:D")
LED_PINS = pins_of("Device.kicad_sym", "LED", "Device:LED")
FUSE_PINS = pins_of("Device.kicad_sym", "Polyfuse_Small", "Device:Polyfuse_Small")
OPTO_PINS = pins_of("Isolator.kicad_sym", "6N138", "Isolator:6N138")
ULN_PINS  = pins_of("Transistor_Array.kicad_sym", "ULN2803A", "Transistor_Array:ULN2803A")
REG_PINS  = pins_of("Converter_DCDC.kicad_sym", "R-78E5.0-0.5", "Converter_DCDC:R-78E5.0-0.5")
CP_PINS   = pins_of("Device.kicad_sym", "C_Polarized", "Device:C_Polarized")
DIN_PINS  = pins_of("Connector.kicad_sym", "DIN-5", "Connector:DIN-5")
PWR_IN_PINS = pins_of("Connector.kicad_sym", "Screw_Terminal_01x02", "Connector:Screw_Terminal_01x02")
RELAY_PINS = pins_of("Relay.kicad_sym", "G5V-1", "Relay:G5V-1")
JACK_TRS_PINS = pins_of("Connector_Audio.kicad_sym", "AudioJack3", "Connector_Audio:AudioJack3")
JUMPER3_PINS = pins_of("Jumper.kicad_sym", "SolderJumper_3_Bridged12", "Jumper:SolderJumper_3_Bridged12")
HOLE_PINS = pins_of("Mechanical.kicad_sym", "MountingHole", "Mechanical:MountingHole")
CONN6_PINS = pins_of("Connector_Generic.kicad_sym", "Conn_01x06", "Connector_Generic:Conn_01x06")

LIB_CACHE[TEENSY_LIBID] = (build_teensy_block(TEENSY_LIBID), {n: {"x": lx, "y": ly} for n, (lx, ly) in TEENSY_PINS.items()})

# ------------------------------------------------------------- POWER SECTION
# Screw terminal rather than a barrel jack: the back panel has no DC jack hole. It takes a
# pigtail from a panel/inline DC jack now, or the DC output of a 12 V mains module later.
J2 = place("Connector:Screw_Terminal_01x02", "J2", "9-12VDC IN", 20, 30, PWR_IN_PINS)
F1 = place("Device:Polyfuse_Small", "F1", "MF-RHT070 0.7A", 45, 30, FUSE_PINS)
# 16 relay coils put the 5 V load near 630 mA -- far too much for a linear 7805 from
# 9-12 V, so a Recom R-78E switching module (7805 pinout) is used instead.
U4 = place("Converter_DCDC:R-78E5.0-0.5", "U4", "R-78E5.0-1.0", 65, 30, REG_PINS)
C1 = place("Device:C_Polarized", "C1", "10uF 25V", 52, 42, CP_PINS)
C2 = place("Device:C_Polarized", "C2", "22uF 10V", 80, 42, CP_PINS)

route(J2["1"], F1["1"])          # + -> fuse
route(F1["2"], U4["1"])          # fuse -> regulator IN
cin_tap = (C1["1"][0], F1["2"][1])
route(C1["1"], cin_tap)          # input cap taps the IN line
forced_junctions.add(cin_tap)
route(C2["1"], U4["3"], via="vh")   # output cap on OUT
power_flag("GND", *C1["2"])
power_flag("GND", *C2["2"])
power_flag("+5V", *U4["3"])      # regulator OUT -> +5V
power_flag("GND", *U4["2"])      # regulator GND
power_flag("GND", *J2["2"])      # - -> GND
power_flag("PWR_FLAG", *U4["1"])  # mark raw DC input as externally driven (silences ERC)
power_flag("PWR_FLAG", *U4["2"])  # mark GND net as externally driven (silences ERC)

# -------------------------------------------------------------- MIDI SECTION
# MIDI current loop is powered by the *sending* device; nothing on this side of the
# opto may touch our supply or ground, or the isolation the MIDI spec requires is lost.
J1 = place("Connector:DIN-5", "J1", "MIDI IN (to panel DIN)", 20, 90, DIN_PINS)
R1 = place("Device:R", "R1", "220", 50, 80, R_PINS)
D1 = place("Device:D", "D1", "1N4148", 65, 90, D_PINS)
U2 = place("Isolator:6N138", "U2", "6N138", 85, 90, OPTO_PINS)
R2 = place("Device:R", "R2", "470", 110, 90, R_PINS)

route(J1["4"], R1["1"], via="vh")    # DIN pin 4 -> 220R
route(R1["2"], U2["2"], via="vh")    # 220R -> opto LED anode
route(J1["5"], U2["3"])              # DIN pin 5 -> opto LED cathode
anode_tap = (D1["1"][0], U2["2"][1])
cathode_tap = (D1["2"][0], U2["3"][1])
add_wire(D1["1"], anode_tap)         # 1N4148 reverse-parallel across the LED
add_wire(D1["2"], cathode_tap)
forced_junctions.update({anode_tap, cathode_tap})

# Output side runs at 3.3 V: the Teensy 4.1 is NOT 5 V tolerant, so the opto is fed
# from the Teensy's own 3.3 V pin and pulled up there (PJRC's Teensy MIDI circuit).
power_flag("GND", *U2["5"])
power_flag("+3V3", *U2["8"])
power_flag("+3V3", *R2["1"])
route(R2["2"], U2["6"])          # pull-up -> opto output (MIDI_RX node)
no_connects.extend([J1["1"], J1["2"], J1["3"], U2["7"]])   # unused DIN pins, opto base tap

MIDI_RX = R2["2"]

# ------------------------------------------------------- TEENSY + ULN2803A
U1 = place(TEENSY_LIBID, "U1", "Teensy4.1", 150, 150, TEENSY_PINS)
U3 = place("Transistor_Array:ULN2803A", "U3", "ULN2803A", 185, 150, ULN_PINS)
U5 = place("Transistor_Array:ULN2803A", "U5", "ULN2803A", 185, 150 + GROUP_B_DY, ULN_PINS)

power_flag("+5V", *U1["VIN"])
power_flag("+3V3", *U1["3V3"])      # Teensy's onboard 3.3 V regulator feeds the MIDI opto side
power_flag("PWR_FLAG", *U1["3V3"])
power_flag("GND", *U1["G1"])
power_flag("GND", *U1["G2"])

# long way round, avoiding crossing straight through the Teensy body
wire_path([MIDI_RX, (125, MIDI_RX[1]), (125, U1["0"][1]), U1["0"]])

# Line n: 1-8 drive jack 1-8 TIP via U3 from Teensy pins 2-9; 9-16 drive jack 1-8 RING
# via U5 from pins 24-31. Within each driver, slot k (1..8) uses input I(9-k) / output
# O(9-k): both parts are counter-clockwise numbered, so on the PCB (Teensy above, ULN
# inputs facing it) this reversal is what lets the driver traces run straight.
def uln_in_pin(k):
    return str(9 - k)          # I(9-k) is DIP pin 9-k

def uln_out_pin(k):
    return str(10 + k)         # O(9-k) is DIP pin 19-(9-k)

LINES = {}                     # line n -> (teensy pin, driver refdes, driver pins, slot k)
for k in range(1, 9):
    LINES[k] = (k + 1, "U3", U3, k)
    LINES[k + 8] = (k + 23, "U5", U5, k)

for n, (tpin, _, drv, k) in LINES.items():
    route(U1[str(tpin)], drv[uln_in_pin(k)])

for drv in (U3, U5):
    power_flag("GND", *drv["9"])
    power_flag("+5V", *drv["10"])

# ------------------------------------------------------------- RELAY CHANNELS
labels = []  # (name, x, y, angle)

def label(name, x, y, angle):
    labels.append((name, x, y, angle))

def jack_of(n):
    return (n - 1) % 8 + 1     # lines n and n+8 share jack n (tip and ring)

# Driver outputs reach their channel blocks by net label (DRVn), not wires.
for n, (_, _, drv, k) in LINES.items():
    px, py = drv[uln_out_pin(k)]
    end = (round(px + 5.08, 4), py)
    add_wire((px, py), end)
    label(f"DRV{n}", end[0], end[1], 0)

# Two banks of 8 channel blocks: lines 1-8 (tips) then 9-16 (rings).
for n in range(1, 17):
    bx = 225 + ((n - 1) // 8) * 140
    ry = 40 + ((n - 1) % 8) * 26
    j = jack_of(n)

    K = place("Relay:G5V-1", f"K{n}", "G5V-1", bx + 15, ry, RELAY_PINS)
    power_flag("+5V", *K["2"])   # coil A -> +5V

    Rled = place("Device:R", f"R1{n:02d}", "1k", bx, ry - 20, R_PINS, footprint=LED_R_FOOTPRINT)
    power_flag("+5V", *Rled["1"])
    Led = place("Device:LED", f"LED{n}", "LED", bx, ry - 10, LED_PINS)
    route(Rled["2"], Led["2"])   # resistor -> LED anode

    bp = (bx, ry)                # switched node: coil B + LED cathode, driven by DRVn
    route(bp, K["9"])
    route(bp, Led["1"])
    label(f"DRV{n}", bp[0], bp[1], 270)

    # G5V-1: blade pivot (COM) = pins 5/6, rests on pin 1 (NC), swings to pin 10 (NO).
    # COM goes to the jack sleeve, shared by that jack's tip and ring lines.
    stub = 5.08
    for pin, net, direction in (("5", f"JACK{j}_SLV", +1), ("10", f"CH{n}_NO", -1), ("1", f"CH{n}_NC", -1)):
        px, py = K[pin]
        end = (px, round(py + direction * stub, 4))
        add_wire((px, py), end)
        label(net, end[0], end[1], 270 if direction > 0 else 90)

    # Per-line NO/NC select: ships bridged 1-2 (output = NO: closed to sleeve while the
    # line is on). Cut the 1-2 bridge and solder 2-3 for NC (open while the line is on).
    JP = place("Jumper:SolderJumper_3_Bridged12", f"JP{n}", "NO|NC", bx + 60, ry, JUMPER3_PINS, in_bom=False)
    for pin, net, (dx, dy), angle in (("1", f"CH{n}_NO", (-5.08, 0), 180),
                                      ("3", f"CH{n}_NC", (5.08, 0), 0),
                                      ("2", f"CH{n}_OUT", (0, 5.08), 270)):
        px, py = JP[pin]
        end = (round(px + dx, 4), round(py + dy, 4))
        add_wire((px, py), end)
        label(net, end[0], end[1], angle)

# Switchcraft RN112BPC TRS jacks: tip = line j, ring = line j+8, sleeve = their common.
for j in range(1, 9):
    T = place("Connector_Audio:AudioJack3", f"J{2 + j}", "RN112BPC", 480, 40 + (j - 1) * 26, JACK_TRS_PINS)
    for pin, net in (("T", f"CH{j}_OUT"), ("R", f"CH{j + 8}_OUT"), ("S", f"JACK{j}_SLV")):
        px, py = T[pin]
        end = (round(px + 7.62, 4), py)
        add_wire((px, py), end)
        label(net, end[0], end[1], 0)

# ------------------------------------------------------- button panel link
# 6-pin cable to the button board (panel/OctopusPanel); its I2C pull-ups live there.
for pin, net in (("18", "I2C_SDA"), ("19", "I2C_SCL"), ("22", "PANEL_INT")):
    px, py = U1[pin]
    end = (round(px - 5.08, 4), py)
    add_wire((px, py), end)
    label(net, end[0], end[1], 180)

J11 = place("Connector_Generic:Conn_01x06", "J11", "Button panel", 100, 210, CONN6_PINS)
for pin, kind, net in (("1", "+5V", None), ("2", "+3V3", None), ("3", "GND", None),
                       ("4", None, "I2C_SDA"), ("5", None, "I2C_SCL"), ("6", None, "PANEL_INT")):
    px, py = J11[pin]
    end = (round(px - 5.08, 4), py)
    add_wire((px, py), end)
    if kind:
        power_flag(kind, *end)
    else:
        label(net, end[0], end[1], 180)

# ----------------------------------------------------------- mounting holes
# two, on the case floor's screw bosses (the jack nuts hold the back edge)
for i in range(2):
    place("Mechanical:MountingHole", f"H{i + 1}", "M3", 20 + i * 12, 130, HOLE_PINS, in_bom=False)

# ------------------------------------------------------------ junction detect
endpoint_count = defaultdict(int)
for p1, p2 in wires:
    endpoint_count[p1] += 1
    endpoint_count[p2] += 1
auto_junctions = {pt for pt, c in endpoint_count.items() if c >= 3} | forced_junctions

# ------------------------------------------------------------------- assemble
def fmt_wire(p1, p2):
    return (
        "\t(wire\n"
        f"\t\t(pts\n\t\t\t(xy {p1[0]:g} {p1[1]:g}) (xy {p2[0]:g} {p2[1]:g})\n\t\t)\n"
        "\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n"
        f'\t\t(uuid "{U()}")\n'
        "\t)"
    )

def fmt_junction(pt):
    return (
        "\t(junction\n"
        f"\t\t(at {pt[0]:g} {pt[1]:g})\n"
        "\t\t(diameter 0)\n"
        '\t\t(color 0 0 0 0)\n'
        f'\t\t(uuid "{U()}")\n'
        "\t)"
    )

lib_symbols_block = "\n".join(text for text, _ in LIB_CACHE.values())

out = []
out.append('(kicad_sch')
out.append('\t(version 20260306)')
out.append('\t(generator "eeschema")')
out.append('\t(generator_version "10.0")')
out.append(f'\t(uuid "{SHEET_UUID}")')
out.append('\t(paper "A2")')
out.append('\t(title_block')
out.append('\t\t(title "Octopus")')
out.append('\t\t(comment 1 "SR&D Octopus clone - Teensy 4.1 MIDI 16-line relay switcher")')
out.append('\t)')
out.append('\t(lib_symbols')
out.append(lib_symbols_block)
out.append('\t)')
out.extend(components_text)
out.extend(power_flag_text)
for p1, p2 in wires:
    out.append(fmt_wire(p1, p2))
for pt in sorted(auto_junctions):
    out.append(fmt_junction(pt))
for x, y in no_connects:
    out.append(f'\t(no_connect\n\t\t(at {x:g} {y:g})\n\t\t(uuid "{U()}")\n\t)')
for name, x, y, angle in labels:
    justify = "right bottom" if angle in (180, 270) else "left bottom"
    out.append(
        f'\t(label "{name}"\n'
        f'\t\t(at {x:g} {y:g} {angle})\n'
        f'\t\t(effects (font (size 1.27 1.27)) (justify {justify}))\n'
        f'\t\t(uuid "{U()}")\n'
        '\t)'
    )
out.append('\t(sheet_instances')
out.append('\t\t(path "/"')
out.append('\t\t\t(page "1")')
out.append('\t\t)')
out.append('\t)')
out.append('\t(embedded_fonts no)')
out.append(')')
out.append('')

OUT.write_text("\n".join(out), encoding="utf-8")
print(f"Wrote {OUT} ({len(components_text)} components, {len(wires)} wires, {len(auto_junctions)} junctions)")

# ---------------------------------------------------- standalone symbol library
SYMLIB_OUT = OUT.parent / "Octopus.kicad_sym"
symlib = []
symlib.append('(kicad_symbol_lib')
symlib.append('\t(version 20251024)')
symlib.append('\t(generator "kicad_symbol_editor")')
symlib.append('\t(generator_version "10.0")')
symlib.append(build_teensy_block(TEENSY_BASENAME))
symlib.append('\t(embedded_fonts no)')
symlib.append(')')
symlib.append('')
SYMLIB_OUT.write_text("\n".join(symlib), encoding="utf-8")
print(f"Wrote {SYMLIB_OUT}")

SYMTABLE_OUT = OUT.parent / "sym-lib-table"
SYMTABLE_OUT.write_text(
    '(sym_lib_table\n'
    '\t(version 7)\n'
    '\t(lib (name "Octopus") (type "KiCad") (uri "${KIPRJMOD}/Octopus.kicad_sym") (options "") (descr ""))\n'
    ')\n',
    encoding="utf-8",
)
print(f"Wrote {SYMTABLE_OUT}")
