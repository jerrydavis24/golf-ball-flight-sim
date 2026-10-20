"""Core golf ball flight physics.

The ball is modeled as a point mass acted on by three forces:

* gravity
* aerodynamic drag, opposite the ball's velocity relative to the air
* Magnus lift, perpendicular to both the velocity and the spin axis

The equations of motion are integrated with a fixed-step 4th-order
Runge-Kutta (RK4) solver until the ball returns to the ground.

Coordinate system (right-handed, meters):
    x -> downrange (toward the target)
    y -> up
    z -> right of the target line (positive z = ball finishing right)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# --- Physical constants -----------------------------------------------------

GRAVITY = 9.81                 # m/s^2
BALL_MASS = 0.04593            # kg  (USGA max: 45.93 g)
BALL_DIAMETER = 0.04267        # m   (USGA min: 42.67 mm)
BALL_RADIUS = BALL_DIAMETER / 2
BALL_AREA = math.pi * BALL_RADIUS ** 2

SEA_LEVEL_DENSITY = 1.225      # kg/m^3 at 15 C
SPIN_DECAY_RATE = 0.04         # fraction of spin lost per second (approx.)

MPH_TO_MS = 0.44704
RPM_TO_RADS = 2 * math.pi / 60
M_TO_YD = 1.0936133
M_TO_FT = 3.2808399


def air_density(altitude_m: float = 0.0, temp_c: float = 15.0) -> float:
    """Air density from altitude and temperature (ISA barometric formula)."""
    temp_k = temp_c + 273.15
    pressure = 101325 * (1 - 2.25577e-5 * altitude_m) ** 5.25588  # Pa
    return pressure / (287.05 * temp_k)


def drag_coefficient(spin_factor: float) -> float:
    """Drag coefficient as a function of spin factor S = r*omega/v.

    A dimpled ball in the normal flight regime has Cd near 0.22-0.35,
    rising as spin increases. Coefficients were fit to TrackMan PGA Tour
    averages for driver, 7-iron, and pitching wedge (see README).
    """
    return 0.21 + 0.30 * spin_factor


def lift_coefficient(spin_factor: float) -> float:
    """Lift coefficient as a function of spin factor.

    Lift rises quickly at low spin factors, then saturates near 0.32,
    matching the shape of published wind-tunnel data for golf balls.
    """
    return 0.32 * (1 - math.exp(-spin_factor / 0.13))


# --- Inputs and outputs ---------------------------------------------------

@dataclass
class Shot:
    """Launch conditions measured off the clubface (launch monitor style)."""

    ball_speed_mph: float
    launch_angle_deg: float
    back_spin_rpm: float
    side_spin_rpm: float = 0.0       # + curves right (fade/slice), - curves left
    launch_direction_deg: float = 0.0  # + starts right of target


@dataclass
class Conditions:
    """Atmosphere and wind."""

    altitude_m: float = 0.0
    temp_c: float = 15.0
    wind_speed_mph: float = 0.0
    # Direction the wind blows FROM, in degrees: 0 = headwind, 180 = tailwind,
    # 90 = from the right (pushes ball left), 270 = from the left.
    wind_from_deg: float = 0.0

    def wind_vector(self) -> np.ndarray:
        speed = self.wind_speed_mph * MPH_TO_MS
        theta = math.radians(self.wind_from_deg)
        # Wind blowing from angle theta moves air toward theta + 180.
        return np.array([-speed * math.cos(theta), 0.0, -speed * math.sin(theta)])


@dataclass
class FlightResult:
    times: np.ndarray            # s
    positions: np.ndarray        # (N, 3) meters
    velocities: np.ndarray       # (N, 3) m/s
    carry_yd: float = 0.0
    apex_ft: float = 0.0
    offline_yd: float = 0.0      # + right of target line
    flight_time_s: float = 0.0
    landing_angle_deg: float = 0.0
    summary: dict = field(default_factory=dict)


# --- Simulation -----------------------------------------------------------

def _spin_vector(shot: Shot) -> np.ndarray:
    """Spin vector in rad/s.

    Backspin is rotation about the -z axis (top of ball moving back toward
    the golfer), which produces upward lift for a ball moving in +x.
    Side spin is rotation about the vertical axis: positive side spin
    produces a lift component toward +z (curving right).
    """
    back = shot.back_spin_rpm * RPM_TO_RADS
    side = shot.side_spin_rpm * RPM_TO_RADS
    return np.array([0.0, -side, back])


def _acceleration(vel: np.ndarray, spin: np.ndarray, wind: np.ndarray,
                  rho: float) -> np.ndarray:
    rel_vel = vel - wind
    speed = np.linalg.norm(rel_vel)
    if speed < 1e-9:
        return np.array([0.0, -GRAVITY, 0.0])

    omega = np.linalg.norm(spin)
    spin_factor = BALL_RADIUS * omega / speed

    q = 0.5 * rho * BALL_AREA * speed ** 2      # dynamic pressure * area
    drag = -q * drag_coefficient(spin_factor) * rel_vel / speed

    lift = np.zeros(3)
    if omega > 1e-9:
        direction = np.cross(spin, rel_vel)
        norm = np.linalg.norm(direction)
        if norm > 1e-9:
            lift = q * lift_coefficient(spin_factor) * direction / norm

    gravity = np.array([0.0, -GRAVITY * BALL_MASS, 0.0])
    return (drag + lift + gravity) / BALL_MASS


def simulate(shot: Shot, conditions: Conditions | None = None,
             dt: float = 0.005, max_time: float = 20.0) -> FlightResult:
    """Simulate a shot until it lands. Returns the full trajectory."""
    conditions = conditions or Conditions()
    rho = air_density(conditions.altitude_m, conditions.temp_c)
    wind = conditions.wind_vector()

    speed = shot.ball_speed_mph * MPH_TO_MS
    launch = math.radians(shot.launch_angle_deg)
    direction = math.radians(shot.launch_direction_deg)
    vel = speed * np.array([
        math.cos(launch) * math.cos(direction),
        math.sin(launch),
        math.cos(launch) * math.sin(direction),
    ])
    pos = np.zeros(3)
    spin0 = _spin_vector(shot)

    times, positions, velocities = [0.0], [pos.copy()], [vel.copy()]
    t = 0.0

    def deriv(v: np.ndarray, time: float) -> np.ndarray:
        spin = spin0 * math.exp(-SPIN_DECAY_RATE * time)
        return _acceleration(v, spin, wind, rho)

    while t < max_time:
        # RK4 step for position and velocity.
        k1v = deriv(vel, t)
        k1x = vel
        k2v = deriv(vel + 0.5 * dt * k1v, t + 0.5 * dt)
        k2x = vel + 0.5 * dt * k1v
        k3v = deriv(vel + 0.5 * dt * k2v, t + 0.5 * dt)
        k3x = vel + 0.5 * dt * k2v
        k4v = deriv(vel + dt * k3v, t + dt)
        k4x = vel + dt * k3v

        new_vel = vel + dt / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
        new_pos = pos + dt / 6 * (k1x + 2 * k2x + 2 * k3x + k4x)
        t += dt

        if new_pos[1] < 0 and t > dt:
            # Interpolate to the exact ground crossing.
            frac = pos[1] / (pos[1] - new_pos[1])
            new_pos = pos + frac * (new_pos - pos)
            new_vel = vel + frac * (new_vel - vel)
            t = t - dt + frac * dt
            times.append(t)
            positions.append(new_pos)
            velocities.append(new_vel)
            break

        pos, vel = new_pos, new_vel
        times.append(t)
        positions.append(pos.copy())
        velocities.append(vel.copy())

    return _summarize(np.array(times), np.array(positions), np.array(velocities))


def _summarize(times, positions, velocities) -> FlightResult:
    final_pos = positions[-1]
    final_vel = velocities[-1]
    horizontal = math.hypot(final_vel[0], final_vel[2])
    landing_angle = math.degrees(math.atan2(-final_vel[1], horizontal))

    result = FlightResult(
        times=times,
        positions=positions,
        velocities=velocities,
        carry_yd=float(math.hypot(final_pos[0], final_pos[2]) * M_TO_YD),
        apex_ft=float(positions[:, 1].max() * M_TO_FT),
        offline_yd=float(final_pos[2] * M_TO_YD),
        flight_time_s=float(times[-1]),
        landing_angle_deg=landing_angle,
    )
    result.summary = {
        "Carry (yd)": round(result.carry_yd, 1),
        "Apex (ft)": round(result.apex_ft, 1),
        "Offline (yd)": round(result.offline_yd, 1),
        "Flight time (s)": round(result.flight_time_s, 2),
        "Landing angle (deg)": round(result.landing_angle_deg, 1),
    }
    return result
