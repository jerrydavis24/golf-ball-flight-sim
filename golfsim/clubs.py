"""Preset launch conditions based on TrackMan PGA Tour averages."""

from .physics import Shot

CLUB_PRESETS: dict[str, Shot] = {
    "driver": Shot(ball_speed_mph=171, launch_angle_deg=10.4, back_spin_rpm=2545),
    "3-wood": Shot(ball_speed_mph=162, launch_angle_deg=9.3, back_spin_rpm=3663),
    "5-iron": Shot(ball_speed_mph=135, launch_angle_deg=12.1, back_spin_rpm=5361),
    "7-iron": Shot(ball_speed_mph=123, launch_angle_deg=16.3, back_spin_rpm=7097),
    "9-iron": Shot(ball_speed_mph=112, launch_angle_deg=20.4, back_spin_rpm=8647),
    "pw": Shot(ball_speed_mph=104, launch_angle_deg=24.2, back_spin_rpm=9304),
}

# Published TrackMan PGA Tour average carries, used for validation tests.
TOUR_CARRY_YD = {
    "driver": 282,
    "3-wood": 249,
    "5-iron": 194,
    "7-iron": 176,
    "9-iron": 152,
    "pw": 136,
}
