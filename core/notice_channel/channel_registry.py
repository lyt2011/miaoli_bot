from ...protocols		import BaseChannel
from .channel_surface	import ChannelSurface

from typing	import List


class ChannelRegistry:
	
	def __init__(self) -> None:
		self._channels: List[BaseChannel] = [] # 以 BaseChannel.name 为证据 而非静态字典
	
	def to_surface(self) -> ChannelSurface:
		"""复制一份不可修改的 surface"""
		return ChannelSurface(list(self._channels))
	
	def register(self, channel: BaseChannel) -> None:
		
		"""注册渠道 对于相同 name 会替换原有的 channel"""
		
		channels = {c.name: c for c in self._channels}
		channels.update({channel.name: channel})
		
		self._channels = list(channels.values())
	
	def unregister(self, channel: BaseChannel) -> None:
		"""幂等注销渠道 对于不存在的渠道直接返回"""
		if channel in self._channels:
			self._channels.remove(channel)