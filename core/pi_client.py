from pi_bridge			import PiClient as _PiClient
from pi_bridge.models	import BaseEvent

from ncatbot.utils		import get_log
from collections.abc	import AsyncIterator
from typing				import Optional, Literal

from ..errors	import PIPromptBusyError

import asyncio


PI_LOGGER = get_log("PiClient")


class PiClient(_PiClient):
	
	def __init__(self, *args, **kwargs) -> None:
		
		super().__init__(*args, **kwargs)
		
		# 并发输出安全
		self._stream_lock: asyncio.Lock	= asyncio.Lock()
	
	@property
	def is_streaming(self) -> bool:
		return self._stream_lock.locked()
	
	async def prompt(
		self,
		message				: str, *,
		images				: Optional[list]	= None,
		streamingBehavior	: Optional[Literal["steer", "followUp"]]	= None,
	) -> AsyncIterator[BaseEvent]:
		
		"""
		重写 prompt 逻辑
		使其忙时提前通过 streamingBehavior 进行其他逻辑
		而非通过 prompt 内置参数提交到 pi 后让 pi 进行
		防止一个事件流被多个 Task 注册导致混乱
		"""
		
		if self._stream_lock.locked():
		
			PI_LOGGER.debug(f"pi 正流式输出中... (streamingBehavior = {streamingBehavior})")
			
			if streamingBehavior == "steer":
				await self.steer(message=message, images=images)
			
			elif streamingBehavior == "followUp":
				await self.follow_up(message=message, images=images)
			
			else:
				raise PIPromptBusyError()
			
			return
		
		await self._stream_lock.acquire()
		
		try:
			
			async for event in super().prompt(message=message, images=images):
				yield event
		
		except Exception as e:
			PI_LOGGER.exception(f"prompt 出错: {e}")
			raise
		
		finally:
			self._stream_lock.release()