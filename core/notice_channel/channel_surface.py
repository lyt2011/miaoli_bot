from ...protocols	import BaseChannel, BaseChannelMessage

from asyncio	import wait_for
from typing		import Dict, List, Tuple

import asyncio
import logging


LOGGER = logging.getLogger("ChannelSurface")


class ChannelSurface:
	
	def __init__(self, channels: List[BaseChannel]) -> None:
		self.channels = channels
	
	async def batch_drain(self, atimeout: float) -> Dict[BaseChannel, List[BaseChannelMessage]]:
		
		# 转为 wait_for 协程列表后塞给 asyncio.gather 并发获取
		coros	= [wait_for(_drain_c(c), timeout=atimeout) for c in self.channels]
		results	= await asyncio.gather(*coros, return_exceptions=True)
		
		# dict(List[Tuple[BaseChannel, List[BaseChannelMessage]]]) 直接转为字典
		return dict([result for result in results if isinstance(result, tuple)])


async def _drain_c(c: BaseChannel) -> Tuple[BaseChannel, List[BaseChannelMessage]]:
			
	"""返回 (渠道实例: 渠道消息列表) 元组 方便组装字典"""
	
	try:
		return (c, await c.drain())
	
	except BaseException as e:
		
		LOGGER.exception(f"渠道 {c.name} "
			f"拉取信息异常: {type(e).__name__}: {e}")
		
		raise
	
	return None