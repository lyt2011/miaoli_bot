from datetime	import datetime
from typing		import Protocol, Union


class BaseTimer(Protocol):
	
	"""用于判断是否到点的抽象基类"""
	
	def next_fire_time(self, now: datetime, previous: Union[datetime, None]) -> Union[datetime, None]:
		"""获取下一次触发时间 返回 None 表示不应该再被触发"""
		...