"""
没必要过度防御
必须存在的东西不存在说明是代码的问题
"""

from typing	import Any, Awaitable, Callable, Dict

from langgraph.runtime		import Runtime
from langgraph.typing		import StateT, ContextT
from langchain_core.tools	import BaseTool

from ..stores		import SHARE_STORE
from ..protocols	import Parser
from ..consts		import (
	GRAPH_PIPELINE,
	TOOL_REGISTRY,
	EVENT_PARSER,
	SEGMENT_PARSER,
	ON_AGENT_START,
	ON_TURN_START,
	ON_BEFORE_REQUEST,
	ON_REQUEST,
	ON_AFTER_REQUEST,
	ON_TOOL_CALLING,
	ON_TURN_END,
	ON_AGENT_END,
)


Function	= Callable[[StateT, Runtime[ContextT]], Awaitable[Dict[str, Any]]]
Node		= Function[StateT, ContextT]


class Registry:
	
	def register_tool(self, tool: BaseTool) -> None:
		SHARE_STORE.recall(TOOL_REGISTRY).register(tool)
	
	def register_segment_parser(self, parser: Parser) -> None:
		SHARE_STORE.recall(SEGMENT_PARSER).register_parser(parser)
	
	def register_event_parser(self, parser: Parser) -> None:
		SHARE_STORE.recall(EVENT_PARSER).register_parser(parser)
	
	def on_agent_start(self, node: Node, priority: int = 0) -> None:
		self._register_node(event=ON_AGENT_START, node=node, priority=priority)
	
	def on_turn_start(self, node: Node, priority: int = 0) -> None:
		self._register_node(event=ON_TURN_START, node=node, priority=priority)
	
	def on_before_request(self, node: Node, priority: int = 0) -> None:
		self._register_node(event=ON_BEFORE_REQUEST, node=node, priority=priority)
	
	def on_request(self, node: Node, priority: int = 0) -> None:
		self._register_node(event=ON_REQUEST, node=node, priority=priority)
	
	def on_after_request(self, node: Node, priority: int = 0) -> None:
		self._register_node(event=ON_AFTER_REQUEST, node=node, priority=priority)
	
	def on_tool_call(self, node: Node, priority: int = 0) -> None:
		self._register_node(event=ON_TOOL_CALLING, node=node, priority=priority)
	
	def on_turn_end(self, node: Node, priority: int = 0) -> None:
		self._register_node(event=ON_TURN_END, node=node, priority=priority)
	
	def on_agent_end(self, node: Node, priority: int = 0) -> None:
		self._register_node(event=ON_AGENT_END, node=node, priority=priority)
	
	def _register_node(self, event: str, node: Node, priority: int = 0) -> None:
		SHARE_STORE.recall(GRAPH_PIPELINE).register(event=event, node=node, priority=priority)


registry = Registry()
