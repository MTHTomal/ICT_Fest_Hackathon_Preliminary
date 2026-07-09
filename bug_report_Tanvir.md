# 1. File: `timeutils.py`

## According to Rule

**Datetimes:** Input datetimes carrying a UTC offset must be converted to UTC before storage or comparison; naive input is treated as UTC.

## Bug

```python
if dt.tzinfo is not None:
    dt = dt.replace(tzinfo=None)
```

## Issue

The code removes the timezone information without first converting the datetime to UTC. As a result, offset-aware datetimes are stored with an incorrect timestamp, leading to incorrect storage and comparison.

## Fixed

```python
if dt.tzinfo is not None:
    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
```

This converts offset-aware datetimes to UTC before removing the timezone information, ensuring all stored datetimes are normalized as naive UTC values in accordance with the business rule.


