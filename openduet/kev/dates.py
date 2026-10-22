"""Deterministic EN/IT due dates, ported from the original commitment engine."""

import calendar
import re
from datetime import date, datetime, timedelta

DUE_HOUR = 18

_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    "lunedi": 0,
    "lunedì": 0,
    "martedi": 1,
    "martedì": 1,
    "mercoledi": 2,
    "mercoledì": 2,
    "giovedi": 3,
    "giovedì": 3,
    "venerdi": 4,
    "venerdì": 4,
    "sabato": 5,
    "domenica": 6,
}
_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
    "gennaio": 1,
    "febbraio": 2,
    "marzo": 3,
    "aprile": 4,
    "maggio": 5,
    "giugno": 6,
    "luglio": 7,
    "agosto": 8,
    "settembre": 9,
    "ottobre": 10,
    "novembre": 11,
    "dicembre": 12,
}
_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "un": 1,
    "uno": 1,
    "due": 2,
    "tre": 3,
    "quattro": 4,
    "cinque": 5,
}


def _next_weekday(start: date, weekday: int) -> date:
    days = (weekday - start.weekday()) % 7
    return start + timedelta(days=days or 7)


def _this_friday(start: date) -> date:
    return start + timedelta(days=max(0, 4 - start.weekday()))


def due_from_text(text: str, sent: datetime) -> datetime | None:
    """The deadline a sentence states, relative to when it was sent, at the
    end of the working day. None when it states none."""
    t = text.lower()
    day = sent.date()
    found: date | None = None

    def at(d: date) -> datetime:
        return datetime(d.year, d.month, d.day, DUE_HOUR, 0)

    if re.search(r"\b(dopodomani|day after tomorrow)\b", t):
        found = day + timedelta(days=2)
    elif re.search(r"\b(domani|tomorrow)\b", t):
        found = day + timedelta(days=1)
    elif re.search(
        r"\b(oggi|stasera|entro sera|today|tonight|this evening|asap|subito|right away|a breve|in giornata)\b",
        t,
    ):
        found = day
    elif m := re.search(
        r"\b(?:in|tra|fra|entro|within)\s+(\d+|one|two|three|four|five|un|uno|due|tre|quattro|cinque)\s+(days?|giorni|giorno|weeks?|settimane|settimana)\b",
        t,
    ):
        n = int(m.group(1)) if m.group(1).isdigit() else _NUMBERS[m.group(1)]
        found = day + timedelta(days=n * (7 if m.group(2).startswith(("week", "settiman")) else 1))
    elif re.search(r"\b(next week|la prossima settimana|settimana prossima|la settimana prossima)\b", t):
        found = _this_friday(day) + timedelta(days=7)
    elif re.search(
        r"\b(end of the week|this week|by the weekend|fine settimana|entro la settimana|questa settimana|in settimana)\b",
        t,
    ):
        found = _this_friday(day)
    elif re.search(r"\b(end of the month|fine mese|entro il mese|this month)\b", t):
        found = date(day.year, day.month, calendar.monthrange(day.year, day.month)[1])
    else:
        for name, weekday in _WEEKDAYS.items():
            if re.search(rf"\b{name}\b", t):
                found = _next_weekday(day, weekday)
                break
        if found is None:
            found = _explicit_date(t, day)
    return at(found) if found else None


def _explicit_date(t: str, day: date) -> date | None:
    candidate: date | None = None
    if m := re.search(r"\b(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?\b", t):
        d, mo = int(m.group(1)), int(m.group(2))
        y = int(m.group(3)) + (2000 if m.group(3) and len(m.group(3)) == 2 else 0) if m.group(3) else day.year
        candidate = _safe_date(y, mo, d)
    else:
        month_names = "|".join(sorted(_MONTHS, key=len, reverse=True))
        if m := re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({month_names})\b", t):
            candidate = _safe_date(day.year, _MONTHS[m.group(2)], int(m.group(1)))
        elif m := re.search(rf"\b({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", t):
            candidate = _safe_date(day.year, _MONTHS[m.group(1)], int(m.group(2)))
        elif m := re.search(r"\b(?:the|il|entro il)\s+(\d{1,2})(?:st|nd|rd|th)?\b", t):
            candidate = _safe_date(day.year, day.month, int(m.group(1)))
            if candidate and candidate < day:
                next_month = day.month % 12 + 1
                candidate = _safe_date(day.year + (day.month == 12), next_month, int(m.group(1)))
    if candidate and candidate < day:
        candidate = _safe_date(candidate.year + 1, candidate.month, candidate.day)
    return candidate


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


# ---------------------------------------------------------------- finding promises
