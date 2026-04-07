def callable_alias_demo(name: str) -> str:
    result = f"callable-{name}"
    print(f"[playground.nested.demo_tags] callable_alias_demo -> {result}")
    return result


def make_pair(first: str, second: str) -> str:
    result = f"{first}|{second}"
    print(f"[playground.nested.demo_tags] make_pair -> {result}")
    return result
