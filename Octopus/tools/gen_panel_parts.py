"""Writes the button-board custom parts: the Omron B3W-9 two-LED switch symbol + footprint,
and the OLED module footprint.

Outputs (in Octopus/panel/):
  OctopusPanel.kicad_sym                              symbol     B3W-9_RG
  OctopusPanel.pretty/Omron_B3W-9_2LED_10x10.kicad_mod   footprint  (through hole)
  OctopusPanel.pretty/OLED_Winstar_WEA012864D-03.kicad_mod

Switch source: Omron B3W-9 datasheet (Cat. No. A167-E1-08), "2 LED Types" dimensions,
"PCB Processing Dimensions" and "Terminal Arrangement/Internal Connections" (top view).
B3W-9000-RG2N: 10 x 10 mm milky-white cap, 11 mm tall, red LED 1 + green LED 2, each
with its own anode and cathode. Switch terminals 1-2 are one contact, 3-4 the other (N.O.).
Top view, mm: switch pins at (+-3.25, +-2.25); LED 1 (red) anode (0, -3.6), cathode
(+3.6, 0); LED 2 (green) anode (0, +3.6), cathode (-3.6, 0). Eight 1.0 mm holes.
"""
import pathlib

PANEL = pathlib.Path(__file__).resolve().parent.parent / "panel"

SYMBOL_NAME = "B3W-9_RG"
FP_NAME = "Omron_B3W-9_2LED_10x10"

# lib-space pin positions (y up); left = switch, right = LEDs
SYMBOL_PINS = [
    ("1", "S1", -10.16, 5.08, 0), ("2", "S1", -10.16, 2.54, 0),
    ("3", "S2", -10.16, -2.54, 0), ("4", "S2", -10.16, -5.08, 0),
    ("A1", "R+", 10.16, 5.08, 180), ("K1", "R-", 10.16, 2.54, 180),
    ("A2", "G+", 10.16, -2.54, 180), ("K2", "G-", 10.16, -5.08, 180),
]

# top view, mm (y down)
SW_PADS = {"4": (-3.25, -2.25), "3": (3.25, -2.25), "2": (-3.25, 2.25), "1": (3.25, 2.25)}
LED_PADS = {"A1": (0, -3.6), "K1": (3.6, 0), "A2": (0, 3.6), "K2": (-3.6, 0)}
BODY = 10.0


