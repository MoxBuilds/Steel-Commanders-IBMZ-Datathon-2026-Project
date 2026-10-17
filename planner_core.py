"""Calendar parsing and fetching shared by the planner server."""

import re
import urllib.request
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9
    ZoneInfo = None


ISO = "%Y-%m-%dT%H:%M:%S"
WEEKDAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
LOCAL_TZ = None


def set_local_tz(name):
    global LOCAL_TZ
    if ZoneInfo is None:
        raise RuntimeError("Named time zones require Python 3.9 or the backport.")
    LOCAL_TZ = ZoneInfo(name)


def now_local():
    if LOCAL_TZ is None:
        return datetime.now()
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)


def normalise_url(url):
    """Convert webcal URLs to HTTPS for urllib."""
    url = url.strip()
    if url.lower().startswith(("webcal://", "webcals://")):
        return "https://" + url.split("://", 1)[1]
    return url


def _unescape(text):
    return (text.replace("\\n", "\n").replace("\\N", "\n")
            .replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\"))


def _parse_dt(value, params):
    value = value.strip()
    if params.get("VALUE") == "DATE" or (len(value) == 8 and "T" not in value):
        return datetime.strptime(value[:8], "%Y%m%d"), True
    if value.endswith("Z"):
        from datetime import timezone
        dt = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return dt.astimezone(LOCAL_TZ).replace(tzinfo=None) if LOCAL_TZ else \
            dt.astimezone().replace(tzinfo=None), False
    dt = datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
    tzid = params.get("TZID")
    if tzid and ZoneInfo:
        try:
            dt = dt.replace(tzinfo=ZoneInfo(tzid)).astimezone(LOCAL_TZ).replace(tzinfo=None) \
                if LOCAL_TZ else dt.replace(tzinfo=ZoneInfo(tzid)).astimezone().replace(tzinfo=None)
        except Exception:
            pass
    return dt, False


def _unfold(text):
    return re.sub(r"\r?\n[ \t]", "", text).splitlines()


def _split_prop(line):
    head, _, value = line.partition(":")
    parts = head.split(";")
    params = {}
    for part in parts[1:]:
        key, _, val = part.partition("=")
        params[key.upper()] = val.strip('"')
    return parts[0].upper(), params, value


def _parse_rrule(value):
    rule = {}
    for part in value.split(";"):
        key, _, val = part.partition("=")
        rule[key.upper()] = val
    return rule


def _add_months(value, count):
    month = value.month - 1 + count
    year, month = value.year + month // 12, month % 12 + 1
    try:
        return value.replace(year=year, month=month)
    except ValueError:
        return None


def _expand(start, rule, win_start, win_end, until_params):
    """Yield recurrence starts within the requested window."""
    freq = rule.get("FREQ", "")
    interval = int(rule.get("INTERVAL", 1) or 1)
    count = int(rule["COUNT"]) if "COUNT" in rule else None
    until = None
    if "UNTIL" in rule:
        try:
            until, is_date = _parse_dt(rule["UNTIL"], until_params)
            if is_date:
                until += timedelta(days=1) - timedelta(seconds=1)
        except (TypeError, ValueError):
            until = None
    byday = [day[-2:] for day in rule.get("BYDAY", "").split(",") if day]
    produced = 0
    limit = min(win_end, until) if until else win_end

    if freq == "WEEKLY":
        week0 = start - timedelta(days=start.weekday())
        days = sorted(WEEKDAYS.index(day) for day in byday) if byday else [start.weekday()]
        for week in range(3000):
            base = week0 + timedelta(weeks=week * interval)
            if base > limit:
                return
            for weekday in days:
                occurrence = base + timedelta(days=weekday)
                if occurrence > limit:
                    return
                if occurrence < start:
                    continue
                produced += 1
                if count is not None and produced > count:
                    return
                if occurrence >= win_start:
                    yield occurrence
    elif freq in ("DAILY", "MONTHLY", "YEARLY"):
        for index in range(5000):
            if freq == "DAILY":
                occurrence = start + timedelta(days=index * interval)
            elif freq == "MONTHLY":
                occurrence = _add_months(start, index * interval)
            else:
                occurrence = _add_months(start, index * interval * 12)
            if occurrence is None:
                continue
            if occurrence > limit:
                return
            produced += 1
            if count is not None and produced > count:
                return
            if occurrence >= win_start:
                yield occurrence
    elif win_start <= start <= win_end:
        yield start


def parse_ics(text, back_days=60, forward_days=400):
    """Parse an iCalendar feed into event dictionaries with recurrences expanded."""
    now = now_local()
    win_start = now - timedelta(days=back_days)
    win_end = now + timedelta(days=forward_days)
    events, current = [], None
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            current = {"props": {}, "exdates": []}
            continue
        if line == "END:VEVENT" and current is not None:
            events.extend(_finish_event(current, win_start, win_end))
            current = None
            continue
        if current is None or ":" not in line:
            continue
        name, params, value = _split_prop(line)
        if name == "EXDATE":
            for item in value.split(","):
                try:
                    current["exdates"].append(_parse_dt(item, params)[0])
                except (TypeError, ValueError):
                    pass
        else:
            current["props"][name] = (params, value)
    events.sort(key=lambda event: event["start"])
    return events


def _finish_event(raw, win_start, win_end):
    props = raw["props"]
    if "DTSTART" not in props:
        return []
    try:
        start, all_day = _parse_dt(props["DTSTART"][1], props["DTSTART"][0])
        if "DTEND" in props:
            end, _ = _parse_dt(props["DTEND"][1], props["DTEND"][0])
        else:
            end = start + (timedelta(days=1) if all_day else timedelta(hours=1))
    except (TypeError, ValueError):
        return []
    duration = end - start

    def text(key):
        return _unescape(props[key][1]).strip() if key in props else ""

    base = {
        "uid": text("UID"),
        "title": text("SUMMARY") or "(untitled)",
        "location": text("LOCATION"),
        "description": text("DESCRIPTION"),
        "all_day": all_day,
    }
    if "RRULE" in props:
        starts = _expand(start, _parse_rrule(props["RRULE"][1]), win_start, win_end,
                         props["DTSTART"][0])
    else:
        starts = [start] if win_start - duration <= start <= win_end else []
    excluded = set(raw["exdates"])
    return [
        {**base, "start": occurrence.strftime(ISO),
         "end": (occurrence + duration).strftime(ISO)}
        for occurrence in starts if occurrence not in excluded
    ]


def fetch_timetable(url, headers=None, timeout=20, opener=None):
    request = urllib.request.Request(normalise_url(url), headers={
        "User-Agent": "StudentPlanner/1.0 (+tkinter)",
        "Accept": "text/calendar, text/plain, */*",
        **(headers or {}),
    })
    open_url = opener.open if opener is not None else urllib.request.urlopen
    with open_url(request, timeout=timeout) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
    content = raw.decode(charset, errors="replace")
    if "BEGIN:VCALENDAR" not in content:
        raise ValueError("The URL did not return an iCalendar (.ics) feed. "
                         "You may need to log in or use the 'subscribe/export' link.")
    return parse_ics(content)
