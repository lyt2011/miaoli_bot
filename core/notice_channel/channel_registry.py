from ...protocols		import BaseChannel
from .channel_surface	import ChannelSurface

from typing	import Dict


class ChannelRegistry:
	
	def __init__(self) -> None:
		self._channels: Dict[str, BaseChannel] = {}
	
	def to_surface(self) -> ChannelSurface:
		"""复制一份不可修改的 surface"""
		return ChannelSurface(list(self._channels.values()))
	
	def register(self, channel: BaseChannel) -> None:
		"""幂等注册渠道"""
		self._channels[channel.name] = channel
	
	def unregister(self, channel: BaseChannel) -> None:
		"""幂等注销渠道"""
		if self._channels.get(channel.name) is channel:
			self._channels.pop(channel.name, None)