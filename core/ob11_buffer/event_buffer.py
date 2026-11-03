from ncatbot.event.qq	import MessageEvent

from collections	import deque
from typing			import Any, List


class EventBuffer:
	
	def __init__(self, size: int) -> None:
		self.size	= size
		self.buffer	= deque(maxlen=size) # 最新的在最前面
	
	def __len__(self) -> int:
		return len(self.buffer)
	
	def pop(self, count: int) -> List[MessageEvent]:
		
		"""踢出缓冲区 count 个 event"""
		
		# 移除在范围内的 保留范围外的
		popped	= [event for index, event in enumerate(self.buffer) if in_range(index, count)]
		kept	= [event for index, event in enumerate(self.buffer) if not in_range(index, count)]
		
		# 重写 self.buffer
		self.buffer = deque(kept, maxlen=self.size)
		
		return popped
	
	def record(self, event: Any) -> None:
		"""记录并把 event 插入到列表头"""
		self.buffer.appendleft(event)


def in_range(cur: int, max_range: int) -> bool:
	"""判断索引是否在指定范围内"""
	return cur < max_range
