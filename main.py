from langchain_core.messages	import HumanMessage, AIMessage

from langgraph.checkpoint.base	import BaseCheckpointSaver

from ncatbot.core	import registrar
from ncatbot.plugin	import NcatBotPlugin

from .utils		import inject_workspace
from .models	import GraphRuntimeContext, GraphState, PluginConfig
from .core		import (
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

	# scheduler
	Every,
	Job,

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
	INVOKE_LOCK,
	CHANNEL_REGISTRY,
	MAIN_READY,
)

from pathlib	import Path
from datetime	import timedelta
from typing		import Dict, Union

import json
import asyncio


PLUGIN_NAME	= "喵璃の本体"
CPA_MAPPING	= {
	"sqlite"	: SQLiteAdapter,
	"postgresql": PostgresqlAdapter,
	"memory"	: InMemoryAdapter,
}


class MiaoLiBot(NcatBotPlugin):
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.plugin_loader	: Union[Loader, None]	= None
		self.auto_waker		: Union[Job, None]		= None
		self.cpa			: Union[BCSA, None]		= None
	
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
		SHARE_STORE.set(INVOKE_LOCK, asyncio.Lock())
		
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
		
		# 插件加载器 自动唤醒器
		self.plugin_loader	= Loader(config.sub_plugin.load_from)
		self.auto_waker		= Job(self.run_graph, Every(timedelta(seconds=60)), job_id="auto_wake")
		
		self.logger.info(f"{PLUGIN_NAME} 已加载")
		
	async def on_close(self) -> None:
		
		"""幂等关闭 有啥关啥"""
		
		if self.plugin_loader:
			await self.plugin_loader.unload_plugins()
		
		if self.auto_waker:
			self.auto_waker.stop()
		
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
		SHARE_STORE.drop(INVOKE_LOCK)
		
		if not SHARE_STORE.is_empty():
			self.logger.warning(f"共享容器可能存在资源泄露: {list(SHARE_STORE.keys())}")
		
		self.logger.info(f"{PLUGIN_NAME} 已卸载")
	
	@registrar.on_startup()
	async def on_startup(self) -> None:
		
		# 准备并加载插件
		self.plugin_loader.prepare_plugins()
		await self.plugin_loader.load_plugins()
		
		# 启动自动唤醒
		self.auto_waker.launch()
		
		SHARE_STORE.recall(MAIN_READY).set()
	
	async def run_graph(self) -> None:
		
		"""收集渠道信息并跑图"""
		
		# 等待插件完全加载
		await SHARE_STORE.recall(MAIN_READY).wait()
		
		# 拿工具注册器 拉信息（图管线由 safe_run_graph 自己取）
		tool_registry	= SHARE_STORE.recall(TOOL_REGISTRY)
		
		channel_messages	= await self.drain_channel_messages()
		channel_messages	= {k: v for k, v in tuple(channel_messages.items()) if v} # 过滤空信息渠道
		
		if not channel_messages:
			self.logger.info("没有任何渠道有新信息 跳过")
			return None
		
		raw_input	= json.dumps(channel_messages, indent=2, ensure_ascii=False)
		graph_state	= await safe_run_graph(
			{
				"raw_input": raw_input,
				"messages": [HumanMessage(raw_input)]
			},
			thread_id	= "main",
			context		= {"tool_surface": tool_registry.to_surface()}
		)
		
		# 注意顺序
		if isinstance(graph_state, AgentAborted):
			self.logger.warning(f"AGENT 被故意中断: {graph_state.reason}")
		
		elif isinstance(graph_state, Exception):
			self.logger.error(f"AGENT 出现错误: {type(graph_state).__name__}: {graph_state}", exc_info=graph_state)
		
		else:
			if (messages := graph_state.get("messages", [])) and isinstance(messages[-1], AIMessage):
				self.logger.info(f"AI 输出: {messages[-1].content}")
		
		return None
	
	async def drain_channel_messages(self) -> Dict[str, Union[str, list, dict]]:
		
		"""
		收集渠道信息
		对于 Exception -> 过滤 + 打印堆栈日志
		"""
		
		# 拿配置 / 渠道注册器
		config				= SHARE_STORE.recall(PLUGIN_CONFIG)
		channel_registry	= SHARE_STORE.recall(CHANNEL_REGISTRY)
		
		# 将渠道转为只读的 surface 并收集数据
		channel_surface	= channel_registry.to_surface()
		drain_results	= await channel_surface.batch_drain(atimeout=config.channel.drain_timeout)
		
		# 过滤 错误与真实数据
		exceptions	= [(name, result) for name, result in drain_results.items() if isinstance(result, Exception)]
		real_data	= {name: result.to_structured() for name, result in drain_results.items() if not isinstance(result, Exception)}
		
		# 为错误打日志
		for name, exception in exceptions:
			self.logger.error(f"收集渠道 '{name}' 信息出现错误: {type(exception).__name__}: {exception}", exc_info=exception)
		
		return real_data
	