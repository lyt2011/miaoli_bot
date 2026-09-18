from ncatbot.utils	import get_log

from typing			import Dict, Awaitable, Callable, Optional, Tuple, List
from collections	import defaultdict

from .pi_client	import PiClient
from ..errors	import SessionManagerClosingError, MissFactoryError

import asyncio


LOGGER = get_log("PiSessionManager")

PI_FACTORY = Optional[Callable[[], Awaitable[PiClient]]]


class PiSessionManager:

	def __init__(self) -> None:
		
		self.sessions	: Dict[str, PiClient]		= {}
		self._locks		: Dict[str, asyncio.Lock]	= defaultdict(asyncio.Lock)
		
		self._is_closing: bool = False
	
	def _pop_sessions(self) -> Tuple[List[str], List[PiClient]]:
		
		session_ids, sessions	= list(self.sessions.keys()), list(self.sessions.values())
		self.sessions			= {}
		
		return session_ids, sessions	
	
	async def close(self) -> None:
		
		if self._is_closing :
			return
		
		self._is_closing = True
		
		_, sessions = self._pop_sessions()
		
		for session in sessions:
			await session.close()
		
		return
	
	async def ensure_session(
		self,
		session_id	: str, *,
		timeout		: float			= 60.0,
		factory		: PI_FACTORY	= None,
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
			
			LOGGER.debug(f"{session_id} client 存在: {session_id in self.sessions}")
			
			if session_id in self.sessions:
				return self.sessions[session_id]
			
			elif factory is None:
				raise MissFactoryError(f"工厂缺失")
			
			factory_coro	= factory()
			pi_client		= await asyncio.wait_for(factory_coro, timeout=timeout)
			
			# 可能等待 open 时 session_manager 被关闭
			if self._is_closing:
				await pi_client.close()
				raise SessionManagerClosingError("SessionManager 正在关闭")
			
			self.sessions[session_id] = pi_client
		
		return pi_client