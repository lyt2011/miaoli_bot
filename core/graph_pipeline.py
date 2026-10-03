from collections	import defaultdict
from typing			import Callable, Awaitable, Dict, List, Mapping, Any, Generic, Optional, Union
from ncatbot.utils	import get_log

from langgraph.graph			import StateGraph, START, END
from langgraph.graph.state		import CompiledStateGraph
from langgraph.prebuilt			import tools_condition
from langgraph.runtime			import Runtime
from langgraph.errors			import GraphBubbleUp
from langgraph.typing			import StateT, ContextT, InputT, OutputT
from langgraph.types			import Command, Overwrite
from langgraph.checkpoint.base	import BaseCheckpointSaver

from ..models		import Handler
from ..errors		import PipelineStopDispatch, AgentAborted
from ..consts		import (
	ON_AGENT_START,
	ON_TURN_START,
	ON_BEFORE_REQUEST,
	ON_REQUEST,
	ON_AFTER_REQUEST,
	ON_TOOL_CALLING,
	ON_TURN_END,
	ON_AGENT_END,
)


LOGGER = get_log("GraphPipeline")


Function			= Callable[[StateT, Runtime[ContextT]], Awaitable[Dict[str, Any]]]
HandlerDict			= Dict[str, List[Handler]]
_StateGraph			= StateGraph[StateT, ContextT, InputT, OutputT]
_CompiledStateGraph	= CompiledStateGraph[StateT, ContextT, InputT, OutputT]


