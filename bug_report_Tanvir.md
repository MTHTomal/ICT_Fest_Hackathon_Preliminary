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