def symbol_block(name):
    L = [f'\t(symbol "{name}"',
         '\t\t(pin_names (offset 1.016))',
         '\t\t(exclude_from_sim no)', '\t\t(in_bom yes)', '\t\t(on_board yes)', '\t\t(in_pos_files yes)',
         '\t\t(duplicate_pin_numbers_are_jumpers no)',
         '\t\t(property "Reference" "SW" (at 0 8.89 0) (effects (font (size 1.27 1.27))))',
         '\t\t(property "Value" "B3W-9000-RG2N" (at 0 -8.89 0) (effects (font (size 1.27 1.27))))',
         f'\t\t(property "Footprint" "OctopusPanel:{FP_NAME}" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))',
         '\t\t(property "Datasheet" "https://omronfs.omron.com/en_US/ecb/products/pdf/en-b3w-9.pdf" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))',
         '\t\t(property "Description" "Omron B3W-9 illuminated tactile switch, N.O., two LEDs with separate leads (LED 1 red A1/K1, LED 2 green A2/K2)" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))',
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
           '\t(descr "Omron B3W-9 illuminated tactile switch, 10x10 mm, two LEDs (B3W-9000-xx2x), through hole. Omron datasheet A167-E1-08 PCB processing dimensions.")',
           '\t(tags "Omron B3W-9 tactile switch illuminated two LED red green")',
           '\t(property "Reference" "REF**" (at 0 -6.4 0) (layer "F.SilkS")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
           '\t(property "Value" "B3W-9000-RG2N" (at 0 6.4 0) (layer "F.Fab")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
           '\t(attr through_hole)', '\t(duplicate_pad_numbers_are_jumpers no)']
    h = BODY / 2
    for x1, y1, x2, y2 in ((-h, -h, h, -h), (h, -h, h, h), (h, h, -h, h), (-h, h, -h, -h)):
        out.append(line(x1, y1, x2, y2, "F.Fab", 0.1))
    s = h + 0.12
    for x1, y1, x2, y2 in ((-s, -s, s, -s), (s, -s, s, s), (s, s, -s, s), (-s, s, -s, -s)):
        out.append(line(x1, y1, x2, y2, "F.SilkS", 0.12))
    c = h + 0.7                  # room for the cathode mark just outside the outline
    for x1, y1, x2, y2 in ((-c, -c, c, -c), (c, -c, c, c), (c, c, -c, c), (-c, c, -c, -c)):
        out.append(line(x1, y1, x2, y2, "F.CrtYd", 0.05))
    # the part's cathode mark is on the LED 1 (red) cathode side: right, top view
    out.append(f'\t(fp_circle (center {h + 0.4:g} 0) (end {h + 0.6:g} 0) (stroke (width 0.12) (type solid)) (fill yes) (layer "F.SilkS"))')
    out.append('\t(fp_text user "${REFERENCE}" (at 0 0 0) (layer "F.Fab")\n\t\t(effects (font (size 0.8 0.8) (thickness 0.12))))')
    for num, (x, y) in {**SW_PADS, **LED_PADS}.items():
        shape = "rect" if num in ("1", "A1") else "circle"
        out.append(f'\t(pad "{num}" thru_hole {shape} (at {x:g} {y:g}) (size 1.6 1.6) (drill 1.0)\n'
                   '\t\t(layers "*.Cu" "*.Mask") (remove_unused_layers no))')
    out += ['\t(embedded_fonts no)', ')', '']
    return "\n".join(out)


# ---------------------------------------------------------------- OLED module
# Winstar WEA012864D-03: 0.96" 128x64 SSD1306 I2C module, "Contour Drawing" in its
# datasheet. Seen from the front (display side): 27.3 x 27.3 mm PCB, 4 x 2.5 mm holes on a
# 20.7 x 23.2 mm pattern (2.05 mm below the top edge), 4-pin 2.54 mm header centred 1.65 mm
# below the top edge, pin 1 (VCC) on the left: VCC, GND, SCL, SDA. The 21.74 x 10.86 mm
# active area is centred left-right and its top is 6.46 mm below the PCB's top edge.
# The module stands off the board on 5 mm M2.5 spacers with its own header pins pushed
# through; the footprint origin is the ACTIVE AREA CENTRE, which is where the panel window
# goes.
OLED_FP = "OLED_Winstar_WEA012864D-03"
OLED_PCB = 27.3
OLED_AA = (21.74, 10.86)
OLED_VA = (23.94, 12.06)
OLED_GLASS = (26.7, 19.26)
OLED_TOP = -(6.46 + OLED_AA[1] / 2)         # PCB top edge relative to the AA centre
OLED_PINS_Y = OLED_TOP + 1.65
OLED_HOLES = [(sx * 20.7 / 2, OLED_TOP + 2.05 + dy) for dy in (0, 23.2) for sx in (-1, 1)]
OLED_PIN_NAMES = ("VCC", "GND", "SCL", "SDA")


def rect_lines(x1, y1, x2, y2, layer, w):
    return [line(x1, y1, x2, y1, layer, w), line(x2, y1, x2, y2, layer, w),
            line(x2, y2, x1, y2, layer, w), line(x1, y2, x1, y1, layer, w)]


