"""Owner-controlled device contribution guardrails.

This is a policy decision helper. It does not measure hardware sensors, enforce
OS-level quotas, stop processes, or prove that reported telemetry is truthful.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class DeviceConditions:
    battery_percent: float
    temperature_c: float
    estimated_power_watts: float
    minute_of_week: int
    network_bps_available: int

    def __post_init__(self) -> None:
        values = (self.battery_percent, self.temperature_c, self.estimated_power_watts)
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
               for value in values):
            raise ValueError("device_condition_values_must_be_finite_numbers")
        if not 0 <= self.battery_percent <= 100 or self.estimated_power_watts < 0:
            raise ValueError("invalid_battery_or_power_value")
        if isinstance(self.minute_of_week, bool) or not isinstance(self.minute_of_week, int):
            raise ValueError("minute_of_week_must_be_integer")
        if not 0 <= self.minute_of_week < 10080:
            raise ValueError("minute_of_week_out_of_range")
        if (isinstance(self.network_bps_available, bool)
                or not isinstance(self.network_bps_available, int)
                or self.network_bps_available < 0):
            raise ValueError("network_capacity_must_be_nonnegative_integer")


@dataclass(frozen=True)
class DeviceContributionPolicy:
    enabled: bool = False
    minimum_battery_percent: float = 40.0
    maximum_temperature_c: float = 42.0
    maximum_power_watts: float = 5.0
    maximum_network_bps: int = 0
    remaining_energy_wh: float = 0.0
    allowed_windows: tuple[tuple[int, int], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled_must_be_boolean")
        numeric = (self.minimum_battery_percent, self.maximum_temperature_c,
                   self.maximum_power_watts, self.remaining_energy_wh)
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
               for value in numeric):
            raise ValueError("policy_values_must_be_finite_numbers")
        if not 0 <= self.minimum_battery_percent <= 100:
            raise ValueError("minimum_battery_out_of_range")
        if self.maximum_power_watts < 0 or self.remaining_energy_wh < 0:
            raise ValueError("power_and_energy_limits_must_be_nonnegative")
        if isinstance(self.maximum_network_bps, bool) or not isinstance(self.maximum_network_bps, int) or self.maximum_network_bps < 0:
            raise ValueError("network_limit_must_be_nonnegative_integer")
        for start, end in self.allowed_windows:
            if (isinstance(start, bool) or isinstance(end, bool)
                    or not isinstance(start, int) or not isinstance(end, int)
                    or not 0 <= start < 10080 or not 0 <= end < 10080 or start == end):
                raise ValueError("invalid_weekly_contribution_window")

    def permits(self, conditions: DeviceConditions, estimated_duration_hours: float) -> tuple[bool, str]:
        if isinstance(estimated_duration_hours, bool) or not isinstance(estimated_duration_hours, (int, float)):
            raise ValueError("duration_must_be_positive_finite_number")
        if not math.isfinite(estimated_duration_hours) or estimated_duration_hours <= 0:
            raise ValueError("duration_must_be_positive_finite_number")
        if not self.enabled:
            return False, "contribution_not_enabled"
        if conditions.battery_percent < self.minimum_battery_percent:
            return False, "battery_below_owner_threshold"
        if conditions.temperature_c > self.maximum_temperature_c:
            return False, "device_temperature_above_limit"
        if conditions.estimated_power_watts > self.maximum_power_watts:
            return False, "power_above_owner_limit"
        if conditions.network_bps_available < self.maximum_network_bps:
            return False, "insufficient_network_capacity"
        if not any(
            (start <= conditions.minute_of_week < end) if start < end
            else (conditions.minute_of_week >= start or conditions.minute_of_week < end)
            for start, end in self.allowed_windows
        ):
            return False, "outside_owner_schedule"
        energy_required = conditions.estimated_power_watts * estimated_duration_hours
        if energy_required > self.remaining_energy_wh:
            return False, "energy_budget_exhausted"
        return True, "permitted"
