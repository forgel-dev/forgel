"""DeepSeek peak/off-peak pricing windows.

Peak hours cost twice the off-peak rate. Autonomous work should not spend at
peak rates by default: when the policy is ``off_peak`` and a request would hit
a window, the daemon holds the work and a chat request gets an explanation of
when the window closes and how to override it.

The default windows are DeepSeek's published schedule (01:00-04:00 and
06:00-10:00 UTC on weekdays; weekends are off-peak). ``FORGEL_PEAK_HOURS`` or
``DEEPSEEK_PEAK_HOURS`` overrides them in the form ``1-4,6-10``.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Mapping, Sequence

from .i18n import t as _t
from .model_profiles import default_profile

DEFAULT_HOURS = default_profile().peak_windows
DEFAULT_POLICY = default_profile().peak_policy
POLICIES = {"off_peak", "always"}
UTC = timezone.utc


def _windows(hours: str) -> list[tuple[int, int]]:
    return parse_hours(hours) if hours.strip() else []


def parse_hours(spec: str) -> list[tuple[int, int]]:
    windows: list[tuple[int, int]] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        start, _, end = part.partition("-")
        try:
            a, b = int(start), int(end)
        except ValueError as exc:
            raise ValueError(
                f"invalid peak hours {spec!r}; expected '1-4,6-10'"
            ) from exc
        if not (0 <= a < b <= 24):
            raise ValueError(
                f"invalid peak window {a}-{b}; use 0 <= start < end <= 24"
            )
        windows.append((a, b))
    if not windows:
        raise ValueError("peak hours must not be empty")
    return windows


def hours_from_env(environ: Mapping[str, str] | None = None) -> str:
    env = environ if environ is not None else os.environ
    return (
        env.get("FORGEL_PEAK_HOURS", "").strip()
        or env.get("DEEPSEEK_PEAK_HOURS", "").strip()
        or default_profile().peak_windows
    )


def policy_from_env(environ: Mapping[str, str] | None = None) -> str:
    env = environ if environ is not None else os.environ
    value = env.get("FORGEL_PEAK_POLICY", DEFAULT_POLICY).strip().lower()
    return value or DEFAULT_POLICY


def _in_peak(hour: int, windows: Sequence[tuple[int, int]]) -> bool:
    return any(start <= hour < end for start, end in windows)


def is_off_peak(
    now: datetime | None = None, hours: str = DEFAULT_HOURS
) -> bool:
    moment = now or datetime.now(UTC)
    windows = _windows(hours)
    if not windows or moment.weekday() >= 5:
        return True
    return not _in_peak(moment.hour, windows)


def next_off_peak(
    now: datetime | None = None, hours: str = DEFAULT_HOURS
) -> datetime:
    moment = now or datetime.now(UTC)
    windows = _windows(hours)
    if not windows or is_off_peak(moment, hours):
        return moment
    for delta in range(1, 24 * 8):
        boundary = (moment + timedelta(hours=delta)).replace(
            minute=0, second=0, microsecond=0
        )
        if boundary.weekday() >= 5 or not _in_peak(
            boundary.hour, windows
        ):
            return boundary
    return moment + timedelta(hours=1)


def seconds_until_off_peak(
    now: datetime | None = None, hours: str = DEFAULT_HOURS
) -> float:
    moment = now or datetime.now(UTC)
    return max(0.0, (next_off_peak(moment, hours) - moment).total_seconds())


def next_peak(
    now: datetime | None = None, hours: str = DEFAULT_HOURS
) -> datetime | None:
    moment = now or datetime.now(UTC)
    windows = _windows(hours)
    if not windows:
        return None
    hour = moment.replace(minute=0, second=0, microsecond=0)
    for delta in range(0, 24 * 8):
        candidate = hour + timedelta(hours=delta)
        if candidate <= moment or candidate.weekday() >= 5:
            continue
        if not _in_peak(candidate.hour, windows):
            continue
        previous = candidate - timedelta(hours=1)
        if previous.weekday() < 5 and _in_peak(previous.hour, windows):
            continue
        return candidate
    return None


def local_time(moment: datetime, tz_name: str = "") -> str:
    if not tz_name:
        return ""
    try:
        from zoneinfo import ZoneInfo

        return moment.astimezone(ZoneInfo(tz_name)).strftime("%H:%M")
    except Exception:
        return ""


def humanize(seconds: float) -> str:
    minutes = int(seconds // 60)
    if minutes < 1:
        return "under a minute"
    if minutes < 60:
        return f"{minutes} min"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m" if minutes else f"{hours}h"


def _moment(moment: datetime, tz_name: str) -> str:
    local = local_time(moment, tz_name)
    base = moment.strftime("%H:%M UTC")
    return f"{base} ({local} local)" if local else base


def project_policy(settings: object, control: object) -> str:
    """The project's policy, falling back to the runtime setting."""

    from .project_config import ConfigError, load_project_config

    fallback = str(getattr(settings, "peak_policy", "always"))
    try:
        config = load_project_config(control)  # type: ignore[arg-type]
    except ConfigError:
        config = None
    if config is None:
        return fallback
    return config.models.peak_policy


def should_defer(
    policy: str, now: datetime | None = None, hours: str = DEFAULT_HOURS
) -> bool:
    if policy not in POLICIES:
        raise ValueError(f"unknown peak policy {policy!r}")
    return policy == "off_peak" and not is_off_peak(now, hours)


def windows_text(hours: str = DEFAULT_HOURS) -> str:
    windows = _windows(hours)
    if not windows:
        return "no configured peak windows"
    return ", ".join(
        f"{start:02d}:00-{end:02d}:00 UTC" for start, end in windows
    )


def defer_message(
    now: datetime | None = None,
    hours: str = DEFAULT_HOURS,
    tz_name: str = "",
    lang: str = "en",
) -> str:
    moment = now or datetime.now(UTC)
    boundary = next_off_peak(moment, hours)
    wait = humanize(seconds_until_off_peak(moment, hours))
    return _t(
        lang,
        "peak_defer",
        model=default_profile().display,
        windows=windows_text(hours),
        moment=_moment(boundary, tz_name),
        wait=wait,
    )


def status_text(
    policy: str,
    now: datetime | None = None,
    hours: str = DEFAULT_HOURS,
    tz_name: str = "",
    lang: str = "en",
) -> str:
    moment = now or datetime.now(UTC)
    state = _t(
        lang,
        "peak_state_off_peak"
        if is_off_peak(moment, hours)
        else "peak_state_peak",
    )
    action = _t(
        lang,
        "peak_allowed" if policy == "always" else "peak_deferred",
    )
    boundary = next_off_peak(moment, hours)
    upcoming = next_peak(moment, hours)
    lines = [
        _t(
            lang,
            "peak_policy",
            policy=policy,
            model=default_profile().display,
        ),
        _t(
            lang,
            "peak_now",
            state=state,
            moment=_moment(moment, tz_name),
        ),
        _t(lang, "peak_windows", windows=windows_text(hours)),
        action,
        _t(
            lang,
            "peak_next_off",
            moment=_moment(boundary, tz_name),
            wait=humanize(seconds_until_off_peak(moment, hours)),
        ),
    ]
    if upcoming is not None:
        lines.append(
            _t(
                lang,
                "peak_next",
                moment=_moment(upcoming, tz_name),
            )
        )
    lines.append(_t(lang, "peak_override"))
    return "\n".join(lines)
