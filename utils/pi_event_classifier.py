from pi_bridge.models	import (
	MessageUpdateEvent,
	AgentSettledEvent,
	TextDeltaEvent,
	ThinkingDeltaEvent
)

from typing	import Any


def is_text_delta(event: Any) -> bool:
		
	"""判断是否为正文(text)增量事件"""
	
	return (
		isinstance(event, MessageUpdateEvent)
		and isinstance(event.assistantMessageEvent, TextDeltaEvent)
	)

def is_thinking_delta(event: Any) -> bool:
	
	"""判断是否为思维链增量事件"""
	
	return (
		isinstance(event, MessageUpdateEvent)
		and isinstance(event.assistantMessageEvent, ThinkingDeltaEvent)
	)

def is_agent_end(event: Any) -> bool:
	
	"""判断是否为agent结束事件"""
	
	return isinstance(event, AgentSettledEvent)

def is_agent_error(event: Any) -> bool:
	
	"""判断agent是否出现错误"""
	
	return getattr(event, "error", None) is not None