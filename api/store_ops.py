"""
SHARE_STORE 的便捷 api
防止子插件直接操作 SHARE_STORE
"""


from typing	import Any

from ..stores	import SHARE_STORE


_UNSET = object()


def store_recall(key: str, *, default: Any = _UNSET) -> Any:
	
	"""
	SHARE_STORE 的便捷 recall 转发 api
	default 不传且 SHARE_STORE 没有这个键就会报错
	"""
	
	if default is _UNSET:
		return SHARE_STORE.recall(key)
	
	return SHARE_STORE.recall(key, default=default)

def store_drop(key: str) -> None:
	"""SHARE_STORE 的便捷 drop 转发 api"""
	SHARE_STORE.drop(key)

def store_update(key: str, value: Any) -> None:
	
	"""更新不能新建不存在的键"""
	
	if not SHARE_STORE.contains(key):
		raise KeyError(f"容器中没有 {key} 不可更新")
	
	SHARE_STORE.set(key, value)

def store_set(key: str, value: Any) -> None:

	"""设置不能覆盖已经存在的键"""
	
	if SHARE_STORE.contains(key):
		raise KeyError(f"容器中已有 {key} 不可覆盖")
	
	SHARE_STORE.set(key, value)

def store_contains(key: str) -> bool:
	"""判断 key 是否已经存在"""
	return SHARE_STORE.contains(key)
