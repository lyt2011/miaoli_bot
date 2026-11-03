from langgraph._internal._typing	import MISSING
from langgraph.channels.base		import BaseChannel
from langgraph.errors				import EmptyChannelError

from typing	import Any, Dict, Optional, Sequence, get_origin


class SectionPatch(BaseChannel):
	
	"""
	按 id 打补丁的段落字典
	
	值：  {"identity": "你是喵璃", "style": "简短些"}
	更新：{"identity": "...", "style": None}
	"""
	
	__slots__ = ("value",)
	
	def __init__(self, typ: Any, key: str = "") -> None:
		
		# 先对类型进行校验
		origin = get_origin(typ) or typ
		if origin is not dict:
			raise TypeError(f"通道只支持 dict 类型，接收到: {typ!r}")
		
		super().__init__(typ, key)
		
		self.value: Any = MISSING
	
	@property
	def ValueType(self) -> Any:
		return Dict[str, str]
	
	@property
	def UpdateType(self) -> Any:
		return Dict[str, Optional[str]]
	
	def get(self) -> Dict[str, str]:
		
		if self.value is MISSING:
			raise EmptyChannelError()
		
		return dict(self.value)
	
	def update(self, values: Sequence[Dict[str, Optional[str]]]) -> bool:
		
		# 复制一份 self.value 副本
		value_snapshot = {} if self.value is MISSING else dict(self.value)
		
		# 递归 values 并使快照合并 value
		for value in values:
			
			if not isinstance(value, dict):
				raise TypeError(f"仅支持 dict 接收到 {value}")
			
			# 手动实现合并
			for dict_key, dict_value in value.items():
				
				value_snapshot[dict_key] = dict_value
				
				# None 删键
				if dict_value is None:
					value_snapshot.pop(dict_key)
		
		# 对比快照和实际字典 确实更改了才覆盖
		if (is_changed := (value_snapshot != self.value)) is True:
			self.value = value_snapshot
		
		return is_changed
	
	def from_checkpoint(self, checkpoint: Any) -> "SectionPatch":
		
		channel = self.__class__(self.typ, self.key)
		
		if checkpoint is not MISSING:
			channel.value = dict(checkpoint)
		
		return channel
	
	def __eq__(self, other: object) -> bool:
		return isinstance(other, SectionPatch)
