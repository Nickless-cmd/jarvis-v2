from __future__ import annotations

from core.services.tool_result_store import cleanup_old_results


def main() -> int:
    removed = cleanup_old_results(max_age_days=7)
    print(f"Removed {removed} tool result files older than 7 days.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
