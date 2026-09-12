from ncatbot.plugin		import NcatBotPlugin
from ncatbot.core		import registrar
from ncatbot.event.qq	import MessageEvent
from ncatbot.utils		import get_log

from pi_bridge	import models
from pathlib	import Path

from .chains	import EventParseChain
from .core		import PIToolBackend, PiClient
from .handlers	import GroupMessageEventHandler, PrivateMessageEventHandler
from .stores	import SHARE_STORE
from .tools		import send_message_to_QQ, download_qq_file
from .adapters	import EventAdapter
from .utils		import (
	easier_send,
	get_id_from_event,
	is_agent_end,
	is_agent_error,
	is_thinking_delta,
	is_text_delta,
)

import json
import asyncio


class Claw(NcatBotPlugin):
	
	def __init__(self, *args, **kwargs) -> None:
		
		super().__init__(*args, **kwargs)
		
		self._share_store_lock	= asyncio.Lock()
		self._plugin_lock		= asyncio.Lock()
	
	async def _register_parse_chain(self) -> None:
		
		"""事件链已注册后不会重新注册处理器"""
		
		async with self._share_store_lock:
		
			if SHARE_STORE.contains("parse_chain"):
				return None
			
			parse_chain = EventParseChain()
			SHARE_STORE.set("parse_chain", parse_chain)
		
		parse_chain.register_handler(GroupMessageEventHandler())
		parse_chain.register_handler(PrivateMessageEventHandler())
		
	async def _register_tools(self) -> None:
		
		"""统一注册工具"""
		
		async with self._plugin_lock:
			
			if not hasattr(self, "config"):
				raise RuntimeError(f"调用时序出错 config不可用")
			
			config = self.config
		
		async with self._share_store_lock:
		
			if SHARE_STORE.contains("tool_backend"):
				return None
		
			tool_backend = PIToolBackend(config)
			SHARE_STORE.set("tool_backend", tool_backend)
		
		tool_backend.register_tool(send_message_to_QQ)
		tool_backend.register_tool(download_qq_file)
		
		await tool_backend.run_server()
	
	async def _close_tool_backend(self) -> None:
		
		async with self._share_store_lock:
			
			tool_backend = SHARE_STORE.recall("tool_backend", None)
			
			if tool_backend is not None:
				SHARE_STORE.drop("tool_backend")
		
		# double-check并打印日志
		if tool_backend is None:
			self.logger.warning("工具后端未启用 跳过关闭逻辑")
			return None
		
		await tool_backend.close_backend()
	
	async def on_load(self) -> None:
				
		SHARE_STORE.set("ncatbot_api", self.api)
		
		await self._register_parse_chain()
		await self._register_tools()
		
		# HACK: 为了快速测试留下的技术债
		self.pi_client = await PiClient.open(
			session_dir		= "/tmp/",
			system_prompt	= Path("/sdcard/Ncatbot_QQ/plugins/miaoli_bot/data/new_prompt.md").read_text(),
			buffer_limit	= 32 * 1024 * 1024,
		)
		await self.pi_client.set_model("lisenaupair", "deepseek-v4-flash")
		
	async def on_close(self) -> None:
		
		await self._close_tool_backend()
				
		if not SHARE_STORE.is_empty():
			self.logger.warning(f"共享容器可能存在资源泄露: {list(SHARE_STORE.keys())}")
	
	@registrar.on_message()
	async def on_message(self, event: MessageEvent) -> None:
		
		parse_chain 	= SHARE_STORE.recall("parse_chain", None)
		is_group		= event.is_group_msg()
		target_id		= get_id_from_event(event)
		event_adapter	= EventAdapter.build(event)
		
		if not parse_chain:
			self.logger.warning("parse_chain 不存在/获取失败")
			return
		
		disp_result	= await parse_chain.dispatch(event)
		if not disp_result.is_handled:
			self.logger.warning(f"无解析器器接受 {type(event)}")
			
		if not disp_result.result:
			self.logger.warning(f"{type(event)} 无处理结果")
		
		if isinstance(disp_result.result, dict):
			i_data = json.dumps(disp_result.result, ensure_ascii=False, indent=2)
		
		else:
			i_data = str(disp_result.result)
		
		client_state = await self.pi_client.get_state()
		if client_state.isStreaming is True:
			return await self.pi_client.steer(i_data)
		
		
		text	: str = ""
		thinking: str = ""
		
		async for pi_event in self.pi_client.prompt(i_data):
			
			# HACK: 不够优雅
			# FIXME: 已知bug 当AI仅回复一句话时，没有`\n\n`，不进入该逻辑，导致最终text被丢弃，可稳定复现
			if text.endswith("\n\n"):
				
				await event_adapter.send(self.api, text.rstrip())
				text = ""
			
			if is_text_delta(pi_event):
				text += pi_event.assistantMessageEvent.delta
			
			if is_thinking_delta(pi_event):
				thinking += pi_event.assistantMessageEvent.delta
			
			if is_agent_error(pi_event):
				await event_adapter.send(self.api, f"出现错误: {pi_event.error}")
			
			if is_agent_end(pi_event):
				break
		
		if thinking:
			await event_adapter.send(self.api, f"=====思维链=====\n\n{thinking}")
		
		# HACK: 因为上面的缓冲区bug 临时写一个兜底逻辑
		if text:
			await event_adapter.send(self.api, text)
		
		await event.reply("[DONE]")