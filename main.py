from langchain_core.messages	import HumanMessage, AIMessage

from langgraph.checkpoint.base	import BaseCheckpointSaver

from ncatbot.core	import registrar
from ncatbot.plugin	import NcatBotPlugin

from .utils		import inject_workspace
from .models	import GraphRuntimeContext, GraphState, PluginConfig
from .protocols	import BaseChannel, BaseChannelMessage
from .consts	import (
	NCATBOT_API,
	PLUGIN_CONFIG,
	RAW_CONFIG,
	PLUGIN_DIR,
	GRAPH_PIPELINE,
	TOOL_REGISTRY,
	HANDLER_REGISTRY,
	WORKSPACE_DIR,
	GRAPH_EVENTS,
	INVOKE_LOCKS,
	RUN_REQUESTED,
	CHANNEL_REGISTRY,
	MAIN_READY,
)
from .core	import (
	# share_store
	SHARE_STORE,

	# graph_runner
	safe_run_graph,

	# plugin
	Loader,

	# handler_registry
	HandlerRegistry,

	# tool
	ToolRegistry,

	# notice_channel
	ChannelRegistry,

	# graph_pipeline
	GraphPipeline,
	AgentAborted,

	# check_pointer_adapters
	InMemoryAdapter,
	SQLiteAdapter,
	PostgresqlAdapter,
	BaseCheckpointerSaverAdapter as BCSA,
)

from collections	import defaultdict
from pathlib		import Path
from contextlib		import suppress
from typing			import Dict, List, Union
from asyncio		import wait_for as await_for

import asyncio


PLUGIN_NAME	= "喵璃の本体"
CPA_MAPPING	= {
	"sqlite"	: SQLiteAdapter,
	"postgresql": PostgresqlAdapter,
	"memory"	: InMemoryAdapter,
}


ChannelDrainResult = Dict[BaseChannel, List[BaseChannelMessage]]


