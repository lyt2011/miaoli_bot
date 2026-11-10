from ...protocols	import BaseChannel, BaseChannelMessage
from .helpers		import _drain_c

from typing		import Dict, List

import asyncio


ChannelDrainResult = Dict[BaseChannel, List[BaseChannelMessage]]


class ChannelSurface:
	
	def __init__(self, channels: List[BaseChannel]) -> None:
		self.channels = channels
	
	async def batch_drain(self, atimeout: float) -> ChannelDrainResult:
		
		# 转为协程列表后塞给 asyncio.gather 并发获取 超时在 _drain_c 内部判
		coros	= [_drain_c(c, timeout=atimeout) for c in self.channels]
		results	= await asyncio.gather(*coros, return_exceptions=True)

		# dict(List[Tuple[BaseChannel, List[BaseChannelMessage]]]) 直接转为字典
		return dict([result for result in results if isinstance(result, tuple)])
