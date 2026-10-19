ON_AGENT_START		= "__on_agent_start__"
ON_TURN_START		= "__on_turn_start__"
ON_BEFORE_COMPACT	= "__on_before_compact__"
ON_COMPACT			= "__on_compact__"
ON_AFTER_COMPACT	= "__on_after_compact__"
ON_BEFORE_REQUEST	= "__on_before_request__"
ON_REQUEST			= "__on_request__"
ON_AFTER_REQUEST	= "__on_after_request__"
ON_TOOL_CALLING		= "__on_tool_calling__"
ON_TURN_END			= "__on_turn_end__"
ON_AGENT_END		= "__on_agent_end__"

# 图里的节点声明顺序 —— 第一个事件是 START 的落点
GRAPH_EVENTS = [
	ON_AGENT_START,
	ON_TURN_START,
	ON_BEFORE_COMPACT,
	ON_COMPACT,
	ON_AFTER_COMPACT,
	ON_BEFORE_REQUEST,
	ON_REQUEST,
	ON_AFTER_REQUEST,
	ON_TOOL_CALLING,
	ON_TURN_END,
	ON_AGENT_END,
]
