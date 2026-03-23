import time

SESSION_PAUSE_DURATION = 3600  # 1 hour in seconds
SESSION_EXPIRED_ERRCODE = -14

_pause_until: dict[str, float] = {}


def pause_session(account_id: str) -> None:
    _pause_until[account_id] = time.time() + SESSION_PAUSE_DURATION


def is_session_paused(account_id: str) -> bool:
    until = _pause_until.get(account_id)
    if until is None:
        return False
    if time.time() >= until:
        del _pause_until[account_id]
        return False
    return True


def remaining_pause_seconds(account_id: str) -> float:
    until = _pause_until.get(account_id)
    if until is None:
        return 0.0
    remaining = until - time.time()
    if remaining <= 0:
        _pause_until.pop(account_id, None)
        return 0.0
    return remaining
