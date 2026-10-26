import functools


def fail_once(func):
    state = {"calls": 0}

    @functools.wraps(func)  # keeps the name, docstring and signature
    def wrapper(*args, **kwargs):
        state["calls"] += 1
        if state["calls"] == 1:
            raise ConnectionError(
                "Internal system temporarily unavailable (503). Please retry."
            )
        return func(*args, **kwargs)

    return wrapper
