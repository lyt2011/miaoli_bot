from ncatbot.plugin		import NcatBotPlugin
from ncatbot.core		import registrar
from ncatbot.event.qq	import MessageEvent

from pathlib	import Path
from typing		import Optional

from langgraph.checkpoint.base		import BaseCheckpointSaver

from .core		import GraphPipeline, ToolRegistry, PluginLoader, registry
from .errors	import AgentAborted
from .stores	import SHARE_STORE
from .protocols	import BaseCheckpointerSaverAdapter as BCSA
from .models	import GraphRuntimeContext, GraphState, PluginConfig
from .utils		import (
	easier_send,
	concatenate_id,
)
from .consts	import (
	NCATBOT_API,
	PLUGIN_CONFIG,
	RAW_CONFIG,
	PLUGIN_DIR,
	GRAPH_PIPELINE,
	TOOL_REGISTRY,
	WORKSPACE_DIR,
)
from .adapters	import (
	InMemoryAdapter,
	SQLiteAdapter,
	PostgresqlAdapter,
)

import asyncio
import random


PLUGIN_NAME	= "喵璃の本体"
CPA_MAPPING	= {
	"sqlite"	: SQLiteAdapter,
	"postgresql": PostgresqlAdapter,
	"memory"	: InMemoryAdapter,
}


class MiaoLiBot(NcatBotPlugin):
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.plugin_loader	: Optional[PluginLoader]	= None
		self.cpa			: Optional[BCSA]			= None
	
	@staticmethod
	def _build_graph(checkpointer: BaseCheckpointSaver) -> GraphPipeline:
		
		graph_pipeline = GraphPipeline(GraphState, context_schema=GraphRuntimeContext)
		graph_pipeline.wire()
		graph_pipeline.compile(checkpointer=checkpointer)
		
		return graph_pipeline
	
	async def on_load(self) -> None:
		
		plugin_config = PluginConfig.model_validate(self.config)
		
		database	= plugin_config.checkpointer.database
		connect_to	= plugin_config.checkpointer.connect_to
		extra		= plugin_config.checkpointer.extra
		self.cpa	= await CPA_MAPPING[database].connect(connect_to, **extra)
		
		SHARE_STORE.set(NCATBOT_API, self.api)
		
		SHARE_STORE.set(PLUGIN_CONFIG, plugin_config)
		SHARE_STORE.set(RAW_CONFIG, self.config)
		
		SHARE_STORE.set(PLUGIN_DIR, Path(__file__).resolve().parent)
		SHARE_STORE.set(WORKSPACE_DIR, self.workspace)
		
		SHARE_STORE.set(TOOL_REGISTRY, ToolRegistry())
		SHARE_STORE.set(GRAPH_PIPELINE, self._build_graph(checkpointer=self.cpa))
		
		self.plugin_loader = PluginLoader(
			path		= plugin_config.sub_plugin.load_from,
			config		= plugin_config,
			registry	= registry,
		)
		await self.plugin_loader.load_all() # NOTE: 一个插件错误会全炸完
		
		self.logger.info(f"{PLUGIN_NAME} 已加载")
		
	async def on_close(self) -> None:
		
		SHARE_STORE.drop(NCATBOT_API)
		
		SHARE_STORE.drop(PLUGIN_CONFIG)
		SHARE_STORE.drop(RAW_CONFIG)
		
		SHARE_STORE.drop(PLUGIN_DIR)
		SHARE_STORE.drop(WORKSPACE_DIR)
		
		SHARE_STORE.drop(TOOL_REGISTRY)
		SHARE_STORE.drop(GRAPH_PIPELINE)
		
		await self.plugin_loader.unload_all()
		await self.cpa.close()
				
		if not SHARE_STORE.is_empty():
			self.logger.warning(f"共享容器可能存在资源泄露: {list(SHARE_STORE.keys())}")
		
		self.logger.info(f"{PLUGIN_NAME} 已卸载")
	
	@registrar.on_message(priority=-100)
	async def on_message(self, event: MessageEvent) -> None:
		
		# 获取 event 信息
		is_group	= event.is_group_msg()
		chat_id		= event.group_id if is_group else event.sender.user_id
		session_id	= concatenate_id(chat_id, is_group=is_group)
		
		# 获取图以及根配置和工具配置
		graph_pipeline	= SHARE_STORE.recall(GRAPH_PIPELINE)
		plugin_cfg		= SHARE_STORE.recall(PLUGIN_CONFIG)
		tool_registry	= SHARE_STORE.recall(TOOL_REGISTRY)
		
		if is_group and not event.message.is_at(plugin_cfg.account.bot_id, all_except=True):
			self.logger.warning("群消息无@ 已跳过")
			return
		
		# 调用模型产生回复
		try:
			
			final_state = await graph_pipeline.ainvoke(
				{"provider": plugin_cfg.provider, "model": plugin_cfg.model, "event": event._data.model_dump()},
				thread_id	= session_id,
				context		= {"client": None, "tools": tool_registry.tools}
			)
		
		except AgentAborted as e:
			await event.reply(f"agent 被内部中断: {e.reason}")
			return
		
		except Exception as e:
			await event.reply(f"agent 内部出错: {type(e).__name__}: {e}")
			return
		
		# 根据实际情况给内容分块
		if plugin_cfg.split.enable:
			content_parts = final_state["final_answer"].split(plugin_cfg.split.delimiter)
		
		else:
			content_parts = [final_state["final_answer"]]
		
		# 遍历内容块并发送
		for index, content_part in enumerate(content_parts):
			
			# 先格式化内容块
			content_part = content_part.strip()
			
			# 若打字配置被启用则计算打字时间并等待
			if plugin_cfg.typing.enable:
				
				max_speed = plugin_cfg.typing.base_speed + plugin_cfg.typing.speed_offset
				min_speed = plugin_cfg.typing.base_speed - plugin_cfg.typing.speed_offset
				ram_speed = random.uniform(min_speed, max_speed)
				tol_speed = len(content_part) * ram_speed
				
				await asyncio.sleep(tol_speed)
			
			# REVIEW: 试行，首个块使用 event.reply 回复，如果好用我将会保留
			if index == 0:
				await event.reply(content_part)
				continue
			
			await easier_send(self.api, chat_id, content_part, to_group=is_group)