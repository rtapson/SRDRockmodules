"""Writes the Switchcraft RN-series right-angle Hi-D Jax footprints into Octopus.pretty/.

RN112BPC (3-conductor TRS, double open circuit) is what the board uses; RN111PC
(2-conductor TS) is kept for reference. Source: Switchcraft customer drawing
"RN111-RN114 SERIES, RIGHT ANGLE HI-D JAX" rev E, "PCB LAYOUT - COMPONENT SIDE" and
SECTION A-A. The jack lies on the board with the plug axis parallel to it, 9.65 mm
(0.380") above the board surface, and its 3/8-32 bushing overhangs the board edge
through the panel.

Footprint origin = the plug axis at the body's front face (the face that seats
against the inside of the panel); the bushing points toward +X. So a jack is placed
by putting its origin on the panel's inside face, on the hole's centreline.
Terminals are 0.40 x 1.27 mm blades (sleeve 0.30 x 1.27), drilled round so hole
orientation can't be gotten wrong. The three plastic locating posts get 2.41 mm
non-plated holes. Pad numbers match KiCad's AudioJack2/AudioJack3 symbols.
"""
import pathlib

LIB = pathlib.Path(__file__).resolve().parent.parent / "Octopus.pretty"

SLEEVE_X = -5.68            # 0.324" post-to-face minus the 0.100" post-to-sleeve offset
PITCH_ROW = 6.35            # tip/ring rows either side of the axis (0.500" apart)
TIP = (SLEEVE_X - 12.70, -PITCH_ROW)      # 0.724" behind the face
RING = (SLEEVE_X, PITCH_ROW)
SLEEVE = (SLEEVE_X, 0.0)
POSTS = [(SLEEVE_X - 15.24, 0.0), (SLEEVE_X - 2.54, -3.81), (SLEEVE_X - 2.54, 3.81)]

VARIANTS = {
    "RN111PC": {"pads": {"T": TIP, "S": SLEEVE}, "kind": "mono TS"},
    "RN112BPC": {"pads": {"T": TIP, "R": RING, "S": SLEEVE}, "kind": "stereo TRS"},
}

BODY_L, BODY_HALF = 25.0, 7.94    # 0.98" long, 0.625" wide
BUSHING_L, BUSHING_R = 7.02, 4.76  # 3/8-32 thread
CHAMFER = 4.5                      # rear corners (drawing)
DRILL, PAD = 1.5, 2.5              # blade diagonal 1.33 mm
POST_DRILL = 2.45                  # 0.095" +/- 0.001"

def poly(points, layer, width):
    pts = " ".join(f"(xy {x:.3f} {y:.3f})" for x, y in points)
    return (f'\t(fp_poly (pts {pts})\n'
            f'\t\t(stroke (width {width}) (type solid)) (fill no) (layer "{layer}"))')

def body(grow, front=None):
    x0, h, c = -BODY_L - grow, BODY_HALF + grow, CHAMFER
    xf = grow if front is None else front
    return [(x0, -h + c), (x0 + c, -h), (xf, -h), (xf, h), (x0 + c, h), (x0, h - c)]

def text(s, x, y, layer="F.SilkS"):
    return f'\t(fp_text user "{s}" (at {x:g} {y:g} 0) (layer "{layer}")\n\t\t(effects (font (size 1 1) (thickness 0.15))))'

def footprint(part, spec):
    name = f"Jack_6.35mm_Switchcraft_{part}_Horizontal"
    out = [
        f'(footprint "{name}"',
        '\t(version 20260206)',
        '\t(generator "octopus_gen")',
        '\t(layer "F.Cu")',
        f'\t(descr "Switchcraft {part} right-angle 1/4in {spec["kind"]} Hi-D Jax, PC terminals, 3/8-32 bushing overhangs the board edge. Origin = plug axis at the body front face. Switchcraft drawing RN111-RN114 SERIES rev E.")',
        f'\t(tags "Switchcraft 6.35mm 1/4 jack right angle {spec["kind"]} {part}")',
        '\t(property "Reference" "REF**" (at -14.5 2.5 0) (layer "F.SilkS")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
        f'\t(property "Value" "{part}" (at -12.5 9.2 0) (layer "F.Fab")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
        '\t(attr through_hole)',
        '\t(duplicate_pad_numbers_are_jumpers no)',
        poly(body(0), "F.Fab", 0.1),
        poly([(0, -BUSHING_R), (BUSHING_L, -BUSHING_R), (BUSHING_L, BUSHING_R), (0, BUSHING_R)], "F.Fab", 0.1),
        poly(body(0.12, front=-1.5), "F.SilkS", 0.12),    # stops short of the board edge the body overhangs
        poly(body(0.35), "F.CrtYd", 0.05),
        text("${REFERENCE}", -12.5, 0, "F.Fab"),
    ]
    for x, y in POSTS:
        out.append(f'\t(pad "" np_thru_hole circle (at {x:.3f} {y:.3f}) (size {POST_DRILL} {POST_DRILL}) (drill {POST_DRILL})\n'
                   '\t\t(layers "*.Cu" "*.Mask"))')
    for num, (x, y) in spec["pads"].items():
        out.append(f'\t(pad "{num}" thru_hole circle (at {x:.3f} {y:.3f}) (size {PAD} {PAD}) (drill {DRILL})\n'
                   '\t\t(layers "*.Cu" "*.Mask") (remove_unused_layers no))')
        out.append(text(num, x - 2.4 if num == "T" else x + 2.4, y))
    out += ['\t(embedded_fonts no)', ')', '']
    path = LIB / f"{name}.kicad_mod"
    path.write_text("\n".join(out), encoding="utf-8")
    print("wrote", path)

LIB.mkdir(parents=True, exist_ok=True)
for old in LIB.glob("Jack_6.35mm_Switchcraft_*_Vertical.kicad_mod"):
    old.unlink()          # superseded: drawn from the catalog's N-series (board-behind-panel) layout
for part, spec in VARIANTS.items():
    footprint(part, spec)
