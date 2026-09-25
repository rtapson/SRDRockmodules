"""Writes the Cliff FM6725 (DIN-5 180 deg, screened, right-angle PCB) footprint into Octopus.pretty/.

Source: Cliff "Screened DIN connectors" datasheet (case/screeneddins.pdf, 02/2025 iss.4),
"PC LAYOUT (BOTTOM VIEW)", checked against the 3D model case/FM6725.stp. Seen from the
component side with the socket's front face toward +X:
  * pins 1, 2, 3 are 12.50 mm behind the front mounting face (FMF), at +7.5 / 0 / -7.5 mm
    across; pins 4 and 5 are 15.00 mm behind, at +5.0 / -5.0 mm
  * the two screen legs are 2.5-3.0 mm behind the FMF, 5.00 mm apart
  * holes are 1.50 mm; the socket axis is 10.3 mm above the board (10.1 in the 3D model)
Pin 1 is on the right when you look into the socket from outside, as in the DIN front
view. The screen legs are numbered "2" so they share DIN pin 2's net: grounded on a MIDI
THRU/OUT, left floating on a MIDI IN (both as the MIDI spec requires).

Footprint origin = socket axis at the front mounting face, like the jack footprints, so a
socket is placed by putting its origin on the panel's inside face.
"""
import pathlib

LIB = pathlib.Path(__file__).resolve().parent.parent / "Octopus.pretty"
NAME = "DIN-5_180deg_Cliff_FM6725_Horizontal"

PINS = {"1": (-12.5, -7.5), "2": (-12.5, 0.0), "3": (-12.5, 7.5), "4": (-15.0, -5.0), "5": (-15.0, 5.0)}
SCREEN = [(-2.75, -2.5), (-2.75, 2.5)]
DRILL, PAD = 1.5, 2.3
W, DEPTH = 21.0, 19.2           # front screen width; overall depth incl. the rear pins
SOCKET_D = 14.0

def poly(points, layer, width):
    pts = " ".join(f"(xy {x:.3f} {y:.3f})" for x, y in points)
    return (f'\t(fp_poly (pts {pts})\n'
            f'\t\t(stroke (width {width}) (type solid)) (fill no) (layer "{layer}"))')

def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

def pad(num, x, y):
    return (f'\t(pad "{num}" thru_hole circle (at {x:.3f} {y:.3f}) (size {PAD} {PAD}) (drill {DRILL})\n'
            '\t\t(layers "*.Cu" "*.Mask") (remove_unused_layers no))')

def main():
    h = W / 2
    out = [
        f'(footprint "{NAME}"',
        '\t(version 20260206)',
        '\t(generator "octopus_gen")',
        '\t(layer "F.Cu")',
        '\t(descr "Cliff FM6725 DIN-5 180deg socket with screen, right-angle PCB mount. Origin = socket axis at the front mounting face; front toward +X. Cliff screened DIN datasheet 02/2025 iss.4.")',
        '\t(tags "DIN 5 pin 180 degree MIDI socket Cliff FM6725 D5SA")',
        '\t(property "Reference" "REF**" (at -7.0 0 90) (layer "F.SilkS")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
        '\t(property "Value" "FM6725" (at -9.5 11.8 0) (layer "F.Fab")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
        '\t(attr through_hole)',
        '\t(duplicate_pad_numbers_are_jumpers no)',
        poly(rect(-DEPTH + 2.0, -h, 0, h), "F.Fab", 0.1),
        # silk stops short of the front face, which sits at (or past) the board edge
        poly([(-1.5, -h - 0.12), (-DEPTH + 1.88, -h - 0.12), (-DEPTH + 1.88, h + 0.12), (-1.5, h + 0.12)], "F.SilkS", 0.12),
        poly(rect(-DEPTH - 0.3, -h - 0.3, 0.3, h + 0.3), "F.CrtYd", 0.05),
        f'\t(fp_circle (center 0 0) (end {SOCKET_D / 2} 0) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab"))',
        '\t(fp_text user "${REFERENCE}" (at -9.5 0 90) (layer "F.Fab")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
        '\t(fp_text user "1" (at -12.5 -9.4 0) (layer "F.SilkS")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
    ]
    out += [pad(n, x, y) for n, (x, y) in PINS.items()]
    out += [pad("2", x, y) for x, y in SCREEN]          # screen legs share pin 2's net
    out += [
        '\t(model "${KIPRJMOD}/case/FM6725.stp"',
        '\t\t(offset (xyz -2.0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz -90 0 -90)))',
        '\t(embedded_fonts no)', ')', '']
    LIB.mkdir(parents=True, exist_ok=True)
    path = LIB / f"{NAME}.kicad_mod"
    path.write_text("\n".join(out), encoding="utf-8")
    print("wrote", path)

if __name__ == "__main__":
    main()
