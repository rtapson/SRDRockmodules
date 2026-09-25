"""Keeps the generator scripts from overwriting files that have been edited by hand.

Every generator calls check() with the files it is about to (re)write before it touches
any of them, and record() after writing them. record() stores a fingerprint of each file
in tools/generated.json (committed with the project); check() refuses -- and changes
nothing -- if any target has changed since, i.e. someone edited it in KiCad, or if it
exists with no fingerprint at all. Pass --force to a generator to overwrite anyway.

Fingerprints ignore line endings, so git converting LF/CRLF on checkout doesn't count as
an edit.

    python tools/guard.py --status      list every tracked file: unchanged / EDITED / missing
    python tools/guard.py --adopt       fingerprint the generated files as they are now
                                        (only when you know they're untouched generator output)

Plain Python, so it runs under KiCad's bundled Python as well.
"""
import hashlib
import json
import pathlib
import sys

PROJ = pathlib.Path(__file__).resolve().parent.parent       # Octopus/
STAMPS = PROJ / "tools" / "generated.json"
FORCE = "--force" in sys.argv

# Everything the generators write (relative to Octopus/), for --adopt and --status.
GENERATED = [
    "Octopus.kicad_sch", "Octopus.kicad_sym", "sym-lib-table", "Octopus.kicad_pcb",
    "Octopus.pretty/Teensy41_Socketed.kicad_mod",
    "Octopus.pretty/Jack_6.35mm_Switchcraft_RN111PC_Horizontal.kicad_mod",
    "Octopus.pretty/Jack_6.35mm_Switchcraft_RN112BPC_Horizontal.kicad_mod",
    "Octopus.pretty/DIN-5_180deg_Cliff_FM6725_Horizontal.kicad_mod",
    "panel/OctopusPanel.kicad_sch", "panel/OctopusPanel.kicad_sym", "panel/OctopusPanel.kicad_pcb",
    "panel/fp-lib-table", "panel/sym-lib-table",
    "panel/OctopusPanel.pretty/Omron_B3W-9_2LED_10x10.kicad_mod",
    "panel/OctopusPanel.pretty/OLED_Winstar_WEA012864D-03.kicad_mod",
]


def _key(path):
    return pathlib.Path(path).resolve().relative_to(PROJ).as_posix()


def _digest(path):
    data = pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _load():
    return json.loads(STAMPS.read_text(encoding="utf-8")) if STAMPS.exists() else {}


def _save(stamps):
    STAMPS.write_text(json.dumps(dict(sorted(stamps.items())), indent=1) + "\n", encoding="utf-8")


def changed(paths):
    """The subset of paths that exist but differ from (or have no) recorded fingerprint."""
    stamps = _load()
    out = []
    for p in paths:
        p = pathlib.Path(p)
        if p.exists() and stamps.get(_key(p)) != _digest(p):
            out.append(p)
    return out


def check(*paths):
    """Stop the calling generator before it overwrites anything edited since it last ran."""
    bad = changed(paths)
    if not bad or FORCE:
        if bad:
            print("--force: overwriting hand-edited " + ", ".join(_key(p) for p in bad))
        return
    script = pathlib.Path(sys.argv[0]).name
    print(f"{script}: not overwriting these files, which have changed since the generators last wrote them")
    print("(edited in KiCad?):")
    for p in bad:
        print("   ", _key(p))
    print("Nothing was written. Run with --force to overwrite them anyway (their edits will be lost).")
    sys.exit(1)


def record(*paths):
    """Fingerprint files the calling generator has just written."""
    stamps = _load()
    for p in paths:
        if pathlib.Path(p).exists():
            stamps[_key(p)] = _digest(p)
    _save(stamps)


def forget(*paths):
    """Drop fingerprints of files a generator deleted."""
    stamps = _load()
    for p in paths:
        stamps.pop(_key(p), None)
    _save(stamps)


if __name__ == "__main__":
    if "--adopt" in sys.argv:
        record(*(PROJ / f for f in GENERATED))
        print(f"fingerprinted {sum((PROJ / f).exists() for f in GENERATED)} files in {_key(STAMPS)}")
    else:
        stamps = _load()
        for f in GENERATED:
            p = PROJ / f
            state = "missing" if not p.exists() else "unchanged" if stamps.get(f) == _digest(p) else "EDITED"
            print(f"  {state:9s} {f}")
