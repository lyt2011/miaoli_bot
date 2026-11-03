from langgraph.types			import Command
from langgraph.runtime			import Runtime
from langgraph.errors			import GraphBubbleUp
from langgraph.graph			import StateGraph, START
from langgraph.graph.state		import CompiledStateGraph
from langgraph.checkpoint.base	import BaseCheckpointSaver
from langgraph.typing			import StateT, ContextT, InputT, OutputT

from ...errors			import AgentAborted
from .runtimes.handler	import Handler
from .actions			import Continue, Goto, Abort, BaseNodeAction
from ...utils			import (
	ActionResult,
	is_none_action,
	is_update_action,
	merge_into_state,
	merge_into_updates,
)

from typing	import Callable, Awaitable, Dict, List, Any, Generic, Optional, Union

import logging


LOGGER = logging.getLogger("GraphPipeline")


DispatchResult_		= Union[Dict[str, Any], Command]
Function			= Callable[[StateT, Runtime[ContextT]], Awaitable[ActionResult]]
StateGraph_			= StateGraph[StateT, ContextT, InputT, OutputT]
CompiledStateGraph_	= CompiledStateGraph[StateT, ContextT, InputT, OutputT]


class GraphPipeline(Generic[StateT, ContextT, InputT, OutputT]):
	
	"""
	按优先级分发事件处理器的图管线
	
	每个事件（event）在图里对应一个节点，节点内部按 priority 降序依次调用该事件的处理器，
	把它们的返回值折叠成一份增量交给 langgraph 落盘。
	
	事件名由调用方通过 wire(events) 传入 —— 本包不预设任何业务事件。
	"""
	
	def __init__(
		self,
		state_schema	: type[StateT],
		context_schema	: Optional[type[ContextT]]	= None,
		*,
		input_schema	: Optional[type[InputT]]	= None,
		output_schema	: Optional[type[OutputT]]	= None,
	) -> None:
		
		self.handlers = []
		
		self._graph: StateGraph_ = StateGraph(
			state_schema,
			context_schema,
			input_schema	= input_schema,
			output_schema	= output_schema,
		)
		self._app: Optional[CompiledStateGraph_] = None
	
	async def ainvoke(self, input: Union[InputT, Command], thread_id: str, *, context: Optional[ContextT]) -> Dict[str, Any]:
		return await self._app.ainvoke(input, {"configurable": {"thread_id": thread_id}}, context=context)
	
	def wire(self, events: List[str]) -> None:
		
		"""
		把事件节点和入口边一次性挂进图
		events 的顺序即图里节点的声明顺序，**第一个事件是 START 的落点**
		"""
		
		if not events:
			raise ValueError("events 不能为空：至少需要一个事件作为图入口")
		
		for event in events:
			self._graph.add_node(event, self.bind(event))
		
		# 入口
		self._graph.add_edge(START, events[0])
	
	def compile(self, checkpointer: Optional[BaseCheckpointSaver] = None) -> None:
		self._app: CompiledStateGraph_ = self._graph.compile(checkpointer=checkpointer)
	
	def bind(self, event: str) -> Function[StateT, ContextT]:
		
		"""封装处理函数 闭包传参"""
		
		async def _node(state: StateT, runtime: Runtime[ContextT]) -> DispatchResult_:
			return await self._dispatch(event, state=state, runtime=runtime)
		
		_node.__name__ = event
		
		return _node
	
	def register_handler(self, event: str, func: Function[StateT, ContextT], priority: int = 0) -> Callable[[], None]:
		
		"""注册事件处理器 不会去重也没必要去重"""
		
		handler = Handler(event=event, function=func, priority=priority)
		self.handlers.append(handler)
		
		def undo() -> None:
			if handler in self.handlers:
				self.handlers.remove(handler)
		
		return undo
	
	async def _dispatch(self, event: str, state: StateT, runtime: Runtime[ContextT]) -> DispatchResult_:
		
		"""按优先级执行该事件的全部处理器 返回本次累积的增量更新"""
		
		# 初始化节点视图与增量数据
		view	: Dict[str, Any] = merge_into_state(state, {}, self._graph.channels) # 保证他是一个字典
		updates	: Dict[str, Any] = {} # updates用于记录本次增量内容
		
		# 收集并排序处理器
		handlers = [handler for handler in self.handlers if handler.event == event]
		handlers = sorted(handlers, key=lambda h: h.priority, reverse=True)
		
		LOGGER.debug(f"收集到 {len(handlers)} 个 {event} 处理器")
		
		for handler in handlers:
			
			try:
				action = await handler.function(state=view, runtime=runtime)
			
			except GraphBubbleUp:
				raise
			
			except Exception as e:
				LOGGER.exception(f"{handler.function.__name__} 出现错误 {type(e).__name__}: {e}")
				continue
			
			# 无操作
			if is_none_action(action):
				continue
			
			if is_update_action(action):
				delta	= action if isinstance(action, dict) else action.updates
				updates	= merge_into_updates(updates, delta, self._graph.channels)
				view	= merge_into_state(state, updates, self._graph.channels)
			
			if isinstance(action, Continue):
				break
			
			elif isinstance(action, Goto):
				return Command(goto=action.goto, update=updates)
			
			elif isinstance(action, Abort):
				raise AgentAborted(reason=(action.reason or "null"))
			
			elif not isinstance(action, (BaseNodeAction, dict)):
				LOGGER.error(f"未知的 Action: {type(action).__name__}")
		
		return updates # 仅返回本次dispatch产生的增量内容 让框架负责更新
