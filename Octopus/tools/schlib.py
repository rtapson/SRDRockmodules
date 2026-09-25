"""Small helper library for generating KiCad 10 schematics as text.

Same conventions as gen_schematic.py (which predates this module): symbols are
copied verbatim from KiCad's installed libraries into the sheet's lib_symbols cache,
every placement is at rotation 0, and a pin's sheet position is (x + lx, y - ly)
because library space is y-up while the sheet is y-down.

Connections are made with short wire stubs ending in a net label (or a power
symbol), pointed away from the symbol body, so no two nets ever share a wire corner.
"""
import pathlib
import re
import uuid

LIBDIR = pathlib.Path(r"C:/Program Files/KiCad/10.0/share/kicad/symbols")


def _extract_symbol_block(text, name):
    start = text.find(f'\t(symbol "{name}"\n')
    if start == -1:
        raise ValueError(f"symbol {name} not found")
    depth, i = 0, start
    while True:
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1


def _list_pins(block):
    pins = {}
    for m in re.finditer(r'\(pin (\w+) (\w+)\s*\n?\s*\(at ([\-0-9.]+) ([\-0-9.]+) (\d+)\)', block):
        _, _, x, y, angle = m.groups()
        num = re.search(r'\(number "([^"]*)"', block[m.end():m.end() + 400])
        pins[num.group(1)] = (float(x), float(y), int(angle))
    return pins


# outward direction on the sheet (y down) for a pin whose library angle is given
_OUTWARD = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}
_LABEL_ANGLE = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}


class Sheet:
    def __init__(self, project, sheet_uuid, uuid_ns, footprints, paper="A3", title="", comment=""):
        self.project = project
        self.sheet_uuid = sheet_uuid
        self.uuid_ns = uuid.UUID(uuid_ns)
        self.footprints = footprints
        self.paper, self.title, self.comment = paper, title, comment
        self.cache = {}            # lib_id -> (block text, pins)
        self.items = []            # formatted symbol instances
        self.wires, self.labels, self.no_connects = [], [], []
        self._pwr = 0

    # ------------------------------------------------------------ symbols
    def _stable(self, key):
        return str(uuid.uuid5(self.uuid_ns, key))

    def lib(self, libfile, symname, libid):
        if libid not in self.cache:
            text = (LIBDIR / libfile).read_text(encoding="utf-8")
            block = _extract_symbol_block(text, symname)
            self.cache[libid] = (block.replace(f'\t(symbol "{symname}"', f'\t(symbol "{libid}"', 1), _list_pins(block))
        return self.cache[libid][1]

    def custom(self, libid, block_with_libid_name):
        self.cache[libid] = (block_with_libid_name, _list_pins(block_with_libid_name))

    def place(self, libid, ref, value, x, y, in_bom=True, ref_hidden=False, value_dy=-6):
        """Place a symbol; returns {pin number: (sheet x, sheet y, outward (dx, dy))}."""
        pins = self.cache[libid][1]
        fp = self.footprints.get(libid, "")
        hide = " (hide yes)" if ref_hidden else ""
        L = ["\t(symbol", f'\t\t(lib_id "{libid}")', f"\t\t(at {x:g} {y:g} 0)", "\t\t(unit 1)",
             "\t\t(exclude_from_sim no)", f'\t\t(in_bom {"yes" if in_bom else "no"})', "\t\t(on_board yes)",
             "\t\t(dnp no)", f'\t\t(uuid "{self._stable(ref)}")',
             f'\t\t(property "Reference" "{ref}" (at {x:g} {y + 6:g} 0){hide} (effects (font (size 1.27 1.27))))',
             f'\t\t(property "Value" "{value}" (at {x:g} {y + value_dy:g} 0) (effects (font (size 1.27 1.27))))',
             f'\t\t(property "Footprint" "{fp}" (at {x:g} {y:g} 0) (show_name no) (hide yes) (effects (font (size 1.27 1.27))))']
        for num in pins:
            L.append(f'\t\t(pin "{num}" (uuid "{self._stable(f"{ref}/pin/{num}")}"))')
        L += ["\t\t(instances", f'\t\t\t(project "{self.project}"', f'\t\t\t\t(path "/{self.sheet_uuid}"',
              f'\t\t\t\t\t(reference "{ref}")', "\t\t\t\t\t(unit 1)", "\t\t\t\t)", "\t\t\t)", "\t\t)", "\t)"]
        self.items.append("\n".join(L))
        return {n: (round(x + lx, 4), round(y - ly, 4), _OUTWARD[a]) for n, (lx, ly, a) in pins.items()}

    def power(self, kind, x, y):
        libid = f"power:{kind}"
        self.lib("power.kicad_sym", kind, libid)
        self._pwr += 1
        self.place(libid, f"#PWR{self._pwr:03d}", kind, x, y, ref_hidden=True, value_dy=(-4 if kind == "GND" else 4))

    # ------------------------------------------------------------ connections
    def wire(self, p1, p2):
        if p1 != p2:
            self.wires.append((p1, p2))

    def _stub(self, pin, length):
        x, y, (dx, dy) = pin
        end = (round(x + dx * length, 4), round(y + dy * length, 4))
        self.wire((x, y), end)
        return end, (dx, dy)

    def net(self, pin, name, length=5.08):
        """Stub out of the pin and end it with a local net label."""
        end, d = self._stub(pin, length)
        self.labels.append((name, end[0], end[1], _LABEL_ANGLE[d]))

    def pwr(self, pin, kind, length=5.08):
        """Stub out of the pin and end it with a power symbol (GND, +5V, +3V3, PWR_FLAG...)."""
        end, _ = self._stub(pin, length)
        self.power(kind, *end)
        return end

    def nc(self, pin):
        self.no_connects.append((pin[0], pin[1]))

    # ------------------------------------------------------------ output
    def write(self, path):
        out = ["(kicad_sch", "\t(version 20260306)", '\t(generator "eeschema")', '\t(generator_version "10.0")',
               f'\t(uuid "{self.sheet_uuid}")', f'\t(paper "{self.paper}")',
               "\t(title_block", f'\t\t(title "{self.title}")', f'\t\t(comment 1 "{self.comment}")', "\t)",
               "\t(lib_symbols", "\n".join(t for t, _ in self.cache.values()), "\t)"]
        out += self.items
        for (x1, y1), (x2, y2) in self.wires:
            out.append(f'\t(wire (pts (xy {x1:g} {y1:g}) (xy {x2:g} {y2:g}))\n\t\t(stroke (width 0) (type default)) (uuid "{uuid.uuid4()}"))')
        for x, y in self.no_connects:
            out.append(f'\t(no_connect (at {x:g} {y:g}) (uuid "{uuid.uuid4()}"))')
        for name, x, y, a in self.labels:
            just = "right bottom" if a in (180, 270) else "left bottom"
            out.append(f'\t(label "{name}" (at {x:g} {y:g} {a})\n\t\t(effects (font (size 1.27 1.27)) (justify {just})) (uuid "{uuid.uuid4()}"))')
        out += ["\t(sheet_instances", '\t\t(path "/"', '\t\t\t(page "1")', "\t\t)", "\t)", "\t(embedded_fonts no)", ")", ""]
        pathlib.Path(path).write_text("\n".join(out), encoding="utf-8")
