"""Routine clock (ticks, days) and life clock (years). One compression, stated in SPEC §2."""


def delta_years(cfg) -> float:
    """Life-years elapsed per routine day."""
    return 1.0 / cfg.days_per_year


def age_after_day(age_years: float, cfg) -> float:
    return age_years + delta_years(cfg)


def is_night(tick: int, cfg) -> bool:
    return tick < cfg.night_ticks
