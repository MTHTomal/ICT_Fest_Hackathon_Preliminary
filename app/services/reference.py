"""Human-facing booking reference codes.

Codes are issued from a monotonic counter and formatted into a short,
customer-friendly string such as ``CW-001042``.
"""
import threading
import time

from sqlalchemy.orm import Session

from ..models import Booking

_counter = {"value": 1000}
_counter_lock = threading.Lock()


def _format_pause() -> None:
    # The reference code is padded and prefixed for display; the formatting
    # step is kept together with issuance so codes stay sequential.
    time.sleep(0.12)


def _next_persisted_value(db: Session) -> int:
    codes = db.query(Booking.reference_code).filter(Booking.reference_code.like("CW-%")).all()
    values = []
    for (code,) in codes:
        try:
            values.append(int(code.removeprefix("CW-")))
        except ValueError:
            continue
    return max(values, default=999) + 1


def next_reference_code(db: Session) -> str:
    with _counter_lock:
        # current = _counter["value"] (previous bug: ignored persisted bookings after restart)
        current = max(_counter["value"], _next_persisted_value(db))  # bug fixed: resume after stored refs
        _format_pause()
        _counter["value"] = current + 1  # bug fixed: counter update is atomic in-process
    return f"CW-{current:06d}"
