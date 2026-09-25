"""Builds panel/OctopusPanel.kicad_pcb: the button board.

Front (F.Cu): the 8 Omron B3W-9 switches in 2 rows of 4 at the right, and left of them the
OLED module (on 5 mm spacers) and the rotary encoder -- only parts the front panel needs.
Back (B.Cu): each button's 2 LED resistors beside it, the PCA9685 (under
the display), the MCP23017 with the encoder's RC filters, decoupling, I2C pull-ups and
the cable header.

All geometry is given in FRONT-PANEL coordinates: origin at the panel's top-left corner
seen from the front, x to the right, y down, mm. The panel is 8.5" x 1.75" (1U, half
rack). The panel outline and button holes are also drawn on Dwgs.User (not fabricated)
as a fit/drilling reference.

Case fit (from case/Top.step, Bottom.step, FrontPanel.step -- case frame: x across,
y front->back, z up; front panel spans x -108.12..107.78, z -1.14..43.31):
  * The board slides into a 2.03 mm groove (y -60.96..-58.93) formed by two vertical
    ribs on each side wall, 2.54 mm deep (wall at x = +-105.73, rib faces at +-103.19),
    running from the floor (z 2.22) to the roof (z 41.09).
  * A 2.54 mm rib runs across the floor (z <= 4.76) and roof (z >= 38.55) directly
    BEHIND the board, and the wall ribs cover the board's ends on both faces -- hence the
    footprint keep-out rule areas added below.
  * The board's front face ends up ~9.3 mm behind the inside of the front panel.

Run with KiCad's bundled Python:
    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/gen_panel_pcb.py [--no-route]
"""
import pathlib
import re
import subprocess
import sys

import pcbnew

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import guard  # noqa: E402  (refuses to overwrite hand-edited files)
from gen_pcb import (FREEROUTING_JAR, JAVA, KICAD_CLI, SYS_FP, MM,  # noqa: E402
                     parse_netlist)

TOOLS = pathlib.Path(__file__).resolve().parent
PANEL = TOOLS.parent / "panel"
SCH = PANEL / "OctopusPanel.kicad_sch"
PCB = PANEL / "OctopusPanel.kicad_pcb"
BUILD = PANEL / "build"

# ------------------------------------------------------------------ panel geometry (mm)
PANEL_W, PANEL_H = 8.5 * 25.4, 1.75 * 25.4      # 215.9 x 44.45
PITCH = 15.24                                    # 0.6" between button centres, both ways
RIGHT_COL_FROM_EDGE = 25.4                       # right-hand column 1.0" in from the panel edge
CAP_HOLE = 10.6                                  # square panel cut-out for the 10 x 10 mm B3W-9 cap
COLS = [PANEL_W - RIGHT_COL_FROM_EDGE - (3 - c) * PITCH for c in range(4)]
# display (active area centre) and encoder (shaft), left of the buttons at mid-height
DISPLAY_U = 121.0
ENCODER_U = 92.0
DISPLAY_WINDOW = (25.0, 13.0)                    # panel cut-out: the 23.94 x 12.06 viewing area + margin
ENCODER_HOLE_D = 7.5                             # clears the EC11E's 6 mm shaft and 7 mm bushing
ARRAY_U = 137.0                                  # LED resistor arrays, between display and buttons
ROWS = [PANEL_H / 2 - PITCH / 2, PANEL_H / 2 + PITCH / 2]

# Case frame -> panel coordinates: u = x - PANEL_X0, v = PANEL_Z1 - z
PANEL_X0, PANEL_Z1 = -108.12, 43.31
GROOVE_X = 105.73                                # side-wall groove bottoms at x = +-105.73
RIB_X = 103.19                                   # wall rib faces: groove is 2.54 mm deep
FLOOR_Z, ROOF_Z = 2.22, 41.09                    # inside floor / roof at the groove
FLOOR_RIB_Z, ROOF_RIB_Z = 4.76, 38.55            # tops of the ribs behind the board
FIT = 0.25                                       # clearance to the groove on each edge
KEEPOUT_MARGIN = 0.5


