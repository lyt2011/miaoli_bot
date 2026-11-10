DEFAULT_TEMPLATE = """
Current Time: $now
Weekday: $weekday
"""
TAG = "time-inject"
HELPER_TAG = "time-inject-helper"
HELPER_TEXT = f"{TAG} 注入时刻快照，不会刷新，以最后一条为准"
