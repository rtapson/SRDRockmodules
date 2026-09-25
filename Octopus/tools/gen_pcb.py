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

# ------------------------------------------------------------------ case geometry
# From case/*.step. Case frame: x across (+x = right, seen from the front), y front->back,
# z up, mm. The board lies flat in the case bottom, component side up, jacks along the
# back edge with their bushings through the back panel (inside face at y = 64.77).
PANEL_IN_Y = 64.77                  # back panel inside face
JACK_Z = 18.10                      # jack hole centres above the case bottom
JACK_AXIS_ABOVE_PCB = 9.65          # RN112BPC plug axis above the board surface
BOARD_TOP_Z = JACK_Z - JACK_AXIS_ABOVE_PCB          # 8.45: board rests on ~1.8 mm spacers
# Back panel holes (the panel is drilled to match these; see the README table). Jack 8 sits
# 0.8 mm clear of the left groove rib (x -103.19); from jack 1 rightward come MIDI IN, MIDI
# THRU and the cord hole, 1.5 mm apart.
JACK_PITCH = 17.78                  # 0.700"
JACK_SLEEVE_BEHIND_FACE = 5.68      # RN112BPC sleeve pin (footprint origin) behind its front face
JACK_X = [30.0 - JACK_PITCH * i for i in range(8)]  # hole centres; jack 1 is leftmost seen from the back
DIN_X = {"J1": 49.94, "J12": 72.44}                 # FM6725 MIDI IN, MIDI THRU
DIN_AXIS_ABOVE_PCB = 10.3                           # Cliff drawing (10.1 in the 3D model)
CORD_X, CORD_Z, CORD_D = 91.68, 21.53, 14.48        # power cord hole (unchanged size and height)
WALL_X = 102.9                      # clear of the side walls and the back-panel groove ribs
FRONT_Y = -47.5                     # clear of the button board's back-side parts
BACK_Y = 64.2                       # jack bodies seat on the panel; bushings overhang this edge
PILLARS = [(0.0, -38.1), (-96.84, 33.34), (96.84, 33.34)]   # top/bottom screw posts
PILLAR_CLEAR = 5.25                 # radius cut round each post (posts are r 4.75 at board height)
MOUNT_HOLES = [(-57.15, 9.52), (57.15, 9.52)]        # floor bosses (screw from below)
PSU_ZONE = (52.0, FRONT_Y, WALL_X, 5.0)             # front right, kept free for a mains module

# KiCad page coordinates: seen from above, back edge at the top
OX, OY = 150.0, 100.0
def K(x, y):
    return round(OX + x, 3), round(OY - y, 3)

# ------------------------------------------------------------------ placement
# (x, y, rotation_deg[, "B" for bottom side]) in KiCad mm; y grows toward the FRONT.
# Footprint origins are pad 1, except the output jacks (plug axis at the body's front face).
T_X, T_Y = 150.0, 112.0             # Teensy centre; rotated 270, driver pins facing the back
ULN_IN_Y = T_Y - 17.0               # ULN2803A input row (rotated 90: inputs facing the Teensy)
RELAY_Y = 64.0                      # relay pin-1 row (NC/NO pins toward the jacks)

def teensy_pad_x(position_index):
    # header position i, counted from the USB end; with the Teensy at 270 it runs toward -X
    return T_X + 29.21 - position_index * 2.54

