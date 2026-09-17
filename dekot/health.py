"""Routine -> biological conversions and mortality (SPEC §6).

Every formula here converts routine-clock tallies (meals, ticks) into a
per-day biological delta, or life-clock quantities (age in years) into an
annual hazard. Do not mix units without an explicit conversion.
"""
import math
from .clock import delta_years


def daily_health_delta(agent, cfg) -> float:
    """Inputs are one routine day's tallies; output is health change for that day."""
    meals = min(agent.meals_eaten, 2)
    rest_needed = cfg.night_ticks
    rest_frac = min(agent.rest_ticks / rest_needed, 1.0)
    overwork = max(agent.work_ticks - (cfg.ticks_per_day - cfg.night_ticks - 2), 0)
    age_decay = cfg.age_decay_k * max(agent.age - 30.0, 0.0)
    return (cfg.food_gain * meals / 2
            - cfg.hunger_loss * (2 - meals)
            + cfg.rest_gain * rest_frac
            - cfg.fatigue_loss * overwork
            + (cfg.milk_gain if agent.milk_drunk >= 1.0 else 0.0)
            - age_decay)


def annual_hazard(age: float, health: float, cfg) -> float:
    """Gompertz age baseline times a health multiplier. Never zero."""
    return cfg.hazard_base * math.exp(cfg.hazard_k * age) * math.exp(cfg.hazard_beta * (50.0 - health) / 50.0)


def p_death(age: float, health: float, cfg) -> float:
    """Probability of death over one routine day. Assumes constant hazard within the step."""
    return 1.0 - math.exp(-annual_hazard(age, health, cfg) * delta_years(cfg))
