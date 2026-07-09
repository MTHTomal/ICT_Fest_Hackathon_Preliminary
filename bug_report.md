# Bug Report

## 1. File: `timeutils.py`

### According to Rule

**Datetimes:** Input datetimes carrying a UTC offset must be converted to UTC before storage or comparison; naive input is treated as UTC.

### Bug

```python
if dt.tzinfo is not None:
    dt = dt.replace(tzinfo=None)
```

### Issue

The code removes the timezone information without first converting the datetime to UTC. As a result, offset-aware datetimes are stored with an incorrect timestamp, leading to incorrect storage and comparison.

### Fixed

```python
if dt.tzinfo is not None:
    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
```

---

## 2. File: `routers/bookings.py`

### According to Rule

**No Double-Booking:** Two confirmed bookings overlap iff `existing.start < new.end AND new.start < existing.end`. Back-to-back bookings are allowed.

### Bug

```python
if b.start_time <= end and start <= b.end_time:
    return True
```

### Issue

Using `<=` incorrectly treats back-to-back bookings as overlapping.

### Fixed

```python
if b.start_time < end and start < b.end_time:
    return True
```

---

## 3. File: `routers/bookings.py`

### According to Rule

**Booking Window:** `start_time` must be strictly in the future at request time. No grace window is allowed.

### Bug

```python
if start <= now - timedelta(seconds=300):
```

### Issue

The implementation allows bookings up to five minutes in the past.

### Fixed

```python
if start <= now:
```

---

## 4. File: `routers/bookings.py`

### According to Rule

**Booking Price:** Duration must be a whole number of hours (minimum 1, maximum 8), and `end_time` must be strictly after `start_time`.

### Bug

```python
if duration_hours > MAX_DURATION_HOURS:
    raise AppError(400, "INVALID_BOOKING_WINDOW", "duration out of range")
```

### Issue

The implementation does not validate that:

* `end_time` is strictly after `start_time`.
* Duration is at least one hour.

### Fixed

```python
if end <= start:
    raise AppError(400, "INVALID_BOOKING_WINDOW", "end_time must be after start_time")

if duration_hours < MIN_DURATION_HOURS or duration_hours > MAX_DURATION_HOURS:
    raise AppError(400, "INVALID_BOOKING_WINDOW", "duration out of range")
```

---

## 5. File: `routers/bookings.py`

### According to Rule

**Pagination & Ordering:** Results must be ordered by ascending `start_time` (ties by ascending `id`). Pagination must not skip or repeat items, and the requested `limit` must be respected.

### Bug

```python
base.order_by(Booking.start_time.desc(), Booking.id.asc()) \
    .offset(page * limit) \
    .limit(10)
```

### Issue

* Sorts in descending order instead of ascending.
* Uses an incorrect offset calculation.
* Ignores the requested `limit`.

### Fixed

```python
base.order_by(Booking.start_time.asc(), Booking.id.asc()) \
    .offset((page - 1) * limit) \
    .limit(limit)
```

---

## 6. File: `routers/bookings.py`

### According to Rule

**Booking Details:** The booking response must return the correct booking fields.

### Bug

```python
response["start_time"] = iso_utc(booking.created_at)
```

### Issue

The booking's `start_time` is overwritten with `created_at`, producing an incorrect response.

### Fixed

Remove the incorrect assignment.

```python
# Remove this line
response["start_time"] = iso_utc(booking.created_at)
```

---

## 7. File: `routers/bookings.py`

### According to Rule

**Cancellation Refund Policy:**

* Notice ≥ 48 hours → 100% refund
* 24 hours ≤ Notice < 48 hours → 50% refund
* Notice < 24 hours → 0% refund

### Bug

```python
if notice_hours > 48:
    refund_percent = 100
elif notice >= timedelta(hours=24):
    refund_percent = 50
else:
    refund_percent = 50
```

### Issue

* Exactly 48 hours receives only a 50% refund.
* Less than 24 hours incorrectly receives a 50% refund instead of 0%.

### Fixed

```python
if notice >= timedelta(hours=48):
    refund_percent = 100
elif notice >= timedelta(hours=24):
    refund_percent = 50
else:
    refund_percent = 0
```

---

## 8. File: `routers/bookings.py`

### According to Rule

**Availability:** Room availability must reflect the current state immediately.

### Bug

```python
cache.invalidate_report(user.org_id)
```

### Issue

The availability cache is not invalidated after cancelling a booking, allowing stale availability data to be returned.

### Fixed

