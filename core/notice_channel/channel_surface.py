from ...protocols	import BaseChannel, ChannelMessage

from asyncio	import gather, wait_for
from typing		import Dict, List, Union


class ChannelSurface:
	
	"""
	把拿信息->编排->构建多个步骤弄成可调用的方法
	注意这个是一次性类 __init__ 靠重建字典以保证引用冻结
	"""
	
	def __init__(self, channels: List[BaseChannel]) -> None:
		self._channels	= {c.name: c for c in channels} # 转为字典实现冻结
	
	async def batch_drain(self, atimeout: int) -> Dict[str, Union[List[ChannelMessage], Exception]]:
		
		"""基于 asyncio.gather 并发获取新信息"""
		
		# 构建所有协程再 gather 不然太长了
		coros	= [wait_for(c.drain(), timeout=atimeout) for c in self._channels.values()]
		results	= await gather(*coros, return_exceptions=True)
		
		return dict(zip(self._channels, results))
