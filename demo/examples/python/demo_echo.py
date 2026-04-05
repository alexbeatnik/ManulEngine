def echo_value(value: str) -> str:
    print(f"[examples.python.demo_echo] echo_value -> {value}")
    return value


def join_values(left: str, right: str) -> str:
    result = f"{left}:{right}"
    print(f"[examples.python.demo_echo] join_values -> {result}")
    return result