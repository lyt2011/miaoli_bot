from ncatbot.utils	import get_log

from typing			import Dict, Awaitable, Callable
from collections	import defaultdict

from .pi_client	import PiClient
from ..errors	import SessionManagerClosingError

import asyncio


LOGGER = get_log("PiSessionManager")

_FACTORY_TYPE = Callable[[], Awaitable[PiClient]]


class PiSessionManager:

	def __init__(self) -> None:
		
		self.sessions	: Dict[str, PiClient]		= {}
		self._locks		: Dict[str, asyncio.Lock]	= defaultdict(asyncio.Lock)
		
		self._is_closing: bool = False
	
	async def close_sessions(self) -> None:
		
		if self._is_closing :
			return # 幂等关闭
		
		else:
			self._is_closing = True
		
		# 原子替换
		sessions		= list(self.sessions.values())
		self.sessions	= {}
		
		for session in sessions:
			await session.close()
		
		return
	
	async def ensure_session(
		self,
		session_id		: str, *,
		factory			: _FACTORY_TYPE,
		create_timeout	: float = 60.0,
	) -> PiClient:
		
		"""
		创建或直接获取会话
		自动根据 session_id 上锁
		不处理任何报错 这是特性喵
		"""
		
		# 先判断是否正在关闭 保证不冲突
		if self._is_closing:
			raise SessionManagerClosingError("SessionManager 正在关闭")
		
		async with self._locks[session_id]:
			
			if session_id in self.sessions:
				LOGGER.debug(f"{session_id} client 已存在")
				return self.sessions[session_id]
			
			LOGGER.debug(f"{session_id} client 不存在")
			
			pi_client = await asyncio.wait_for(factory(), timeout=create_timeout)
			
			# 可能等待 open 时 session_manager 被关闭
			if self._is_closing:
				await pi_client.close()
				raise SessionManagerClosingError("SessionManager 正在关闭")
			
			self.sessions[session_id] = pi_client
			LOGGER.debug(f"{session_id} client 创建成功")
		
		return pi_client