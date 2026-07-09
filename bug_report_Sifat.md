# 1. File: `auth.py`

## According to Rule
**Auth:** Access tokens expire in exactly 900 seconds.

## Bug
```
lifetime = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
```

## Issue
The code multiplies the configured access-token lifetime in minutes by 60, causing access tokens to expire far later than the required 900 seconds.

## Fixed
```
lifetime = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
```

This uses the configured lifetime directly in minutes, ensuring access tokens expire after exactly 900 seconds.

---

# 2.

## According to Rule
**Auth:** Logout immediately invalidates the presented access token; subsequent use must fail with `401`.

## Bug
```
if payload.get("sub") in _revoked_tokens:
```

## Issue
The code checks the token's `sub` claim against the revoked-token set instead of the `jti` claim. Since revoked tokens are recorded by `jti`, valid revoked tokens are not recognized and remain accepted.

## Fixed
```
if payload.get("jti") in _revoked_tokens:
```

This checks the token identifier used for revocation, ensuring revoked access tokens are properly rejected.