```python
cache.invalidate_report(user.org_id)
cache.invalidate_availability(
    booking.room_id,
    booking.start_time.date().isoformat(),
)
```

---

## 9. File: `routers/auth.py`

### According to Rule

**Registration:** A duplicate username within the organization must return **409 `USERNAME_TAKEN`**.

### Bug

```python
if existing is not None:
    return {
        "user_id": existing.id,
        "org_id": org.id,
        "username": existing.username,
        "role": existing.role,
    }
```

### Issue

Instead of rejecting duplicate usernames, the endpoint returns the existing user's information.

### Fixed

```python
if existing is not None:
    raise AppError(
        409,
        "USERNAME_TAKEN",
        "Username already exists",
    )
```

---

## 10. File: `routers/auth.py`

### According to Rule

**Authentication:** Refresh tokens are single-use. Refreshing must invalidate the presented refresh token.

### Bug

```python
return {
    "access_token": create_access_token(user),
    "refresh_token": create_refresh_token(user),
    "token_type": "bearer",
}
```

### Issue

The refresh endpoint issues a new refresh token without invalidating the one that was just used, allowing refresh token reuse.

### Fixed

Invalidate the presented refresh token (or its `jti`) before issuing a new refresh token. The exact implementation depends on `auth.py`.

---

## 11. File: `services/export.py`

### According to Rule

**Multi-tenancy:** Every code path must enforce organization scoping; cross-org resource IDs behave as non-existent.

### Bug

```python
if include_all:
    if room_id is not None:
        rows = fetch_bookings_raw(db, room_id)
```

### Issue

When `include_all=True` and `room_id` is provided, the export query loads bookings by room ID only. An admin can export bookings from another organization by guessing a cross-org room ID.

### Fixed

```python
if room_id is not None:
    room = db.query(Room).filter(Room.id == room_id, Room.org_id == org_id).first()
    if room is None:
        raise AppError(404, "ROOM_NOT_FOUND", "Room not found")

rows = fetch_bookings_raw(db, org_id, room_id)
```

---

## 12. File: `routers/bookings.py`

### According to Rule

**No Double-Booking:** The no-double-booking guarantee must hold under concurrent requests.

### Bug

```python
if _has_conflict(db, room.id, start, end):
    raise AppError(409, "ROOM_CONFLICT", "Room already booked for this interval")

db.add(booking)
db.commit()
```

### Issue

The conflict check and insert were not protected as one critical section. Two concurrent requests for the same room and overlapping interval could both pass the conflict check before either booking was committed.

### Fixed

```python
with _booking_write_lock:
    if _has_conflict(db, room.id, start, end):
        raise AppError(409, "ROOM_CONFLICT", "Room already booked for this interval")

    db.add(booking)
    db.commit()
```

---

## 13. File: `routers/bookings.py`

### According to Rule

**Booking Quota:** A member may hold at most 3 confirmed bookings in `(now, now + 24h]`, and the rule must hold under concurrent requests.

### Bug

```python
_check_quota(db, user.id, now, start)

db.add(booking)
db.commit()
```

### Issue

Quota checking and booking creation were not atomic. Concurrent requests could all observe the same quota count and then commit more than three bookings in the quota window.

### Fixed

```python
with _booking_write_lock:
    _check_quota(db, user.id, now, start)

    db.add(booking)
    db.commit()
```

---

## 14. File: `services/reference.py` and `models.py`

### According to Rule

**Reference Codes:** Every booking's `reference_code` is unique, including under concurrent creation.

### Bug

```python
current = _counter["value"]
_format_pause()
_counter["value"] = current + 1
```

### Issue

The in-memory counter was read and updated without synchronization, allowing concurrent calls to return the same reference code. The database model also did not enforce uniqueness on `Booking.reference_code`.

### Fixed

```python
with _counter_lock:
    current = _counter["value"]
    _format_pause()
    _counter["value"] = current + 1
```

```python
reference_code = Column(String, nullable=False, unique=True, index=True)
```

---

## 15. File: `services/ratelimit.py`

### According to Rule

**Rate Limit:** `POST /bookings` is limited to 20 requests per rolling 60 seconds per user, and the rule must hold under concurrent requests.

### Bug

```python
bucket = _buckets.get(user_id, [])
bucket = [t for t in bucket if t > now - _WINDOW_SECONDS]
bucket.append(now)
_buckets[user_id] = bucket
```

### Issue

The rate-limit bucket was read, modified, and written without synchronization. Concurrent requests could lose updates and allow more than 20 booking attempts inside the rolling window.

