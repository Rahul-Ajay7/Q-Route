"""
src/traffic/traffic_profiles.py

Synthetic congestion multipliers by hour-of-day. Used as fallback when
real traffic APIs (Google) are unavailable, and as the multiplier applied
on top of OSRM's free-flow duration.
"""


class TrafficProfiles:

    # hour (0-23) -> congestion multiplier vs free-flow
    DEFAULT_PROFILE = {
        0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.05,
        6: 1.2, 7: 1.7, 8: 2.0, 9: 1.6, 10: 1.2, 11: 1.15,
        12: 1.25, 13: 1.2, 14: 1.15, 15: 1.2, 16: 1.4,
        17: 1.9, 18: 2.1, 19: 1.7, 20: 1.3, 21: 1.1,
        22: 1.05, 23: 1.0,
    }

    def __init__(self, profile: dict = None):
        self.profile = profile or self.DEFAULT_PROFILE

    def get_factor(self, hour: int) -> float:
        hour = int(hour) % 24
        return self.profile.get(hour, 1.0)
