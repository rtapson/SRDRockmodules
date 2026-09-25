"""Checks the button board against the case model in Octopus/case/*.step.

Needs:  pip install cadquery-ocp matplotlib numpy   (plain CPython, not KiCad's Python)
Run:    python tools/case_fit.py

Writes panel/build/case_fit_side.png (side section through the right-hand button
column: case solids, board, switch and both usable cap styles) and prints whether the
board's plane inside the groove is clear of case material. Geometry constants come
from gen_panel_pcb.py's docstring / measured values; case frame is x across,
y front->back, z up (mm).
"""
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from OCP.BRepClass3d import BRepClass3d_SolidClassifier  # noqa: E402
from OCP.gp import gp_Pnt  # noqa: E402
from OCP.IFSelect import IFSelect_RetDone  # noqa: E402
from OCP.STEPControl import STEPControl_Reader  # noqa: E402
from OCP.TopAbs import TopAbs_IN, TopAbs_ON  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
CASE = ROOT / "case"
OUT = ROOT / "panel" / "build"

# groove / board (see gen_panel_pcb.py)
GROOVE_FRONT, GROOVE_BACK = -60.96, -58.93
BOARD_X, BOARD_Z = (-105.48, 105.48), (2.47, 40.84)
BOARD_T = 1.6
# buttons: right-hand column (4/8) in case coordinates; rows from the 1.75" panel
PANEL_X0, PANEL_Z1, PANEL_FRONT = -108.12, 43.31, -72.23
BUTTON_X = 8.5 * 25.4 - 25.4 + PANEL_X0
ROWS_Z = [PANEL_Z1 - (44.45 / 2 - 7.62), PANEL_Z1 - (44.45 / 2 + 7.62)]
SWITCH_H, SWITCH_W, HOLE = 7.2, 7.2, 8.0
CAPS = {"A (round, 3.5 mm)": (3.5, 7.3), "D (cylinder, 9.4 mm)": (9.4, 7.4)}


def load(name):
    r = STEPControl_Reader()
    if r.ReadFile(str(CASE / f"{name}.step")) != IFSelect_RetDone:
        raise RuntimeError(f"cannot read {name}.step")
    r.TransferRoots()
    return BRepClass3d_SolidClassifier(r.OneShape())


PARTS = {n: load(n) for n in ("Bottom", "Top", "FrontPanel")}
CODE = {"Bottom": 1, "Top": 2, "FrontPanel": 3}


def solid_at(x, y, z):
    for name, c in PARTS.items():
        c.Perform(gp_Pnt(x, y, z), 1e-4)
        if c.State() in (TopAbs_IN, TopAbs_ON):
            return CODE[name]
    return 0


def check_groove_plane():
    mid = (GROOVE_FRONT + GROOVE_BACK) / 2
    hits = [(x, z) for x in np.arange(BOARD_X[0], BOARD_X[1], 0.5)
            for z in np.arange(BOARD_Z[0], BOARD_Z[1], 0.5) if solid_at(x, mid, z)]
    slack = (GROOVE_BACK - GROOVE_FRONT) - BOARD_T
    print(f"groove {GROOVE_BACK - GROOVE_FRONT:.2f} mm for a {BOARD_T} mm board ({slack:.2f} mm play); "
          f"board plane: {'CLEAR' if not hits else f'{len(hits)} samples hit case material, e.g. {hits[:3]}'}")


def side_section():
    board_front = GROOVE_BACK - BOARD_T      # board pushed back, as when a button is pressed
    ys, zs = np.arange(-80.0, -52.0, 0.1), np.arange(-2.0, 45.0, 0.1)
    img = np.array([[solid_at(BUTTON_X, y, z) for y in ys] for z in zs])
    for z in ROWS_Z:                         # cap holes aren't in the panel model yet
        img[(np.abs(zs - z) < HOLE / 2)[:, None] & ((ys > PANEL_FRONT) & (ys < -69.8))[None, :] & (img == 3)] = 0
    fig, axes = plt.subplots(1, len(CAPS), figsize=(14, 7), sharey=True)
    for ax, (name, (cap_h, cap_d)) in zip(axes, CAPS.items()):
        ax.imshow(img, origin="lower", extent=[ys[0], ys[-1], zs[0], zs[-1]], cmap="tab10", vmin=0, vmax=9,
                  aspect="equal", interpolation="nearest")
        ax.add_patch(Rectangle((board_front, BOARD_Z[0]), BOARD_T, BOARD_Z[1] - BOARD_Z[0], color="darkgreen"))
        for z in ROWS_Z:
            ax.add_patch(Rectangle((board_front - SWITCH_H, z - SWITCH_W / 2), SWITCH_H, SWITCH_W, color="black"))
            ax.add_patch(Rectangle((board_front - SWITCH_H - cap_h, z - cap_d / 2), cap_h, cap_d, color="tab:olive"))
        proud = PANEL_FRONT - (board_front - SWITCH_H - cap_h)
        ax.set_title(f"cap {name}: top {abs(proud):.1f} mm {'proud of' if proud > 0 else 'behind'} the panel face")
        ax.set_xlabel("y (mm)   <- front ... back ->")
        print(f"cap {name}: {abs(proud):.1f} mm {'proud of' if proud > 0 else 'behind'} the panel face")
    axes[0].set_ylabel("z (mm)")
    fig.suptitle(f"Section at x={BUTTON_X:.2f} (buttons 4/8): orange=Bottom, green=Top, red=FrontPanel, "
                 "dark green=button board")
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "case_fit_side.png", dpi=110)
    print("wrote", OUT / "case_fit_side.png")


if __name__ == "__main__":
    check_groove_plane()
    side_section()
