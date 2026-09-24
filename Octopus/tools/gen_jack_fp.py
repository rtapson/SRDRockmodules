"""Writes Octopus.pretty/Jack_6.35mm_Switchcraft_RN111PC_Vertical.kicad_mod.

Switchcraft RN111PC (Hi-D Jax Series 11, 2-conductor, open circuit, insulated
bushing, PC terminals). Dimensions from the "Recommended PC board layout
(component side)" drawing in the Switchcraft catalog (EDG41, catalog p.100):
the jack stands perpendicular to the board, and the plug tip passes through a
0.25" clearance hole centred on the plug axis. Footprint origin = plug axis.
Terminals are 0.078" x 0.016" flat blades; drilled round here so hole
orientation can't be gotten wrong.
"""
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "Octopus.pretty" / "Jack_6.35mm_Switchcraft_RN111PC_Vertical.kicad_mod"
IN = 25.4

PADS = {                     # AudioJack2 pin numbers
    "T": (-0.250 * IN, 0.022 * IN),
    "S": (0.182 * IN, 0.182 * IN),
}
DRILL, PAD = 2.2, 3.5        # clears a 1.98 x 0.41 mm blade (diagonal 2.02 mm)
CLEARANCE_HOLE = 6.4         # 0.25" plug-tip clearance
HALF = 0.31 * IN             # body is ~0.62" square
CHAMFER = 0.12 * IN          # chamfered corner on the sleeve side

def poly(points, layer, width):
    pts = " ".join(f"(xy {x:.3f} {y:.3f})" for x, y in points)
    return (f'\t(fp_poly (pts {pts})\n'
            f'\t\t(stroke (width {width}) (type solid)) (fill no) (layer "{layer}"))')

def outline(h, c):
    return [(-h, -h), (h, -h), (h, h - c), (h - c, h), (-h, h)]

out = [
    '(footprint "Jack_6.35mm_Switchcraft_RN111PC_Vertical"',
    '\t(version 20260206)',
    '\t(generator "octopus_gen")',
    '\t(layer "F.Cu")',
    '\t(descr "Switchcraft RN111PC / N111PC 1/4in mono jack, PC terminals, mounts perpendicular to the board with plug tip through a 0.25in clearance hole. Catalog EDG41 p.100.")',
    '\t(tags "Switchcraft 6.35mm 1/4 jack mono TS RN111PC N111PC")',
    '\t(property "Reference" "REF**" (at 0 -9.2 0) (layer "F.SilkS")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
    '\t(property "Value" "RN111PC" (at 0 9.3 0) (layer "F.Fab")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
    '\t(attr through_hole)',
    '\t(duplicate_pad_numbers_are_jumpers no)',
    poly(outline(HALF, CHAMFER), "F.Fab", 0.1),
    # tip pad reaches past the body edge, so silk/courtyard sit outside the pads
    poly(outline(HALF + 0.6, CHAMFER), "F.SilkS", 0.12),
    poly(outline(HALF + 0.8, CHAMFER), "F.CrtYd", 0.05),
    '\t(fp_text user "T" (at -6.35 -2.6 0) (layer "F.SilkS")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
    '\t(fp_text user "S" (at 4.6 1.4 0) (layer "F.SilkS")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
    '\t(fp_text user "${REFERENCE}" (at 0 -5.5 0) (layer "F.Fab")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
    f'\t(pad "" np_thru_hole circle (at 0 0) (size {CLEARANCE_HOLE} {CLEARANCE_HOLE}) (drill {CLEARANCE_HOLE})\n'
    '\t\t(layers "*.Cu" "*.Mask"))',
]
for num, (x, y) in PADS.items():
    out.append(f'\t(pad "{num}" thru_hole circle (at {x:.4f} {y:.4f}) (size {PAD} {PAD}) (drill {DRILL})\n'
               '\t\t(layers "*.Cu" "*.Mask") (remove_unused_layers no))')
out += ['\t(embedded_fonts no)', ')', '']

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(out), encoding="utf-8")
print("wrote", OUT)