def case_to_panel(x, z):
    return x - PANEL_X0, PANEL_Z1 - z


BOARD_LEFT, BOARD_BOTTOM = case_to_panel(-GROOVE_X + FIT, FLOOR_Z + FIT)
BOARD_RIGHT, BOARD_TOP = case_to_panel(GROOVE_X - FIT, ROOF_Z - FIT)
BOARD_H = BOARD_BOTTOM - BOARD_TOP
MID = PANEL_H / 2
# band where back-side parts can go (clear of the floor/roof ribs) and the ends that sit
# inside the wall grooves (no parts on either side)
BACK_TOP = case_to_panel(0, ROOF_RIB_Z - KEEPOUT_MARGIN)[1]
BACK_BOTTOM = case_to_panel(0, FLOOR_RIB_Z + KEEPOUT_MARGIN)[1]
END_LEFT = case_to_panel(-RIB_X + KEEPOUT_MARGIN, 0)[0]
END_RIGHT = case_to_panel(RIB_X - KEEPOUT_MARGIN, 0)[0]
HOLES = []                                       # the groove holds the board; no screws

# KiCad page coordinates = panel coordinates + this offset
OX, OY = 40.0, 60.0
BX, BY, BW, BH = OX + BOARD_LEFT, OY + BOARD_TOP, BOARD_RIGHT - BOARD_LEFT, BOARD_H