class MiaoLiBot(NcatBotPlugin):
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.plugin_loader	: Union[Loader, None]		= None
		self.cpa			: Union[BCSA, None]			= None
		self.tick_task		: Union[asyncio.Task, None]	= None
	
	@staticmethod
	def _build_graph(checkpointer: BaseCheckpointSaver) -> GraphPipeline:
		
		graph_pipeline = GraphPipeline(GraphState, context_schema=GraphRuntimeContext)
		graph_pipeline.wire(GRAPH_EVENTS)
		graph_pipeline.compile(checkpointer=checkpointer)
		
		return graph_pipeline
	
	async def on_load(self) -> None:
		
		# 重置插件状态
		SHARE_STORE.set(MAIN_READY, asyncio.Event())
		
		# 加载并注入插件目录
		p_path	= Path(__file__).resolve().parent
		config	= inject_workspace(self.config, str(p_path))
		config	= PluginConfig.model_validate(config)
		
		# 从配置构建 checkpointer adapter
		database	= config.checkpointer.database
		connect_to	= config.checkpointer.connect_to
		extra		= config.checkpointer.extra
		self.cpa	= await CPA_MAPPING[database].connect(connect_to, **extra)
		
		# ncatbot api/执行锁
		SHARE_STORE.set(NCATBOT_API, self.api)
		SHARE_STORE.set(INVOKE_LOCKS, defaultdict(asyncio.Lock))
		
		# 跑图请求标记
		SHARE_STORE.set(RUN_REQUESTED, asyncio.Event())
		
		# pydantic插件配置/原生配置
		SHARE_STORE.set(PLUGIN_CONFIG, config)
		SHARE_STORE.set(RAW_CONFIG, self.config)
		
		# miaoli_bot 插件目录/ncatbot 提供的工作目录
		SHARE_STORE.set(PLUGIN_DIR, p_path)
		SHARE_STORE.set(WORKSPACE_DIR, self.workspace)
		
		tool_registry	= ToolRegistry()
		graph_pipeline	= self._build_graph(checkpointer=self.cpa)
		
		# 工具注册器/图管线/处理器注册器
		SHARE_STORE.set(TOOL_REGISTRY, tool_registry)
		SHARE_STORE.set(GRAPH_PIPELINE, graph_pipeline)
		SHARE_STORE.set(HANDLER_REGISTRY, HandlerRegistry())
		SHARE_STORE.set(CHANNEL_REGISTRY, ChannelRegistry())
				
		self.logger.info(f"{PLUGIN_NAME} 初始化完成")
		
	async def on_close(self) -> None:
		
		"""幂等关闭 有啥关啥"""
		
		# 先把完成标志清理掉 完整生命周期
		if flag := SHARE_STORE.recall(MAIN_READY, default=None):
			flag.clear()
		
		if self.tick_task:
			
			self.tick_task.cancel()
			
			with suppress(asyncio.CancelledError):
				await self.tick_task
		
		if self.plugin_loader:
			await self.plugin_loader.unload_plugins()
		
		if self.cpa:
			await self.cpa.close()
		
		SHARE_STORE.drop(NCATBOT_API)
		
		SHARE_STORE.drop(PLUGIN_CONFIG)
		SHARE_STORE.drop(RAW_CONFIG)
		
		SHARE_STORE.drop(PLUGIN_DIR)
		SHARE_STORE.drop(WORKSPACE_DIR)
		
		SHARE_STORE.drop(TOOL_REGISTRY)
		SHARE_STORE.drop(GRAPH_PIPELINE)
		SHARE_STORE.drop(HANDLER_REGISTRY)
		SHARE_STORE.drop(CHANNEL_REGISTRY)
		SHARE_STORE.drop(INVOKE_LOCKS)
		SHARE_STORE.drop(RUN_REQUESTED)
		SHARE_STORE.drop(MAIN_READY)
		
		if not SHARE_STORE.is_empty():
			self.logger.warning(f"共享容器可能存在资源泄露: {list(SHARE_STORE.keys())}")
		
		self.logger.info(f"{PLUGIN_NAME} 已卸载")
	
	@registrar.on_startup()
	async def on_startup(self) -> None:
		
		config = SHARE_STORE.recall(PLUGIN_CONFIG)
		
		# 实例化 准备并加载插件
		self.plugin_loader = Loader(config.sub_plugin.load_from)
		self.plugin_loader.prepare_plugins()
		await self.plugin_loader.load_plugins()
		
		# 启动tick任务并严肃制作回调
		def _reset_task(task: asyncio.Task) -> None:
			
			# 对于未准备/正在关闭状态直接 return
			flag = SHARE_STORE.recall(MAIN_READY, default=None)
			if flag is None or not flag.is_set():
				return None
			
			# 取消不重启
			if task.cancelled():
				return None
			
			# 对错误打日志
			if (exception := task.exception()):
				self.logger.error(f"tick 任务异常: {type(exception).__name__}: {exception}", exc_info=exception)
			
			# 重启任务并添加自己作为回调
			self.tick_task = asyncio.create_task(self.tick(config.tick.interval))
			self.tick_task.add_done_callback(_reset_task)
		
		# 启动任务并将 _reset_task 作为回调
		self.tick_task = asyncio.create_task(self.tick(config.tick.interval))
		self.tick_task.add_done_callback(_reset_task)
		
		# 完成标志
		SHARE_STORE.recall(MAIN_READY).set()
		
		# 完全完成加载的日志
		self.logger.info(f"{PLUGIN_NAME} 完全启动完成")
	
	async def tick(self, tick_interval: float) -> None:
		
		"""
		每 tick 的主动唤醒
		会被 RUN_REQUESTED 标记影响提前跑图
		"""
		
		while True:
			
			# 拿配置
			config = SHARE_STORE.recall(PLUGIN_CONFIG)
			
			# 等待 tick 时机
			await self._wait_atick(
				fg=SHARE_STORE.recall(RUN_REQUESTED), timeout=tick_interval)
			
			# 收集渠道信息
			channel_messages = await self._drain_channels(
				registry=SHARE_STORE.recall(CHANNEL_REGISTRY), atimeout=config.channel.atimeout)
			
			# 串行跑图
			await self._run_channel_graphs(channel_messages=channel_messages, atimeout=config.graph.atimeout)
			
			self.logger.debug("一轮 tick 运行完成")
	
	async def _run_channel_graphs(self, channel_messages: ChannelDrainResult, atimeout: float) -> None:
		
		"""为渠道消息串行跑图 并行跑图容易把日志混淆在一坨 肉眼难以分辨"""
		
		for channel, messages in channel_messages.items():
			for message in messages:
				
				try:
					await await_for(self._run_channel_graph(
						channel, message), timeout=atimeout)
				
				except Exception as e:
					self.logger.exception(f"{channel.name}: "
						f"{message.thread_id}跑图时出现异常: {type(e).__name__}: {e}")
				
				else:
					self.logger.debug(f"{channel.name}: {message.thread_id} 跑图完成")
	
		return None
	
	async def _wait_atick(self, fg: asyncio.Event, timeout: float) -> None:
		
		"""
		等待下一个 tick
		返回前清理 tick 标记残留 (无论是超时还是被主动.set)
		"""
		
		with suppress(asyncio.TimeoutError):
			await await_for(
				fg.wait(), timeout=timeout)
		
		# 释放后立马.clear
		fg.clear()
	
	async def _drain_channels(self, registry: ChannelRegistry, atimeout: float) -> ChannelDrainResult:
		"""将渠道注册器转为 surface 后获取所有信息"""
		return await registry.to_surface().batch_drain(atimeout=atimeout)
	
	async def _run_channel_graph(self, channel: BaseChannel, message: BaseChannelMessage) -> None:
		
		"""
		专门服务于 tick 函数的辅助方法 直接当做外置逻辑即可 内部自动获取 tool_registry
		通过 BaseChannel 和 BaseChannelMessage 进行跑图 没有返回值
		若产生了回复 将直接通过 channel.reply 返回给通道
		(channel.reply 抛出的异常会冒给调用方)
		"""
		
		# 过滤空消息 不要瞎跑图
		if not (text := message.to_text().strip()):
			return None
			
		state = await safe_run_graph(
			{
				"messages": [HumanMessage(text)],
			},
			thread_id	= message.thread_id,
			context		= {"tool_surface": SHARE_STORE.recall(TOOL_REGISTRY).to_surface()}
		)
		
		# 注意按顺序匹配
		match state:
			
			case AgentAborted():
				self.logger.warning(f"渠道 {channel.name}: "
					f"{message.thread_id} 因为 {state.reason} 主动中断了跑图")
			
			case Exception():
				self.logger.error(f"渠道 {channel.name}: "
					f"{message.thread_id} 跑图时出现异常: {type(state).__name__}: {state}", exc_info=state)
			
			case {"messages": messages}:
				if messages and isinstance(messages[-1], AIMessage):
					await channel.reply(message.thread_id, messages[-1].content)
			
			case _:
				self.logger.error(f"渠道 {channel.name}: "
					f"{message.thread_id} 返回了没有被 match-case 匹配的对象: {type(state).__name__}")
		
		return None