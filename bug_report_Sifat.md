# 1. File: `app/auth.py`

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

# 2. File: `app/auth.py`

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

# 3. Files: `app/routers/bookings.py`, `app/services/refunds.py`

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

# 4. Files: `app/routers/bookings.py`, `app/routers/rooms.py`

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
