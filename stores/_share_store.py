from dataclasses	import dataclass, field
from typing			import Dict, Any, Iterator

from ..protocols	import StoreProtocol


_UNSET = object()


@dataclass # 全局共享容器
class _ShareStore(StoreProtocol):
	_store: Dict[str, Any] = field(default_factory=dict)
	
	def set(self, key: str, value: Any) -> None:
		"""为 key 设置 value"""
		self._store[key] = value
	
	def drop(self, key: str) -> None:
		"""丢弃 key 与其的值"""
		self._store.pop(key, None)
	
	def clear(self) -> None:
		"""清空容器"""
		self._store = {} # 原子赋值
	
	def recall(self, key: str, default: Any = _UNSET) -> Any:
		"""获取 key 对应的值"""
		return self._store[key] if default is _UNSET else self._store.get(key, default)
	
	def contains(self, key: str) -> bool:
		"""key 是否存在于容器内"""
		return key in self._store
	
	def is_empty(self) -> bool:
		"""容器是否为空的"""
		return not self._store
	
	def keys(self) -> Iterator[str]:
		"""获取所有键 返回可迭代的对象"""
		return self._store.keys()
	
	def values(self) -> Iterator[Any]:
		"""获取所有值 返回可迭代的对象"""
		return self._store.values()


SHARE_STORE = _ShareStore()