def button_xy(n):
    """Panel position of button n (1-8): top row 1-4, bottom row 5-8, left to right."""
    return COLS[(n - 1) % 4], ROWS[(n - 1) // 4]


PLACE = {}                  # ref -> (x, y, rot, side), in panel coordinates
for n in range(1, 9):
    cx, cy = button_xy(n)
    PLACE[f"SW{n}"] = (cx, cy, 0, "F")
# OLED header pins and M2.5 screw heads (back side, ~5 mm across) are kept clear below
PLACE.update({
    # front: display module (origin = active area centre) and encoder (origin = pin A;
    # its shaft is 7.5 mm right of and 2.5 mm below pin A)
    "J2": (DISPLAY_U, MID, 0, "F"),
    "SW9": (ENCODER_U - 7.5, MID - 2.5, 0, "F"),
    # back: the LED driver under the display, between its header and its lower screws,
    # decoupling on the left so the outputs have the right-hand side to themselves on their
    # way to the buttons
    "U1": (DISPLAY_U, MID, 0, "B"), "C1": (DISPLAY_U - 6.0, MID, 90, "B"),
    # LED resistor arrays in the strip between the display and the first button column,
    # beside the row they serve (RN1/RN3: red/green of buttons 1-4; RN2/RN4: 5-8). On the
    # back their LED-side pins (1-4) face the buttons.
    "RN1": (ARRAY_U, ROWS[0] - 3.5, 0, "B"), "RN3": (ARRAY_U, ROWS[0] + 3.5, 0, "B"),
    "RN2": (ARRAY_U, ROWS[1] - 3.5, 0, "B"), "RN4": (ARRAY_U, ROWS[1] + 3.5, 0, "B"),
    # button/encoder expander in the open area left of the encoder, its RC filters beside it
    "U3": (70.0, MID, 0, "B"), "C2": (70.0, 34.5, 0, "B"),
    "R3": (79.0, 16.5, 0, "B"), "R4": (79.0, 19.0, 0, "B"), "R5": (79.0, 21.5, 0, "B"),
    "C5": (79.0, 24.0, 0, "B"), "C6": (79.0, 26.5, 0, "B"), "C7": (79.0, 29.0, 0, "B"),
    # cable header high up (see the case notes), I2C pull-ups and bulk caps beside the encoder
    "J1": (95.0, 9.5, 0, "B"),
    "R1": (104.0, 16.0, 0, "B"), "R2": (104.0, 18.5, 0, "B"),
    "C3": (104.0, 30.5, 0, "B"), "C4": (104.0, 33.0, 0, "B"),
})
for i, (x, y) in enumerate(HOLES, 1):
    PLACE[f"H{i}"] = (x, y, 0, "F")

# parts packed too closely for a silkscreen reference
TIGHT = {f"R{i}" for i in range(1, 6)} | {"C3", "C4", "C5", "C6", "C7"}


def export_netlist():
    BUILD.mkdir(exist_ok=True)
    net = BUILD / "OctopusPanel.net"
    subprocess.run([str(KICAD_CLI), "sch", "export", "netlist", "--format", "kicadsexpr",
                    "-o", str(net), str(SCH)], check=True, capture_output=True)
    return net.read_text(encoding="utf-8")


def load_fp(fpid):
    nick, name = fpid.split(":", 1)
    libdir = PANEL / f"{nick}.pretty" if nick == "OctopusPanel" else SYS_FP / f"{nick}.pretty"
    fp = pcbnew.FootprintLoad(str(libdir), name)
    if fp is None:
        raise RuntimeError(f"footprint {fpid} not found in {libdir}")
    fp.SetFPID(pcbnew.LIB_ID(nick, name))
    return fp


def silk_text(board, text, x, y, layer, size=1.0, mirrored=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetLayer(layer)
    t.SetMirrored(mirrored)
    t.SetTextSize(pcbnew.VECTOR2I_MM(size, size))
    t.SetTextThickness(MM(0.15))
    t.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    board.Add(t)


def add_rect(board, x1, y1, x2, y2, layer, width):
    r = pcbnew.PCB_SHAPE(board)
    r.SetShape(pcbnew.SHAPE_T_RECT)
    r.SetStart(pcbnew.VECTOR2I_MM(x1, y1))
    r.SetEnd(pcbnew.VECTOR2I_MM(x2, y2))
    r.SetLayer(layer)
    r.SetWidth(MM(width))
    board.Add(r)


def draw_panel_reference(board):
    """Front panel outline + cap holes on Dwgs.User: a fit check and drilling template."""
    add_rect(board, OX, OY, OX + PANEL_W, OY + PANEL_H, pcbnew.Dwgs_User, 0.15)
    for n in range(1, 9):
        cx, cy = button_xy(n)
        h = CAP_HOLE / 2
        add_rect(board, OX + cx - h, OY + cy - h, OX + cx + h, OY + cy + h, pcbnew.Dwgs_User, 0.15)
    w, h = DISPLAY_WINDOW                         # display window and encoder shaft hole
    add_rect(board, OX + DISPLAY_U - w / 2, OY + MID - h / 2, OX + DISPLAY_U + w / 2, OY + MID + h / 2,
             pcbnew.Dwgs_User, 0.15)
    c = pcbnew.PCB_SHAPE(board)
    c.SetShape(pcbnew.SHAPE_T_CIRCLE)
    c.SetCenter(pcbnew.VECTOR2I_MM(OX + ENCODER_U, OY + MID))
    c.SetEnd(pcbnew.VECTOR2I_MM(OX + ENCODER_U + ENCODER_HOLE_D / 2, OY + MID))
    c.SetLayer(pcbnew.Dwgs_User)
    c.SetWidth(MM(0.15))
    board.Add(c)
    silk_text(board, 'FRONT PANEL 8.5" x 1.75" (1U half rack) - reference only, seen from the front',
              OX + PANEL_W / 2 - 40, OY + PANEL_H + 3, pcbnew.Dwgs_User, size=1.5)


def build(route=True):
    guard.check(PCB)
    comps, pinnet, net_names = parse_netlist(export_netlist())
    missing = [r for r in comps if r not in PLACE]
    if missing:
        raise RuntimeError(f"no placement for {missing}")
    loaded = {ref: load_fp(c["footprint"]) for ref, c in sorted(comps.items())}

    # fresh board from the template (see gen_pcb.py for why we never board.Remove())
    PCB.write_text((TOOLS / "board_template.kicad_pcb").read_text(encoding="utf-8"), encoding="utf-8")
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
        x, y, rot, side = PLACE[ref]
        fp.SetPosition(pcbnew.VECTOR2I_MM(OX + x, OY + y))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            netname = pinnet.get((ref, pad.GetNumber()))
            if netname in nets:
                pad.SetNet(nets[netname])
        board.Add(fp)
        if side == "B":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)   # after Add(): needs the layer stack
        if ref in TIGHT:
            fp.Reference().SetVisible(False)   # no room on silk; still on the fab layer
        if ref in ("J1", "U3") or ref in {f"SW{n}" for n in range(1, 9)}:
            # the pour reaches these GND pins through a single gap (J1: a small front island
            # between the header's pins; U3: VSS between its routed neighbours; the switches'
            # contact pins among the LED traces); connect them solid so they aren't flagged as
            # starved thermals
            fp.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

    for n in range(1, 9):     # button numbers (= output jacks 1-8), in the gap left of each button
        cx, cy = button_xy(n)
        silk_text(board, str(n), OX + cx - PITCH / 2, OY + cy, pcbnew.F_SilkS)
    silk_text(board, "OCTOPUS BUTTON PANEL  J1 -> main board J11", BX + BW / 2 + 6, BY + 1.8,
              pcbnew.B_SilkS, size=1.0, mirrored=True)

    add_rect(board, BX, BY, BX + BW, BY + BH, pcbnew.Edge_Cuts, 0.1)
    draw_panel_reference(board)
    board.Save(str(PCB))

    if route:
        autoroute(board)
        add_gnd_pours(board, nets["GND"])
    add_case_keepouts(board)
    board.Save(str(PCB))
    return board


def add_case_keepouts(board):
    """Footprint keep-outs where the case ribs sit against the board (tracks/pours allowed)."""
    def area(name, layer, u0, v0, u1, v1):
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetZoneName(name)
        z.SetLayer(layer)
        z.SetDoNotAllowFootprints(True)
        z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowVias(False)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowZoneFills(False)
        o = z.Outline()
        o.NewOutline()
        for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1)):
            o.Append(MM(OX + u), MM(OY + v))
        board.Add(z)

    area("case roof rib", pcbnew.B_Cu, BOARD_LEFT, BOARD_TOP, BOARD_RIGHT, BACK_TOP)
    area("case floor rib", pcbnew.B_Cu, BOARD_LEFT, BACK_BOTTOM, BOARD_RIGHT, BOARD_BOTTOM)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        area("left wall groove", layer, BOARD_LEFT, BOARD_TOP, END_LEFT, BOARD_BOTTOM)
        area("right wall groove", layer, END_RIGHT, BOARD_TOP, BOARD_RIGHT, BOARD_BOTTOM)


