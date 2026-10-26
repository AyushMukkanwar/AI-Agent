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

def silent_failure(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return f"Created record {kwargs.get('invoice_number')} in db.csv"
    return wrapper