### Fixed

```python
with _bucket_lock:
    bucket = _buckets.get(user_id, [])
    bucket = [t for t in bucket if t > now - _WINDOW_SECONDS]
    bucket.append(now)
    _buckets[user_id] = bucket
```

---

## 16. File: `routers/bookings.py` and `models.py`

### According to Rule

**Cancellation:** Cancelling an already-cancelled booking returns `409 ALREADY_CANCELLED`. A cancelled booking has exactly one `RefundLog` entry.

### Bug

```python
if booking.status == "cancelled":
    raise AppError(409, "ALREADY_CANCELLED", "Booking already cancelled")

log_refund(db, booking, refund_percent)
booking.status = "cancelled"
db.commit()
```

### Issue

The status check, refund log creation, and status update were not protected as one critical section. Two concurrent cancellations could both pass the status check and create duplicate refund logs.

### Fixed

```python
with _booking_write_lock:
    if booking.status == "cancelled":
        raise AppError(409, "ALREADY_CANCELLED", "Booking already cancelled")

    log_refund(db, booking, refund_percent)
    booking.status = "cancelled"
    db.commit()
```

```python
booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, unique=True, index=True)
```

---

## 17. File: `routers/rooms.py`

### According to Rule

**Room Stats:** `/rooms/{id}/stats` must always equal the values derivable from confirmed bookings.

### Bug

```python
current = stats.get(room.id)
return {
    "total_confirmed_bookings": current["count"],
    "total_revenue_cents": current["revenue"],
}
```

### Issue

Room stats were served from a process-local dictionary. The dictionary can be empty after restart or drift from the database under concurrent create/cancel operations.

### Fixed

```python
confirmed_count, revenue_cents = (
    db.query(func.count(Booking.id), func.coalesce(func.sum(Booking.price_cents), 0))
    .filter(Booking.room_id == room.id, Booking.status == "confirmed")
    .one()
)
```

---

## 18. File: `services/notifications.py`

### According to Rule

**Liveness:** No combination of concurrent valid requests may hang the service.

### Bug

```python
def notify_created(booking):
    with _email_lock:
        with _audit_lock:
            ...

def notify_cancelled(booking):
    with _audit_lock:
        with _email_lock:
            ...
```

### Issue

The two notification paths acquired locks in opposite orders. Concurrent create and cancel notifications could deadlock by each holding one lock while waiting for the other.

### Fixed

```python
def notify_cancelled(booking):
    with _email_lock:
        with _audit_lock:
            ...
```

---

## 19. File: `routers/auth.py`

### According to Rule

**Registration:** A duplicate username within the organization must return `409 USERNAME_TAKEN`.

### Bug

```python
existing = db.query(User).filter(...).first()
if existing is not None:
    raise AppError(409, "USERNAME_TAKEN", "Username already exists")

db.add(user)
db.commit()
```

### Issue

The duplicate lookup and insert were not protected against concurrent registration. Two requests could both pass the lookup, and the database unique constraint could raise an unhandled integrity error during commit.

### Fixed

```python
with _registration_lock:
    existing = db.query(User).filter(...).first()
    if existing is not None:
        raise AppError(409, "USERNAME_TAKEN", "Username already exists")

    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "USERNAME_TAKEN", "Username already exists")
```

---

## 20. File: `routers/bookings.py`

### According to Rule

**Booking Visibility:** Members may read and cancel only their own bookings. Another member's booking id must return `404 BOOKING_NOT_FOUND`. Admins may read and cancel any booking in their org.

### Bug

```python
if booking is None:
    raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found")
```

### Issue

The booking details endpoint only checked whether the booking belonged to the user's organization. A non-admin member could read another member's booking details in the same organization.

### Fixed

```python
if booking is None or (user.role != "admin" and booking.user_id != user.id):
    raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found")
```

---

## 21. File: `services/reference.py`

### According to Rule

**Reference Codes:** Every booking's `reference_code` is unique, including under concurrent creation.

### Bug

```python
_counter = {"value": 1000}

def next_reference_code() -> str:
    with _counter_lock:
        current = _counter["value"]
        _counter["value"] = current + 1
```

### Issue

The reference-code counter always started at `1000` in memory. After an app restart with persisted bookings, the generator could reuse an existing code such as `CW-001000`, causing a valid booking request to fail on the unique reference-code constraint.

### Fixed

```python
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
        current = max(_counter["value"], _next_persisted_value(db))
        _counter["value"] = current + 1
    return f"CW-{current:06d}"
```

---