class GraphPipeline(Generic[StateT, ContextT, InputT, OutputT]):
	
	def __init__(
		self,
		state_schema	: type[StateT],
		context_schema	: Optional[type[ContextT]]	= None,
		*,
		input_schema	: Optional[type[InputT]]	= None,
		output_schema	: Optional[type[OutputT]]	= None,
	) -> None:
		
		self.handlers: HandlerDict	= defaultdict(list)
		
		self._graph: _StateGraph = StateGraph(
			state_schema,
			context_schema,
			input_schema	= input_schema,
			output_schema	= output_schema,
		)
		self._app: Optional[_CompiledStateGraph] = None
	
	async def ainvoke(self, input: Union[InputT, Command], thread_id: str, *, context: Optional[ContextT]) -> Dict[str, Any]:
		return await self._app.ainvoke(input, {"configurable": {"thread_id": thread_id}}, context=context)
	
	def wire(self) -> None:
		
		"""把事件节点和边一次性挂进图"""
		
		# 节点
		self._graph.add_node(ON_AGENT_START, self.bind(ON_AGENT_START))
		self._graph.add_node(ON_TURN_START, self.bind(ON_TURN_START))
		self._graph.add_node(ON_BEFORE_REQUEST, self.bind(ON_BEFORE_REQUEST))
		self._graph.add_node(ON_REQUEST, self.bind(ON_REQUEST))
		self._graph.add_node(ON_AFTER_REQUEST, self.bind(ON_AFTER_REQUEST))
		self._graph.add_node(ON_TOOL_CALLING, self.bind(ON_TOOL_CALLING))
		self._graph.add_node(ON_TURN_END, self.bind(ON_TURN_END))
		self._graph.add_node(ON_AGENT_END, self.bind(ON_AGENT_END))
		
		# 入口
		self._graph.add_edge(START, ON_AGENT_START)
		self._graph.add_edge(ON_AGENT_START, ON_TURN_START)
		self._graph.add_edge(ON_TURN_START, ON_BEFORE_REQUEST)
		self._graph.add_edge(ON_BEFORE_REQUEST, ON_REQUEST)
		self._graph.add_edge(ON_REQUEST, ON_AFTER_REQUEST)
		self._graph.add_edge(ON_TOOL_CALLING, ON_BEFORE_REQUEST)
		self._graph.add_edge(ON_TURN_END, ON_AGENT_END)
		self._graph.add_edge(ON_AGENT_END, END)
		
		# 循环：有 tool_calls 去跑工具 没有就收尾
		self._graph.add_conditional_edges(ON_AFTER_REQUEST, tools_condition, {"tools": ON_TOOL_CALLING, END: ON_TURN_END})
	
	def compile(self, checkpointer: Optional[BaseCheckpointSaver] = None) -> None:
		self._app: _CompiledStateGraph = self._graph.compile(checkpointer=checkpointer)
	
	def bind(self, event: str) -> Function[StateT, ContextT]:
		
		"""封装处理函数 闭包传参"""
		
		async def _node(state: StateT, runtime: Runtime[ContextT]) -> Dict[str, Any]:
			return await self._dispatch(event, state=state, runtime=runtime)
		
		_node.__name__ = event
		
		return _node
	
	def register(self, event: str, node: Function[StateT, ContextT], priority: int = 0) -> None:
		
		"""
		注册事件处理器节点
		注册时声明优先级，运行时编排顺序
		"""
		
		self.handlers[event].append(Handler(function=node, priority=priority))
		self.handlers[event].sort(key=lambda handler: handler.priority, reverse=True)
	
	async def _dispatch(self, event: str, state: StateT, runtime: Runtime[ContextT]) -> Dict[str, Any]:
		
		"""按优先级执行该事件的全部处理器 返回本次累积的增量更新"""
		
		_view	: Dict[str, Any] = self._merge(state, {}, self._graph.channels) # 保证他是一个字典 他是为了让handler之间传递数据
		_updates: Dict[str, Any] = {} # updates用于记录本次增量内容
		
		for handler in tuple(self.handlers[event]):
			
			try:
				result = await handler.function(state=_view, runtime=runtime)
			
			except AgentAborted as e:
				LOGGER.debug(f"{handler.function.__name__} 主动抛出 {type(e).__name__}: {e}")
				raise
			
			except GraphBubbleUp:
				raise
			
			except PipelineStopDispatch:
				break
			
			except Exception as e:
				LOGGER.exception(f"{handler.function.__name__} 出现错误 {type(e).__name__}: {e}")
				continue
			
			if result is not None:
				# 先更新增量 view从头重算
				_updates	= self._accumulate(_updates, result, self._graph.channels)
				_view		= self._merge(state, _updates, self._graph.channels)
		
		return _updates # 仅返回本次dispatch产生的增量内容 让框架负责更新
	
	@staticmethod
	def _merge(
		old_data: Mapping[str, Any],
		new_data: Mapping[str, Any],
		channels: Mapping[str, Any],
	) -> Dict[str, Any]:
		
		"""
		将 new_data 合进 old_data
		OverWrite 在此被展开/消费
		"""
		
		merged	= dict(old_data)
		
		for key, value in new_data.items():
			
			# 替换语义 直接换值
			if isinstance(value, Overwrite):
				merged[key] = value.value
				continue
			
			channel		= channels.get(key)
			operator	= getattr(channel, "operator", None)
			
			# 有特殊操作+增量信息->通过 operator 获取新量并返回
			if operator is not None and key in merged:
				merged[key] = operator(merged[key], value)
			
			# 无操作/不是增量 直接赋值
			else:
				merged[key] = value
		
		return merged
	
	@staticmethod
	def _accumulate(
		old_data: Mapping[str, Any],
		new_data: Mapping[str, Any],
		channels: Mapping[str, Any],
	) -> Dict[str, Any]:
		
		"""把同一个事件里多个处理器的产出折叠成一份增量"""
		
		merged	= dict(old_data)
		
		for key, value in new_data.items():
			
			channel		= channels.get(key)
			operator	= getattr(channel, "operator", None)
			
			# 无操作/不是增量 直接赋值
			if operator is None or key not in merged:
				merged[key] = value
				continue
			
			old	= merged[key]
			
			# 新来的要替换 -> 它已吸收此前的增量 直接接管
			if isinstance(value, Overwrite):
				merged[key] = value
			
			# 之前是替换 -> 新增量叠在替换结果之上 包装保留
			elif isinstance(old, Overwrite):
				merged[key] = Overwrite(operator(old.value, value))
			
			else:
				merged[key] = operator(old, value)
		
		return merged