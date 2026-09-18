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
		
		"""
		取出并清空会话缓存的同步快照
		只负责把会话摘出来 不负责 close
		"""
		
		session_ids, sessions	= list(self.sessions.keys()), list(self.sessions.values())
		self.sessions			= {}
		
		return session_ids, sessions	
	
	async def close(self) -> None:
		
		"""
		幂等关闭全部会话
		置位关闭标志后逐个 close 关闭期间建出的 client 由 ensure_session 侧回收
		"""
		
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
		自动根据 session_id 上锁 同一会话的建连不会并发
		不处理任何报错 这是特性喵

		session_id 是会话键（group- / private- 前缀）
		timeout 是工厂建连的超时上限（秒） 默认 60
		factory 是无参异步工厂 只在未命中时调用
		未命中且 factory 缺省抛 MissFactoryError
		已关闭 / 建连期间被关闭抛 SessionManagerClosingError（已建出的 client 会被回收）
		工厂超时抛 asyncio.TimeoutError 工厂自身异常原样上抛
		"""
		
		# 先判断是否正在关闭 保证不冲突
		if self._is_closing:
			raise SessionManagerClosingError("SessionManager 正在关闭")
		
		async with self._locks[session_id]:
			
			LOGGER.debug(f"{session_id} client 存在: {session_id in self.sessions}")
			
			if session_id in self.sessions:
				return self.sessions[session_id]
			
			elif factory is None:
				raise MissFactoryError(session_id=session_id)
			
			factory_coro	= factory()
			pi_client		= await asyncio.wait_for(factory_coro, timeout=timeout)
			
			# 可能等待 open 时 session_manager 被关闭
			if self._is_closing:
				await pi_client.close()
				raise SessionManagerClosingError("SessionManager 正在关闭")
			
			self.sessions[session_id] = pi_client
		
		return pi_client