PLACE = {
    "U1": (T_X, T_Y, 270),
    # rot 90 puts pin 1 at the origin with pins 1..9 running toward +X on the input row;
    # each driver's pin 1 (I1) sits right behind the last Teensy pin of its group:
    # U3 behind pin 9 (header position 10), U5 behind pin 31 (header position 22).
    "U3": (teensy_pad_x(10), ULN_IN_Y, 90),
    "U5": (teensy_pad_x(22), ULN_IN_Y, 90),
    "J11": (125.5, 142.5, 0),        # button-panel cable, at the front edge
    # power input right inside the cord hole (a DC pigtail now, a 12 V mains module later)
    "J2": (238.5, 48.0, 0),
    "F1": (215.5, 68.0, 0),
    "U4": (228.5, 72.0, 0),          # Recom R-78E (SIP-3)
    "C1": (218.0, 76.0, 0),
    "C2": (230.0, 81.0, 0),
    # MIDI IN opto and the THRU buffer, just in front of the two DIN sockets
    "U2": (191.0, 59.0, 0),
    "D1": (190.5, 72.5, 0),
    "R1": (190.5, 77.0, 0),
    "R2": (190.5, 81.5, 0),
    "U6": (204.0, 59.0, 0),
    "C3": (204.0, 79.0, 0),
    "R3": (215.5, 58.5, 0),
    "R4": (215.5, 63.0, 0),
}
for ref, dx in DIN_X.items():
    PLACE[ref] = (*K(dx, PANEL_IN_Y), 90)    # socket front on the panel, like the jacks
for i, (x, y) in enumerate(MOUNT_HOLES, 1):
    PLACE[f"H{i}"] = (*K(x, y), 0)

for k, jx in enumerate(JACK_X, 1):
    X, Y = K(jx, PANEL_IN_Y)
    # bushing toward the back edge; the footprint's origin is the sleeve pin, 5.68 mm
    # (0.324" - 0.100") behind the body's front face, which seats on the panel
    PLACE[f"J{2 + k}"] = (X, Y + JACK_SLEEVE_BEHIND_FACE, 90)
    # tip relay left of the jack's axis (under its tip pin), ring relay right of it
    for line, kx in ((k, X - 8.0), (k + 8, X + 1.2)):
        PLACE[f"K{line}"] = (kx, RELAY_Y, 0)
        # NO/NC solder jumper on the bottom, right behind its relay's NC/NO pins
        PLACE[f"JP{line}"] = (kx + 2.54, RELAY_Y - 3.8, 0, "B")

# Jack 8 sits in front of the left rear screw post, so its two relays go side by side in
# the open area below the notch (the jack wiring comes down the gap right of the notch),
# each jumper under its relay on the bottom side.
PLACE.update({
    "K16": (49.3, 84.0, 0), "JP16": (51.84, 89.1, 0, "B"),
    "K8": (59.0, 84.0, 0), "JP8": (61.54, 89.1, 0, "B"),
})

# ...and jack 7's tip cell shifts right to widen the gap jack 8's wiring runs down
for ref in ("K7", "JP7"):
    x, y, *rest = PLACE[ref]
    PLACE[ref] = (x + 0.5, y, *rest)

# parts whose silkscreen reference is left off
NO_SILK_REF = {"JP8", "JP16"}          # rotated jumpers: their NO/NC labels are enough
# reference moved inside the part outline, relative to the footprint origin
REF_AT = {}
for _k in range(1, 9):                 # RN112BPC: on the jack body, clear of the pins
    REF_AT[f"J{2 + _k}"] = (3.5, 9.0)
# pads whose pour connection is a lone island on one layer: connect solid, not by thermal spokes
SOLID_ZONE = {"U2"}

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
# project footprint libraries (as in fp-lib-table); everything else is KiCad's own
PROJECT_FP_LIBS = {"Octopus": PROJ / "Octopus.pretty", "RN112BPC": PROJ / "case" / "RN112BPC"}
# The SnapMagic RN112BPC footprint carries no 3D model reference; its STEP model's origin is
# 12.7 mm behind the sleeve pin with the bushing toward -X, so turn it 180 deg and shift it.
MODELS = {"RN112BPC:SWITCHCRAFT_RN112BPC": ("${KIPRJMOD}/case/RN112BPC/RN112BPC.step", (12.7, 0, 0), (0, 0, 180))}

