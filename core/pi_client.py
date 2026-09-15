from pi_bridge			import PiClient as _PiClient
from pi_bridge.models	import BaseEvent

from ncatbot.utils		import get_log
from collections.abc	import AsyncIterator
from typing				import Optional, Literal

import aiofiles


PI_LOGGER = get_log("PiClient")


class PiClient(_PiClient):
	
	async def prompt(
		self,
		*args,
		streamingBehavior: Optional[Literal["steer", "followUp"]] = None,
		**kwargs,
	) -> AsyncIterator[BaseEvent]:
		
		"""
		重写 prompt 逻辑
		使其忙时提前通过 streamingBehavior 进行其他逻辑
		而非通过 prompt 内置参数提交到 pi 后让 pi 进行
		防止一个事件流被多个 Task 注册导致混乱
		"""
		
		state = await self.get_state()
		
		if state.isStreaming is True:
			
			PI_LOGGER.debug("pi 正流式输出中...")
			
			if streamingBehavior == "steer":
				PI_LOGGER.debug("进入 steer 路径")
				await self.steer(*args, **kwargs)
			
			elif streamingBehavior == "followUp":
				PI_LOGGER.debug("进入 follow_up 路径")
				await self.follow_up(*args, **kwargs)
			
			return # HACK: 防止事件流被多次订阅 但直接return会丢失原因导致另一个订阅者不知道为什么没有收到任何event 后续可能会根据实际情况改成raise ...
		
		try:
			async for event in super().prompt(*args, **kwargs):
				yield event
		
		except ValueError as e:
			
			PI_LOGGER.error(f"prompt 出错: {e}")
			
			buffer: bytes = await self._transport._io._process.stdout.read(1024 * 1024 * 32)
			async with aiofiles.open("/root/lastest_crash.log", "wb") as file:
				await file.write(buffer)
			
			raise