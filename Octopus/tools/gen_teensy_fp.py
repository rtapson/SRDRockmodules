import pathlib
import guard  # noqa: E402  (refuses to overwrite hand-edited files)

OUT = pathlib.Path(__file__).resolve().parent.parent / "Octopus.pretty" / "Teensy41_Socketed.kicad_mod"

# Teensy 4.1, top view, USB end toward -Y. Outer two rows only (bottom pads unused).
LEFT = ["G1", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12",
        "3V3", "24", "25", "26", "27", "28", "29", "30", "31", "32"]
RIGHT = ["VIN", "G2", "3V3", "23", "22", "21", "20", "19", "18", "17", "16", "15", "14", "13",
         "G2", "41", "40", "39", "38", "37", "36", "35", "34", "33"]
assert len(LEFT) == len(RIGHT) == 24

ROW_X = 7.62
PITCH = 2.54
Y0 = -29.21
W, H = 17.78, 60.96

def line(x1, y1, x2, y2, layer, width):
    return (f'\t(fp_line (start {x1:g} {y1:g}) (end {x2:g} {y2:g})\n'
            f'\t\t(stroke (width {width}) (type solid)) (layer "{layer}"))')

def rect(x1, y1, x2, y2, layer, width):
    return "\n".join([line(x1, y1, x2, y1, layer, width), line(x2, y1, x2, y2, layer, width),
                      line(x2, y2, x1, y2, layer, width), line(x1, y2, x1, y1, layer, width)])

def text(kind, value, x, y, layer, hide=False):
    h = " (hide yes)" if hide else ""
    return (f'\t(property "{kind}" "{value}" (at {x:g} {y:g} 0) (layer "{layer}"){h}\n'
            f'\t\t(effects (font (size 1 1) (thickness 0.15))))')

out = []
out.append('(footprint "Teensy41_Socketed"')
out.append('\t(version 20260206)')
out.append('\t(generator "octopus_gen")')
out.append('\t(layer "F.Cu")')
out.append('\t(descr "PJRC Teensy 4.1 on 2x24 0.1in female headers (outer rows only), row spacing 15.24mm. USB end toward -Y.")')
out.append('\t(tags "Teensy 4.1 PJRC socket")')
out.append(text("Reference", "REF**", 0, -32.5, "F.SilkS"))
out.append(text("Value", "Teensy41_Socketed", 0, 32.5, "F.Fab"))
out.append('\t(attr through_hole)')
out.append('\t(duplicate_pad_numbers_are_jumpers no)')
hw, hh = W / 2, H / 2
out.append(rect(-hw, -hh, hw, hh, "F.Fab", 0.1))
out.append(rect(-hw - 0.12, -hh - 0.12, hw + 0.12, hh + 0.12, "F.SilkS", 0.12))
out.append(rect(-hw - 0.25, -hh - 0.25, hw + 0.25, hh + 0.25, "F.CrtYd", 0.05))
# USB connector outline marker at the -Y end
out.append(rect(-3.8, -hh + 0.5, 3.8, -hh + 4.0, "F.SilkS", 0.12))
out.append('\t(fp_text user "USB" (at 0 -24.8 0) (layer "F.SilkS")\n\t\t(effects (font (size 1 1) (thickness 0.15))))')
out.append('\t(fp_text user "${REFERENCE}" (at 0 0 90) (layer "F.Fab")\n\t\t(effects (font (size 1 1) (thickness 0.15))))')

for i, (ln, rn) in enumerate(zip(LEFT, RIGHT)):
    y = Y0 + i * PITCH
    for name, x in ((ln, -ROW_X), (rn, ROW_X)):
        shape = "rect" if (i == 0 and x < 0) else "circle"
        out.append(f'\t(pad "{name}" thru_hole {shape} (at {x:g} {y:g}) (size 1.7 1.7) (drill 1.0)\n'
                   f'\t\t(layers "*.Cu" "*.Mask") (remove_unused_layers no))')
    # silk pin labels, just inside the outline
    out.append(f'\t(fp_text user "{ln}" (at {-ROW_X + 2.3:g} {y:g} 0) (layer "F.Fab")\n\t\t(effects (font (size 0.6 0.6) (thickness 0.1))))')
    out.append(f'\t(fp_text user "{rn}" (at {ROW_X - 2.3:g} {y:g} 0) (layer "F.Fab")\n\t\t(effects (font (size 0.6 0.6) (thickness 0.1))))')

out.append('\t(embedded_fonts no)')
out.append(')')
out.append('')

OUT.parent.mkdir(parents=True, exist_ok=True)
guard.check(OUT)
OUT.write_text("\n".join(out), encoding="utf-8")
guard.record(OUT)
print("wrote", OUT)
