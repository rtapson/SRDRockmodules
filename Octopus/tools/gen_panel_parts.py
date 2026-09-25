"""Writes the button-board custom parts: CTS 228C RGB switch symbol + footprint.

Outputs (in Octopus/panel/):
  OctopusPanel.kicad_sym                      symbol  CTS_228C_RGB
  OctopusPanel.pretty/CTS_228CMV_RGB.kicad_mod footprint (SMD gull wing)

Source: CTS Series 228C datasheet Rev. H, Figure 2 (228CMV). The RGB LED is common
anode: L3 = anode, L2 = red, L4 = green, L1 = blue cathodes. Switch pins 1-2 are one
contact, 3-4 the other (N.O.). Pad positions follow the datasheet's "PCB LAYOUT"
land pattern (top view); the part's bottom view agrees with it, its top view's LED
labels appear rotated 180 deg -- verify against a real part before ordering.
"""
import pathlib

PANEL = pathlib.Path(__file__).resolve().parent.parent / "panel"

SYMBOL_NAME = "CTS_228C_RGB"
FP_NAME = "CTS_228CMV_RGB"

# lib-space pin positions (y up); left = switch, right = LED
SYMBOL_PINS = [
    ("1", "S1", -10.16, 5.08, 0), ("2", "S1", -10.16, 2.54, 0),
    ("3", "S2", -10.16, -2.54, 0), ("4", "S2", -10.16, -5.08, 0),
    ("L3", "LED+", 10.16, 5.08, 180), ("L2", "R", 10.16, 2.54, 180),
    ("L4", "G", 10.16, 0, 180), ("L1", "B", 10.16, -2.54, 180),
]

# land pattern, top view, mm (y down)
SW_PADS = {"2": (-4.2, -2.25), "1": (4.2, -2.25), "4": (-4.2, 2.25), "3": (4.2, 2.25)}
LED_PADS = {"L3": (-0.95, -4.2), "L1": (0.95, -4.2), "L4": (-0.95, 4.2), "L2": (0.95, 4.2)}


def symbol_block(name):
    L = [f'\t(symbol "{name}"',
         '\t\t(pin_names (offset 1.016))',
         '\t\t(exclude_from_sim no)', '\t\t(in_bom yes)', '\t\t(on_board yes)', '\t\t(in_pos_files yes)',
         '\t\t(duplicate_pin_numbers_are_jumpers no)',
         '\t\t(property "Reference" "SW" (at 0 8.89 0) (effects (font (size 1.27 1.27))))',
         '\t\t(property "Value" "CTS_228C_RGB" (at 0 -8.89 0) (effects (font (size 1.27 1.27))))',
         f'\t\t(property "Footprint" "OctopusPanel:{FP_NAME}" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))',
         '\t\t(property "Datasheet" "https://www.ctscorp.com/Files/DataSheets/Switches/Tactile-Switches/CTS-Switches-Tactile-228C-Series-Datasheet.pdf" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))',
         '\t\t(property "Description" "CTS 228C illuminated tactile switch, N.O., RGB LED common anode (L3 +, L2 R, L4 G, L1 B)" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))',
         f'\t\t(symbol "{SYMBOL_NAME}_0_1"',
         '\t\t\t(rectangle (start -7.62 7.62) (end 7.62 -7.62)',
         '\t\t\t\t(stroke (width 0.254) (type default)) (fill (type background)))',
         '\t\t)',
         f'\t\t(symbol "{SYMBOL_NAME}_1_1"']
    for num, nm, x, y, a in SYMBOL_PINS:
        L.append(f'\t\t\t(pin passive line (at {x:g} {y:g} {a}) (length 2.54)')
        L.append(f'\t\t\t\t(name "{nm}" (effects (font (size 1.27 1.27))))')
        L.append(f'\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27)))))')
    L += ['\t\t)', '\t\t(embedded_fonts no)', '\t)']
    return "\n".join(L)


def line(x1, y1, x2, y2, layer, w):
    return f'\t(fp_line (start {x1:g} {y1:g}) (end {x2:g} {y2:g}) (stroke (width {w}) (type solid)) (layer "{layer}"))'


def footprint():
    out = [f'(footprint "{FP_NAME}"', '\t(version 20260206)', '\t(generator "octopus_gen")', '\t(layer "F.Cu")',
           '\t(descr "CTS 228CMV illuminated tactile switch, SMD gull wing, 7.2x6.8mm, RGB. Land pattern per CTS 228C datasheet Rev. H Fig. 2")',
           '\t(tags "CTS 228C tactile switch RGB illuminated")',
           '\t(property "Reference" "REF**" (at 0 -7.2 0) (layer "F.SilkS")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
           '\t(property "Value" "CTS_228CMV_RGB" (at 0 7.3 0) (layer "F.Fab")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
           '\t(attr smd)', '\t(duplicate_pad_numbers_are_jumpers no)']
    h = 3.6  # body half-size (7.2 mm)
    for x1, y1, x2, y2 in ((-h, -h, h, -h), (h, -h, h, h), (h, h, -h, h), (-h, h, -h, -h)):
        out.append(line(x1, y1, x2, y2, "F.Fab", 0.1))
    s = 3.75  # silk corner brackets clear of every pad
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(line(sx * s, sy * s, sx * s, sy * 3.05, "F.SilkS", 0.12))
            out.append(line(sx * s, sy * s, sx * 1.8, sy * s, "F.SilkS", 0.12))
    c = 5.95
    for x1, y1, x2, y2 in ((-c, -c, c, -c), (c, -c, c, c), (c, c, -c, c), (-c, c, -c, -c)):
        out.append(line(x1, y1, x2, y2, "F.CrtYd", 0.05))
    out.append('\t(fp_text user "+" (at -0.95 -6.2 0) (layer "F.SilkS")\n\t\t(effects (font (size 0.8 0.8) (thickness 0.12))))')
    out.append('\t(fp_text user "${REFERENCE}" (at 0 0 0) (layer "F.Fab")\n\t\t(effects (font (size 0.8 0.8) (thickness 0.12))))')
    for num, (x, y) in SW_PADS.items():
        out.append(f'\t(pad "{num}" smd rect (at {x:g} {y:g}) (size 2.4 1.0) (layers "F.Cu" "F.Mask" "F.Paste"))')
    for num, (x, y) in LED_PADS.items():
        out.append(f'\t(pad "{num}" smd rect (at {x:g} {y:g}) (size 0.8 2.4) (layers "F.Cu" "F.Mask" "F.Paste"))')
    out += ['\t(embedded_fonts no)', ')', '']
    return "\n".join(out)


def main():
    (PANEL / "OctopusPanel.pretty").mkdir(parents=True, exist_ok=True)
    (PANEL / "OctopusPanel.pretty" / f"{FP_NAME}.kicad_mod").write_text(footprint(), encoding="utf-8")
    lib = ['(kicad_symbol_lib', '\t(version 20251024)', '\t(generator "kicad_symbol_editor")',
           '\t(generator_version "10.0")', symbol_block(SYMBOL_NAME), '\t(embedded_fonts no)', ')', '']
    (PANEL / "OctopusPanel.kicad_sym").write_text("\n".join(lib), encoding="utf-8")
    print("wrote panel symbol + footprint")


if __name__ == "__main__":
    main()
