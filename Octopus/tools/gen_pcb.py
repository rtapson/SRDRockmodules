"""Builds Octopus.kicad_pcb: footprint placement, net assignment, outline, autoroute, GND pour.

Run with KiCad's bundled Python (it provides the `pcbnew` module):

    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/gen_pcb.py [--no-route]

Inputs: the netlist exported from Octopus.kicad_sch (regenerated here via kicad-cli).
Routing uses Freerouting (FREEROUTING_JAR / JAVA below) through KiCad's Specctra
DSN export / SES import. Re-running rebuilds the board from scratch, so stop using
this once you begin hand-editing the layout in KiCad.
"""
import os, re, subprocess, sys, pathlib
import pcbnew

HERE = pathlib.Path(__file__).resolve().parent
PROJ = HERE.parent
SCH = PROJ / "Octopus.kicad_sch"
PCB = PROJ / "Octopus.kicad_pcb"
BUILD = PROJ / "build"
KICAD_BIN = pathlib.Path(r"C:/Program Files/KiCad/10.0/bin")
KICAD_CLI = KICAD_BIN / "kicad-cli.exe"
SYS_FP = pathlib.Path(r"C:/Program Files/KiCad/10.0/share/kicad/footprints")
FREEROUTING_JAR = pathlib.Path(os.environ.get("FREEROUTING_JAR", r"C:/Users/rtaps/tools/freerouting/freerouting-2.4.1.jar"))
JAVA = pathlib.Path(os.environ.get("JAVA25", r"C:/Program Files/Eclipse Adoptium/jdk-25.0.4.101-hotspot/bin/java.exe"))

MM = pcbnew.FromMM

# ------------------------------------------------------------------ board frame
BX, BY, BW, BH = 100.0, 100.0, 160.0, 100.0

# ------------------------------------------------------------------ placement
# (x, y, rotation_deg) in board mm; y grows downward. Footprint origins are pad 1,
# except the output jacks, whose origin is the plug axis.
TERM_X1 = 110.2          # channel 1 column reference x
COL = 18.5               # per-channel column pitch (RN111PC needs >= 15.9 mm centres)
JACK_Y = BY + BH - 9.5   # RN111PC plug axis; body is ~15.8 mm square, stands off the board
RELAY_Y = 169.0
LED_Y = 161.0
RES_Y = 154.0
T_X, T_Y = 131.5, 118.0  # Teensy centre; rotated 90 so USB points at the left edge
ULN_Y = 135.0            # ULN2803A input row (rotated 270: inputs on top, facing the Teensy)

def teensy_pad_x(position_index):
    return T_X - 29.21 + position_index * 2.54

PLACE = {
    "U1": (T_X, T_Y, 90),
    # rot 270 puts pin 1 at the origin with pins 1..9 running toward -X on the top row;
    # pin 1 (I1, channel 8) must sit under Teensy pin 9 (header position 10)
    "U3": (teensy_pad_x(10), ULN_Y, 270),
    "J2": (245.0, 113.0, 270),   # barrel jack, plug entry through the top edge
    "F1": (230.0, 118.0, 0),
    "U4": (218.0, 108.0, 0),     # TO-220 tab toward the top edge (room for a heatsink)
    "J1": (178.0, 103.5, 0),     # MIDI harness header at the top edge
    "U2": (182.0, 115.0, 0),
    "R1": (195.0, 113.0, 0),
    "R2": (195.0, 119.0, 0),
    "D1": (168.0, 114.0, 0),
}
for k in range(1, 9):
    tx = TERM_X1 + (k - 1) * COL
    PLACE[f"J{2 + k}"] = (tx + 5.08, JACK_Y, 0)
    # NO/NC solder jumper on the *bottom* side, just below the jack's plug hole: the
    # component side faces the jack panel, so the back is what you can reach.
    PLACE[f"JP{k}"] = (tx + 5.08, JACK_Y + 6.0, 0, "B")
    PLACE[f"K{k}"] = (tx + 1.0, RELAY_Y, 0)
    PLACE[f"LED{k}"] = (tx + 1.0, LED_Y, 0)
    PLACE[f"R1{k:02d}"] = (tx - 1.0, RES_Y, 0)

