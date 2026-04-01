def print_setup_banner() -> None:
    print("[scripts.call_python_showcase] setup banner")


def build_token(prefix: str = "demo") -> str:
    token = f"{prefix}-token"
    print(f"[scripts.call_python_showcase] build_token -> {token}")
    return token


def cleanup_marker() -> str:
    print("[scripts.call_python_showcase] cleanup marker")
    return "cleanup-finished"