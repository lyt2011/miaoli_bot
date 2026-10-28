from typing	import Any, Awaitable, Callable, Dict

from langgraph.runtime	import Runtime
from langgraph.typing	import StateT, ContextT

from ...stores	import SHARE_STORE
from ...consts	import (
	GRAPH_PIPELINE,
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
)


Function = Callable[[StateT, Runtime[ContextT]], Awaitable[Dict[str, Any]]]


class HandlerRegistry:
	
	"""事件处理器注册入口"""
	
	def on_agent_start(self, node: Function[StateT, ContextT], priority: int = 0) -> None:
		self.on(ON_AGENT_START, node, priority)
	
	def on_turn_start(self, node: Function[StateT, ContextT], priority: int = 0) -> None:
		self.on(ON_TURN_START, node, priority)
	
	def on_before_compact(self, node: Function[StateT, ContextT], priority: int = 0) -> None:
		self.on(ON_BEFORE_COMPACT, node, priority)
	
	def on_compact(self, node: Function[StateT, ContextT], priority: int = 0) -> None:
		self.on(ON_COMPACT, node, priority)
	
	def on_after_compact(self, node: Function[StateT, ContextT], priority: int = 0) -> None:
		self.on(ON_AFTER_COMPACT, node, priority)
	
	def on_before_request(self, node: Function[StateT, ContextT], priority: int = 0) -> None:
		self.on(ON_BEFORE_REQUEST, node, priority)
	
	def on_request(self, node: Function[StateT, ContextT], priority: int = 0) -> None:
		self.on(ON_REQUEST, node, priority)
	
	def on_after_request(self, node: Function[StateT, ContextT], priority: int = 0) -> None:
		self.on(ON_AFTER_REQUEST, node, priority)
	
	def on_tool_call(self, node: Function[StateT, ContextT], priority: int = 0) -> None:
		self.on(ON_TOOL_CALLING, node, priority)
	
	def on_turn_end(self, node: Function[StateT, ContextT], priority: int = 0) -> None:
		self.on(ON_TURN_END, node, priority)
	
	def on_agent_end(self, node: Function[StateT, ContextT], priority: int = 0) -> None:
		self.on(ON_AGENT_END, node, priority)
	
	def on(self, event: str, node: Function[StateT, ContextT], priority: int = 0) -> None:
		SHARE_STORE.recall(GRAPH_PIPELINE).register_handler(event=event, node=node, priority=priority)

	def remove_agent_start(self, node: Function[StateT, ContextT]) -> None:
		self.remove(ON_AGENT_START, node)

	def remove_turn_start(self, node: Function[StateT, ContextT]) -> None:
		self.remove(ON_TURN_START, node)

	def remove_before_compact(self, node: Function[StateT, ContextT]) -> None:
		self.remove(ON_BEFORE_COMPACT, node)

	def remove_compact(self, node: Function[StateT, ContextT]) -> None:
		self.remove(ON_COMPACT, node)

	def remove_after_compact(self, node: Function[StateT, ContextT]) -> None:
		self.remove(ON_AFTER_COMPACT, node)

	def remove_before_request(self, node: Function[StateT, ContextT]) -> None:
		self.remove(ON_BEFORE_REQUEST, node)

	def remove_request(self, node: Function[StateT, ContextT]) -> None:
		self.remove(ON_REQUEST, node)

	def remove_after_request(self, node: Function[StateT, ContextT]) -> None:
		self.remove(ON_AFTER_REQUEST, node)

	def remove_tool_call(self, node: Function[StateT, ContextT]) -> None:
		self.remove(ON_TOOL_CALLING, node)

	def remove_turn_end(self, node: Function[StateT, ContextT]) -> None:
		self.remove(ON_TURN_END, node)

	def remove_agent_end(self, node: Function[StateT, ContextT]) -> None:
		self.remove(ON_AGENT_END, node)

	def remove(self, event: str, node: Function[StateT, ContextT]) -> None:
		SHARE_STORE.recall(GRAPH_PIPELINE).unregister_handler(event=event, node=node)