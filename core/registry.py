"""
没必要过度防御
必须存在的东西不存在说明是代码的问题
"""

from typing	import Any, Awaitable, Callable, Dict

from langgraph.runtime		import Runtime
from langgraph.typing		import StateT, ContextT
from langchain_core.tools	import BaseTool

from miaoli_pipeline.core	import GraphPipeline

from ..consts		import (
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
from .tool_registry	import ToolRegistry

Function	= Callable[[StateT, Runtime[ContextT]], Awaitable[Dict[str, Any]]]
Node		= Function[StateT, ContextT]

class Registry:
	
	"""
	子插件注册入口
	
	pipeline 与 tools 都是构造注入的 —— 不依赖 SHARE_STORE，
	这样 Registry 可以在 pipeline 建好之后立刻构造，与共享容器的生命周期解耦。
	"""
	
	def __init__(self, pipeline: GraphPipeline, tools: ToolRegistry) -> None:
		
		self._pipeline	: GraphPipeline	= pipeline
		self._tools		: ToolRegistry	= tools
	
	def register_tool(self, tool: BaseTool) -> None:
		self._tools.register(tool)
	
	def on_agent_start(self, node: Node, priority: int = 0) -> None:
		self._register_node(event=ON_AGENT_START, node=node, priority=priority)
	
	def on_turn_start(self, node: Node, priority: int = 0) -> None:
		self._register_node(event=ON_TURN_START, node=node, priority=priority)
	
	def on_before_compact(self, node: Node, priority: int = 0) -> None:
		self._register_node(event=ON_BEFORE_COMPACT, node=node, priority=priority)
	
	def on_compact(self, node: Node, priority: int = 0) -> None:
		self._register_node(event=ON_COMPACT, node=node, priority=priority)
	
	def on_after_compact(self, node: Node, priority: int = 0) -> None:
		self._register_node(event=ON_AFTER_COMPACT, node=node, priority=priority)
	
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
		self._pipeline.register(event=event, node=node, priority=priority)
