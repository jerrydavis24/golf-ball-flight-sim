"""Command-line interface.

Examples:
    python -m golfsim --club driver
    python -m golfsim --speed 160 --launch 12 --spin 2800 --side-spin 600
    python -m golfsim --club 7-iron --altitude 1600 --wind 10 --wind-from 0
    python -m golfsim --compare-clubs --plot
"""

from __future__ import annotations

import argparse

from .clubs import CLUB_PRESETS
from .physics import Conditions, Shot, simulate


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="golfsim",
                                description="Simulate golf ball flight.")
    p.add_argument("--club", choices=CLUB_PRESETS.keys(),
                   help="Use tour-average launch conditions for a club.")
    p.add_argument("--speed", type=float, help="Ball speed (mph)")
    p.add_argument("--launch", type=float, help="Launch angle (deg)")
    p.add_argument("--spin", type=float, help="Backspin (rpm)")
    p.add_argument("--side-spin", type=float, default=0.0,
                   help="Side spin (rpm), + curves right")
    p.add_argument("--direction", type=float, default=0.0,
                   help="Start direction (deg), + right of target")
    p.add_argument("--altitude", type=float, default=0.0,
                   help="Altitude (m). Albuquerque is about 1600.")
    p.add_argument("--temp", type=float, default=15.0, help="Temperature (C)")
    p.add_argument("--wind", type=float, default=0.0, help="Wind speed (mph)")
    p.add_argument("--wind-from", type=float, default=0.0,
                   help="Wind from (deg): 0 head, 180 tail, 90 from right")
    p.add_argument("--compare-clubs", action="store_true",
                   help="Simulate every preset club.")
    p.add_argument("--plot", action="store_true", help="Show trajectory plot")
    p.add_argument("--save", help="Save the plot to this image path")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    conditions = Conditions(altitude_m=args.altitude, temp_c=args.temp,
                            wind_speed_mph=args.wind,
                            wind_from_deg=args.wind_from)

    shots: dict[str, Shot] = {}
    if args.compare_clubs:
        shots = dict(CLUB_PRESETS)
    elif args.club:
        base = CLUB_PRESETS[args.club]
        shots[args.club] = Shot(base.ball_speed_mph, base.launch_angle_deg,
                                base.back_spin_rpm, args.side_spin,
                                args.direction)
    elif None not in (args.speed, args.launch, args.spin):
        shots["custom"] = Shot(args.speed, args.launch, args.spin,
                               args.side_spin, args.direction)
    else:
        build_parser().error("Use --club, --compare-clubs, or all of "
                             "--speed, --launch and --spin.")

    results = {name: simulate(shot, conditions) for name, shot in shots.items()}

    header = f"{'Shot':<10}" + "".join(f"{k:>21}" for k in
                                       next(iter(results.values())).summary)
    print(header)
    print("-" * len(header))
    for name, r in results.items():
        print(f"{name:<10}" + "".join(f"{v:>21}" for v in r.summary.values()))

    if args.plot or args.save:
        from .plotting import plot_shots
        plot_shots(results, save_path=args.save, show=args.plot)


if __name__ == "__main__":
    main()