for i, (x, y) in enumerate([(104.5, 104.5), (255.5, 104.5), (104.5, 178.0), (255.5, 178.0)], 1):
    PLACE[f"H{i}"] = (x, y, 0)

# ------------------------------------------------------------------ netlist
def export_netlist():
    BUILD.mkdir(exist_ok=True)
    net = BUILD / "Octopus.net"
    subprocess.run([str(KICAD_CLI), "sch", "export", "netlist", "--format", "kicadsexpr",
                    "-o", str(net), str(SCH)], check=True, capture_output=True)
    return net.read_text(encoding="utf-8")

def parse_netlist(text):
    comps = {}
    comp_sec = text[text.index("(components"):text.index("(libparts")]
    for blk in re.split(r"\n\t\t\(comp\n", comp_sec)[1:]:
        ref = re.search(r'\(ref "([^"]+)"\)', blk).group(1)
        val = re.search(r'\(value "([^"]*)"\)', blk).group(1)
        fp = re.search(r'\(footprint "([^"]*)"\)', blk)
        ts = re.findall(r'\(tstamps "([^"]+)"\)', blk)
        comps[ref] = {"value": val, "footprint": fp.group(1) if fp else "", "uuid": ts[-1]}
    pinnet = {}
    net_names = []
    nets = text[text.index("(nets"):]
    for blk in re.split(r"\n\t\t\(net\n", nets)[1:]:
        name = re.search(r'\(name "([^"]*)"\)', blk).group(1)
        net_names.append(name)
        for ref, pin in re.findall(r'\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', blk):
            pinnet[(ref, pin)] = name
    return comps, pinnet, net_names

# ------------------------------------------------------------------ helpers
def load_fp(fpid):
    nick, name = fpid.split(":", 1)
    libdir = PROJ / f"{nick}.pretty" if nick == "Octopus" else SYS_FP / f"{nick}.pretty"
    fp = pcbnew.FootprintLoad(str(libdir), name)
    if fp is None:
        raise RuntimeError(f"footprint {fpid} not found in {libdir}")
    fp.SetFPID(pcbnew.LIB_ID(nick, name))
    return fp

def label_jumper(board, fp):
    """Silkscreen 'NO'/'NC' under pads 1/3 of a NO/NC select jumper, on whichever side it sits."""
    layer = pcbnew.B_SilkS if fp.IsFlipped() else pcbnew.F_SilkS
    pads = {p.GetNumber(): p.GetPosition() for p in fp.Pads()}
    for num, text in (("1", "NO"), ("3", "NC")):
        pos = pads[num]
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text)
        t.SetLayer(layer)
        t.SetMirrored(fp.IsFlipped())
        t.SetTextSize(pcbnew.VECTOR2I_MM(0.8, 0.8))
        t.SetTextThickness(MM(0.12))
        t.SetPosition(pcbnew.VECTOR2I(pos.x, pos.y + MM(2.1)))  # clears the footprint's pin-1 marker
        board.Add(t)

def edge_rect(board, x, y, w, h):
    r = pcbnew.PCB_SHAPE(board)
    r.SetShape(pcbnew.SHAPE_T_RECT)
    r.SetStart(pcbnew.VECTOR2I_MM(x, y))
    r.SetEnd(pcbnew.VECTOR2I_MM(x + w, y + h))
    r.SetLayer(pcbnew.Edge_Cuts)
    r.SetWidth(MM(0.1))
    board.Add(r)