## 22. File: `auth.py` and `models.py`

### According to Rule

**Auth:** Logout immediately invalidates the presented access token for all further use. Refresh tokens are single-use and reuse must return `401`.

### Bug

```python
_revoked_tokens: set[str] = set()
_revoked_refresh_tokens: set[str] = set()
```

### Issue

Access-token revocation and used refresh-token tracking were kept only in process memory. After an app restart with the same database and JWT secret, logged-out access tokens and already-used refresh tokens could become valid again.

### Fixed

```python
class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti = Column(String, primary_key=True)
    token_type = Column(String, nullable=False, index=True)
    expires_at = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
```

```python
def revoke_access_token(payload: dict, db: Session) -> None:
    _persist_revoked_token(db, payload)
    _revoked_tokens.add(payload["jti"])
```

```python
def consume_refresh_token(payload: dict, db: Session) -> bool:
    ...
    if not _persist_revoked_token(db, payload):
        return False
```

---

## 23. File: `routers/admin.py` and `cache.py`

### According to Rule

**Usage Report:** The report must reflect the current state immediately.

### Bug

```python
cached = cache.get_report(admin.org_id, frm, to)
if cached is not None:
    return cached

# query database

cache.set_report(admin.org_id, frm, to, result)
```

### Issue

Report generation and cache writes were not synchronized with cache invalidation. A report request could compute old data, then write that stale result into the cache after a booking or room change had already invalidated the previous cache entry.

### Fixed

```python
def get_or_set_report(org_id: int, frm: str, to: str, build):
    with _report_lock:
        cached = _report_cache.get((org_id, frm, to))
        if cached is not None:
            return cached
        result = build()
        _report_cache[(org_id, frm, to)] = result
        return result
```

```python
return cache.get_or_set_report(
    admin.org_id,
    frm,
    to,
    build_report,
)
```

# 24. File: `app/auth.py`

## According to Rule
**Auth:** Access tokens expire in exactly 900 seconds.

## Bug
```
lifetime = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
```

## Issue
`ACCESS_TOKEN_EXPIRE_MINUTES` is already 15, but the code multiplies it by 60. This makes access tokens expire in 15 hours instead of 15 minutes.

## Fixed
```
lifetime = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
```

This uses the configured access-token lifetime directly, preserving the required 900-second expiry.

---

# 25. File: `app/auth.py`

## According to Rule
**Auth:** Logout immediately invalidates the presented access token; subsequent use must fail with `401`.

## Bug
```
if payload.get("sub") in _revoked_tokens:
```

## Issue
Revoked tokens are stored by their `jti` claim, but the code checks the `sub` claim instead. As a result, revoked access tokens are not rejected.

## Fixed
```
if payload.get("jti") in _revoked_tokens:
```

This checks the actual revoked-token identifier, ensuring logged-out access tokens are invalidated.

---

# 26. Files: `app/routers/bookings.py`, `app/services/refunds.py`

## According to Rule
**Cancellation refund policy:** Refund amount is rounded to the nearest cent with half-cents rounding up, and the cancel response must equal the stored `RefundLog` amount.

## Bug
```
refund_amount_cents = round(booking.price_cents * (refund_percent / 100.0))
```
```
amount_cents = int(refund_dollars * 100)
```

## Issue
`round()` uses bankers rounding on `.5`, and `int()` truncates decimals. For a 50% refund on `1001` cents, this can produce `500` instead of the correct `501`, and the response may differ from the logged refund.

## Fixed
```
refund_amount_cents = (booking.price_cents * refund_percent + 50) // 100
```
```
amount_cents = (booking.price_cents * percent + 50) // 100
```

This uses integer math to round half-cents up consistently, matching cancel response and stored `RefundLog` amounts.

---

# 27. Files: `app/routers/bookings.py`, `app/routers/rooms.py`

## According to Rule
**Usage report:** `/admin/usage-report` must reflect current state immediately and include rooms with zero bookings.

## Bug
- `create_booking()` invalidates room availability but does not invalidate the usage-report cache.
- `create_room()` does not invalidate the usage-report cache after adding a new room.

## Issue
A cached admin usage report can remain stale after a booking is created or a room is created, causing reports to omit new bookings or newly added rooms.

## Fixed
- Added `cache.invalidate_report(user.org_id)` in `app/routers/bookings.py` after booking creation.
- Added `cache.invalidate_report(admin.org_id)` in `app/routers/rooms.py` after room creation.

This ensures admin usage reports are rebuilt from current data whenever rooms or bookings change.
