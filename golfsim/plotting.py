"""Trajectory plots: side view (height vs. distance) and top-down view."""

from __future__ import annotations

import matplotlib.pyplot as plt

from .physics import FlightResult, M_TO_FT, M_TO_YD


def plot_shots(results: dict[str, FlightResult], title: str = "Ball Flight",
               save_path: str | None = None, show: bool = True):
    fig, (side, top) = plt.subplots(2, 1, figsize=(10, 8),
                                    gridspec_kw={"height_ratios": [2, 1]})

    for label, r in results.items():
        x = r.positions[:, 0] * M_TO_YD
        y = r.positions[:, 1] * M_TO_FT
        z = r.positions[:, 2] * M_TO_YD
        line, = side.plot(x, y, linewidth=2,
                          label=f"{label}  ({r.carry_yd:.0f} yd carry)")
        top.plot(x, z, linewidth=2, color=line.get_color())
        top.plot(x[-1], z[-1], "o", color=line.get_color())

    side.set_title(title)
    side.set_xlabel("Distance (yd)")
    side.set_ylabel("Height (ft)")
    side.set_ylim(bottom=0)
    side.grid(alpha=0.3)
    side.legend(loc="upper left")

    top.axhline(0, color="gray", linestyle="--", linewidth=1)
    top.set_xlabel("Distance (yd)")
    top.set_ylabel("Offline (yd)\n+ right / - left")
    top.grid(alpha=0.3)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    if show:
        plt.show()
    return fig