def autoroute(board, passes=300):
    BUILD.mkdir(exist_ok=True)
    dsn, ses = BUILD / "OctopusPanel.dsn", BUILD / "OctopusPanel.ses"
    if ses.exists():
        ses.unlink()
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        raise RuntimeError("DSN export failed")
    text = dsn.read_text(encoding="utf-8")   # 10 um routing margin, as in gen_pcb.py
    text = re.sub(r"\(clearance (\d+(?:\.\d+)?)\)", lambda m: f"(clearance {float(m.group(1)) + 10:g})", text)
    dsn.write_text(text, encoding="utf-8")
    cmd = [str(JAVA), "-jar", str(FREEROUTING_JAR), "-de", str(dsn), "-do", str(ses),
           "-mp", str(passes), "--gui.enabled=false", "--api_server.enabled=false"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    (BUILD / "freerouting.log").write_text(r.stdout + r.stderr, encoding="utf-8")
    if not ses.exists():
        raise RuntimeError(f"Freerouting produced no session file (exit {r.returncode})")
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        raise RuntimeError("SES import failed")


def add_gnd_pours(board, gnd):
    inset = 0.5
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetLocalClearance(MM(0.3))
        z.SetMinThickness(MM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(MM(0.4))
        z.SetThermalReliefSpokeWidth(MM(0.4))
        o = z.Outline()
        o.NewOutline()
        for x, y in ((BX + inset, BY + inset), (BX + BW - inset, BY + inset),
                     (BX + BW - inset, BY + BH - inset), (BX + inset, BY + BH - inset)):
            o.Append(MM(x), MM(y))
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


if __name__ == "__main__":
    build(route="--no-route" not in sys.argv)
    guard.record(PCB)
    print("saved", PCB)
