"""golfsim: a physics-based golf ball flight simulator."""

from .physics import Conditions, FlightResult, Shot, air_density, simulate
from .clubs import CLUB_PRESETS

__all__ = ["Shot", "Conditions", "FlightResult", "simulate", "air_density",
           "CLUB_PRESETS"]
