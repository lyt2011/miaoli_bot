from langgraph.checkpoint.base	import BaseCheckpointSaver

from ncatbot.core	import registrar
from ncatbot.plugin	import NcatBotPlugin

from .core							import AgentAborted
from .core							import GraphPipeline
from .utils							import inject_workspace
from .models						import GraphRuntimeContext, GraphState, PluginConfig
from .core.check_pointer_adapters	import BaseCheckpointerSaverAdapter as BCSA
from .core							import ToolRegistry, Loader, HandlerRegistry, ChannelRegistry, SHARE_STORE
from .core.check_pointer_adapters	import (
	InMemoryAdapter,
	SQLiteAdapter,
	PostgresqlAdapter,
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
from typing		import Optional

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
		
		self.plugin_loader	: Optional[Loader]	= None
		self.cpa			: Optional[BCSA]	= None
	
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
		
		# 插件加载器
		self.plugin_loader = Loader(config.sub_plugin.load_from)
		
		self.logger.info(f"{PLUGIN_NAME} 已加载")
		
	async def on_close(self) -> None:
		
		# 子插件的 on_close 要从注册器摘节点和工具 必须先卸再清共享容器
		await self.plugin_loader.unload_plugins()
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
		
		if self.plugin_loader.erred:
			self.logger.warning(f"有 {len(self.plugin_loader.erred)} 个子插件加载时出现错误: "
				f"{[p.package_name for p in self.plugin_loader.erred]}")
		
		SHARE_STORE.recall(MAIN_READY).set()
	
	async def test_drain(self) -> None:
		
		channel_registry	= SHARE_STORE.recall(CHANNEL_REGISTRY)
		channel_surface		= channel_registry.to_surface()
		drain_results		= await channel_surface.batch_drain(atimeout=30) # HACK: 硬编码测试逻辑
		
		# 重建数据
		for name, messages in tuple(drain_results.items()):
			
			if isinstance(messages, Exception):
				self.logger.exception(f"通道 '{name}' 获取信息出错: {messages}")
				continue
			
			drain_results[name] = [message.to_text() for message in messages]
		
		print(drain_results)