def load_fp(fpid):
    nick, name = fpid.split(":", 1)
    libdir = PROJECT_FP_LIBS.get(nick, SYS_FP / f"{nick}.pretty")
    fp = pcbnew.FootprintLoad(str(libdir), name)
    if fp is None:
        raise RuntimeError(f"footprint {fpid} not found in {libdir}")
    fp.SetFPID(pcbnew.LIB_ID(nick, name))
    if fpid in MODELS:
        path, offset, rotation = MODELS[fpid]
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = path
        m.m_Offset = pcbnew.VECTOR3D(*offset)
        m.m_Rotation = pcbnew.VECTOR3D(*rotation)
        m.m_Scale = pcbnew.VECTOR3D(1, 1, 1)
        fp.Add3DModel(m)
    return fp

def label_jumper(board, fp):
    """Silkscreen 'NO'/'NC' under pads 1/3 of a NO/NC select jumper, on whichever side it sits."""
    layer = pcbnew.B_SilkS if fp.IsFlipped() else pcbnew.F_SilkS
    pads = {p.GetNumber(): p.GetPosition() for p in fp.Pads()}
    across = abs(pads["1"].x - pads["3"].x) < abs(pads["1"].y - pads["3"].y)   # pads in a column
    for num, text in (("1", "NO"), ("3", "NC")):
        pos = pads[num]
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text)
        t.SetLayer(layer)
        t.SetMirrored(fp.IsFlipped())
        t.SetTextSize(pcbnew.VECTOR2I_MM(0.8, 0.8))
        t.SetTextThickness(MM(0.12))
        if across:
            t.SetPosition(pcbnew.VECTOR2I(pos.x + MM(2.4), pos.y))
        else:
            t.SetPosition(pcbnew.VECTOR2I(pos.x, pos.y + MM(2.1)))  # clears the footprint's pin-1 marker
        board.Add(t)

def outline_points():
    """Board outline (case coordinates): full width, notched round the two rear screw posts."""
    w, r = WALL_X, PILLAR_CLEAR
    (_, _), (lx, ly), (rx, ry) = PILLARS
    return [(-w, FRONT_Y), (w, FRONT_Y), (w, ry - r), (rx - r, ry - r), (rx - r, ry + r), (w, ry + r),
            (w, BACK_Y), (-w, BACK_Y), (-w, ly + r), (lx + r, ly + r), (lx + r, ly - r), (-w, ly - r)]