# ------------------------------------------------------------------ build
def build(route=True):
    comps, pinnet, net_names = parse_netlist(export_netlist())
    missing = [r for r in comps if r not in PLACE]
    if missing:
        raise RuntimeError(f"no placement for {missing}")

    loaded = {ref: load_fp(c["footprint"]) for ref, c in sorted(comps.items())}

    # Start from an empty template rather than clearing the old board: calling
    # board.Remove() on footprints breaks this KiCad build's SWIG type registry
    # (later FootprintLoad()/Pads() calls return untyped SwigPyObjects).
    PCB.write_text((HERE / "board_template.kicad_pcb").read_text(encoding="utf-8"), encoding="utf-8")
    board = pcbnew.LoadBoard(str(PCB))

    nets = {}
    for name in net_names:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni

    for ref, c in sorted(comps.items()):
        fp = loaded[ref]
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH(f"/{c['uuid']}"))
        fp.SetSheetname("/")
        fp.SetSheetfile(SCH.name)
        x, y, rot, *side = PLACE[ref]
        fp.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            netname = pinnet.get((ref, pad.GetNumber()))
            if netname in nets:
                pad.SetNet(nets[netname])
        board.Add(fp)
        if side == ["B"]:
            # must happen after board.Add(): Flip() needs the board's layer stack (segfaults otherwise)
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        if ref.startswith("JP"):
            label_jumper(board, fp)

    edge_rect(board, BX, BY, BW, BH)
    board.Save(str(PCB))

    if route:
        autoroute(board)
        add_gnd_pours(board, nets["GND"])
        board.Save(str(PCB))
    return board

def autoroute(board, passes=100):
    BUILD.mkdir(exist_ok=True)
    dsn, ses = BUILD / "Octopus.dsn", BUILD / "Octopus.ses"
    if ses.exists():
        ses.unlink()
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        raise RuntimeError("DSN export failed")
    # Route with a 10 um safety margin over KiCad's clearances: Freerouting's coordinate
    # rounding otherwise lands the odd track a fraction of a micron under the rule.
    text = dsn.read_text(encoding="utf-8")
    text = re.sub(r"\(clearance (\d+(?:\.\d+)?)\)", lambda m: f"(clearance {float(m.group(1)) + 10:g})", text)
    dsn.write_text(text, encoding="utf-8")
    cmd = [str(JAVA), "-jar", str(FREEROUTING_JAR), "-de", str(dsn), "-do", str(ses),
           "-mp", str(passes), "--gui.enabled=false", "--api_server.enabled=false"]
    print("running:", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    (BUILD / "freerouting.log").write_text(r.stdout + r.stderr, encoding="utf-8")
    if not ses.exists():
        raise RuntimeError(f"Freerouting produced no session file (exit {r.returncode}); see build/freerouting.log")
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        raise RuntimeError("SES import failed")

def add_gnd_pours(board, gnd):
    inset = 0.5
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetLocalClearance(MM(0.5))
        z.SetMinThickness(MM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(MM(0.5))
        z.SetThermalReliefSpokeWidth(MM(0.5))
        o = z.Outline()
        o.NewOutline()
        for x, y in ((BX + inset, BY + inset), (BX + BW - inset, BY + inset),
                     (BX + BW - inset, BY + BH - inset), (BX + inset, BY + BH - inset)):
            o.Append(MM(x), MM(y))
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

def report_alignment(board):
    """Sanity check: each Teensy driver pin should sit directly above its ULN input."""
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    pos = lambda ref, num: [pcbnew.ToMM(v) for v in next(p for p in fps[ref].Pads() if p.GetNumber() == num).GetPosition()]
    for k in range(1, 9):
        tx, ty = pos("U1", str(k + 1))
        ux, uy = pos("U3", str(9 - k))
        ox, oy = pos("U3", str(10 + k))
        print(f"ch{k}: teensy pin{k+1} ({tx:.2f},{ty:.2f})  ULN in ({ux:.2f},{uy:.2f})  ULN out ({ox:.2f},{oy:.2f})")

if __name__ == "__main__":
    b = build(route="--no-route" not in sys.argv)
    report_alignment(b)
    print("saved", PCB)
