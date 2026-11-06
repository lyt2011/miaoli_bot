from ...protocols.timer	import BaseTimer

from datetime			import datetime
from logging			import getLogger
from asyncio			import CancelledError
from typing				import Any, Optional, Union
from collections.abc	import Awaitable, Callable

import uuid
import asyncio


LOGGER = getLogger(__name__)


class Job:
	
	"""一个工作对象 管理一个 func+timer"""
	
	def __init__(
		self,
		func	: Callable[[], Awaitable[Any]],
		timer	: BaseTimer,
		*,
		job_id: Optional[str] = None,
	) -> None:
		
		self.func	= func
		self.timer	= timer
		self.job_id	= job_id or str(uuid.uuid4())
		
		self._daemon	: Union[asyncio.Task, None]	= None
		self._previous	: Union[datetime, None]		= None
	
	@property
	def is_running(self) -> bool:
		return bool(self._daemon and not self._daemon.done())
	
	def launch(self, idempotent: bool = False) -> None:
		
		"""启动调度"""

		if self.is_running:
			
			# 不幂等启动 直接报错
			if not idempotent:
				raise RuntimeError("不能重复启动一个 job")
			
			# 幂等启动
			return None
		
		self._daemon = asyncio.create_task(self._run())
	
	def stop(self, idempotent: bool = True) -> None:
		
		"""停止调度"""
		
		if not self.is_running:
			
			if not idempotent:
				raise RuntimeError("不能停止一个没有运行的 job")
			
			return None
		
		self._daemon.cancel()

	async def schedule(self) -> Any:
		"""暴露给外部的转发层"""
		return await self.func()
	
	async def _run(self) -> None:
		
		"""调度逻辑的内部实现"""
		
		while True:
			
			# 获取当前时间与下一次运行时间
			now_t	= datetime.now()
			next_t	= self.timer.next_fire_time(now=now_t, previous=self._previous)
			
			# 不需要运行则跳出循环
			if next_t is None:
				LOGGER.info(f"{self.job_id} 调度正确完成")
				break
			
			# 有意义时才 sleep；否则跳过 sleep
			if (remaining_s := (next_t - now_t).total_seconds()) > 0:
				await asyncio.sleep(remaining_s)
			
			# 安全调度逻辑
			await self._safe_schedule()
			
			# 更新运行时间
			self._previous = next_t
		
		return None
	
	async def _safe_schedule(self) -> Any:
		
		"""更安全的调度运行逻辑"""
		
		try:
			await self.func()
		
		except Exception as e:
			LOGGER.error(f"{self.job_id} 执行失败: {type(e).__name__}: {e}")
		
		except CancelledError:
			LOGGER.info(f"{self.job_id} 执行被取消")
		
		else:
			LOGGER.info(f"{self.job_id} 执行完成")
		
		return None