def add_outline(board):
    pts = [K(x, y) for x, y in outline_points()]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I_MM(*a))
        s.SetEnd(pcbnew.VECTOR2I_MM(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(MM(0.1))
        board.Add(s)
    cx, cy = K(*PILLARS[0])                  # front post passes through the board
    c = pcbnew.PCB_SHAPE(board)
    c.SetShape(pcbnew.SHAPE_T_CIRCLE)
    c.SetCenter(pcbnew.VECTOR2I_MM(cx, cy))
    c.SetEnd(pcbnew.VECTOR2I_MM(cx + PILLAR_CLEAR, cy))
    c.SetLayer(pcbnew.Edge_Cuts)
    c.SetWidth(MM(0.1))
    board.Add(c)

def add_case_notes(board):
    """Dwgs.User (not fabricated): back panel line and the zone kept free for a mains PSU."""
    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I_MM(*K(*a)))
        s.SetEnd(pcbnew.VECTOR2I_MM(*K(*b)))
        s.SetLayer(pcbnew.Dwgs_User)
        s.SetWidth(MM(0.15))
        board.Add(s)
    seg((-WALL_X, PANEL_IN_Y), (WALL_X, PANEL_IN_Y))
    x0, y0, x1, y1 = PSU_ZONE
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        seg(a, b)
    for text, (x, y) in (("BACK PANEL (inside face)", (-60.0, PANEL_IN_Y + 1.5)),
                         ("keep free: future mains PSU", ((x0 + x1) / 2, (y0 + y1) / 2))):
        tx = pcbnew.PCB_TEXT(board)
        tx.SetText(text)
        tx.SetLayer(pcbnew.Dwgs_User)
        tx.SetTextSize(pcbnew.VECTOR2I_MM(1.5, 1.5))
        tx.SetPosition(pcbnew.VECTOR2I_MM(*K(x, y)))
        board.Add(tx)

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
        if ref in NO_SILK_REF:
            fp.Reference().SetVisible(False)
        if ref in SOLID_ZONE:
            fp.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        if ref in REF_AT:
            dx, dy = REF_AT[ref]
            fp.Reference().SetPosition(pcbnew.VECTOR2I_MM(x + dx, y + dy))

    add_outline(board)
    add_case_notes(board)
    add_preroutes(board, nets)
    board.Save(str(PCB))

    if route:
        autoroute(board)
        add_gnd_pours(board, nets["GND"])
        board.Save(str(PCB))
    return board

# Locked tracks laid before autorouting, where Freerouting otherwise boxes a pin in.
# Jack 8's tip pin sits in the corner above the rear-post notch, and its jumper's centre pad
# sits between the other two under relay K8: lay that whole run by hand -- from the tip
# pin, under the jack body, down the gap right of the notch, between K8's pins, and through
# a via onto JP8's centre pad (bottom side).
def jack8_tip_route():
    sx, sy = PLACE["J10"][:2]                       # sleeve pin (footprint origin)
    tip = (sx - 6.35, sy + 12.7)
    gap_x = K(PILLARS[1][0] + PILLAR_CLEAR, 0)[0] + 1.8   # 1.8 mm right of the notch edge
    jp_x, jp_y = PLACE["JP8"][:2]                  # JP8 centre pad (pin 2)
    via = (jp_x, jp_y - 1.6)
    front = [tip, (gap_x - 3.0, tip[1]), (gap_x, tip[1] + 3.0), (gap_x, 72.4),
             (jp_x, 72.4 + jp_x - gap_x), via]
    return {"net": "/CH8_OUT", "width": 0.6, "front": front, "via": via, "back": [via, (jp_x, jp_y)]}

def add_preroutes(board, nets):
    r = jack8_tip_route()
    net = nets[r["net"]]
    for layer, pts in ((pcbnew.F_Cu, r["front"]), (pcbnew.B_Cu, r["back"])):
        for a, b in zip(pts, pts[1:]):
            tr = pcbnew.PCB_TRACK(board)
            tr.SetStart(pcbnew.VECTOR2I_MM(*a))
            tr.SetEnd(pcbnew.VECTOR2I_MM(*b))
            tr.SetWidth(MM(r["width"]))
            tr.SetLayer(layer)
            tr.SetNet(net)
            tr.SetLocked(True)
            board.Add(tr)
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I_MM(*r["via"]))
    v.SetWidth(MM(1.0))
    v.SetDrill(MM(0.5))
    v.SetNet(net)
    v.SetLocked(True)
    board.Add(v)

def autoroute(board, passes=300):
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
        # a plain rectangle: the filler clips it to the outline, notches and post hole
        for x, y in ((-WALL_X, FRONT_Y), (WALL_X, FRONT_Y), (WALL_X, BACK_Y), (-WALL_X, BACK_Y)):
            px, py = K(x, y)
            o.Append(MM(px), MM(py))
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

def report_alignment(board):
    """Sanity check: each Teensy driver pin should sit directly above its ULN input."""
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    pos = lambda ref, num: [pcbnew.ToMM(v) for v in next(p for p in fps[ref].Pads() if p.GetNumber() == num).GetPosition()]
    bad = []
    for drv, first_pin, base in (("U3", 2, 0), ("U5", 24, 8)):
        for k in range(1, 9):
            tx, ty = pos("U1", str(first_pin + k - 1))
            ux, uy = pos(drv, str(9 - k))
            ox, oy = pos(drv, str(10 + k))
            if abs(tx - ux) > 0.01 or abs(ux - ox) > 0.01:
                bad.append(base + k)
            print(f"line{base + k:2d}: teensy pin{first_pin + k - 1:2d} x={tx:.2f}  {drv} in x={ux:.2f}  out x={ox:.2f}")
    print("driver alignment:", "OK" if not bad else f"MISALIGNED lines {bad}")

if __name__ == "__main__":
    b = build(route="--no-route" not in sys.argv)
    report_alignment(b)
    print("saved", PCB)