def oled_footprint():
    h = OLED_PCB / 2
    top, bot = OLED_TOP, OLED_TOP + OLED_PCB
    gy = OLED_TOP + 4.02
    out = [f'(footprint "{OLED_FP}"', '\t(version 20260206)', '\t(generator "octopus_gen")', '\t(layer "F.Cu")',
           '\t(descr "Winstar WEA012864D-03 0.96in 128x64 SSD1306 I2C OLED module on 5 mm M2.5 spacers, header pins through the board. Origin = active area centre. Winstar datasheet contour drawing.")',
           '\t(tags "OLED SSD1306 0.96 128x64 I2C Winstar WEA012864D")',
           f'\t(property "Reference" "REF**" (at 0 {bot + 1.4:.2f} 0) (layer "F.SilkS")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
           f'\t(property "Value" "WEA012864D-03" (at 0 {bot - 3:.2f} 0) (layer "F.Fab")\n\t\t(effects (font (size 1 1) (thickness 0.15))))',
           '\t(attr through_hole)', '\t(duplicate_pad_numbers_are_jumpers no)']
    out += rect_lines(-h, top, h, bot, "F.Fab", 0.1)                                   # module PCB
    out += rect_lines(-OLED_GLASS[0] / 2, gy, OLED_GLASS[0] / 2, gy + OLED_GLASS[1], "F.Fab", 0.1)
    out += rect_lines(-OLED_AA[0] / 2, -OLED_AA[1] / 2, OLED_AA[0] / 2, OLED_AA[1] / 2, "F.Fab", 0.1)
    out += rect_lines(-h - 0.12, top - 0.12, h + 0.12, bot + 0.12, "F.SilkS", 0.12)
    out += rect_lines(-h - 0.4, top - 0.4, h + 0.4, bot + 0.4, "F.CrtYd", 0.05)
    out.append('\t(fp_text user "ACTIVE AREA" (at 0 0 0) (layer "F.Fab")\n\t\t(effects (font (size 1 1) (thickness 0.15))))')
    for i, name in enumerate(OLED_PIN_NAMES):
        x = (i - 1.5) * 2.54
        shape = "rect" if i == 0 else "circle"
        out.append(f'\t(pad "{i + 1}" thru_hole {shape} (at {x:.2f} {OLED_PINS_Y:.2f}) (size 1.7 1.7) (drill 1.0)\n'
                   '\t\t(layers "*.Cu" "*.Mask") (remove_unused_layers no))')
        out.append(f'\t(fp_text user "{name}" (at {x:.2f} {OLED_PINS_Y + 2.0:.2f} 90) (layer "F.Fab")\n\t\t(effects (font (size 0.6 0.6) (thickness 0.1))))')
    for x, y in OLED_HOLES:                                                            # M2.5 spacers
        out.append(f'\t(pad "" np_thru_hole circle (at {x:.2f} {y:.2f}) (size 2.7 2.7) (drill 2.7)\n\t\t(layers "*.Cu" "*.Mask"))')
    out += ['\t(embedded_fonts no)', ')', '']
    return "\n".join(out)


def main():
    (PANEL / "OctopusPanel.pretty").mkdir(parents=True, exist_ok=True)
    (PANEL / "OctopusPanel.pretty" / "CTS_228CMV_RGB.kicad_mod").unlink(missing_ok=True)   # replaced by the B3W-9
    (PANEL / "OctopusPanel.pretty" / f"{FP_NAME}.kicad_mod").write_text(footprint(), encoding="utf-8")
    (PANEL / "OctopusPanel.pretty" / f"{OLED_FP}.kicad_mod").write_text(oled_footprint(), encoding="utf-8")
    lib = ['(kicad_symbol_lib', '\t(version 20251024)', '\t(generator "kicad_symbol_editor")',
           '\t(generator_version "10.0")', symbol_block(SYMBOL_NAME), '\t(embedded_fonts no)', ')', '']
    (PANEL / "OctopusPanel.kicad_sym").write_text("\n".join(lib), encoding="utf-8")
    print("wrote panel symbol + footprint")


if __name__ == "__main__":
    main()
