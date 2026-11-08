"""
SHARE_STORE 的便捷 api
防止子插件直接操作 SHARE_STORE
"""


from ..core	import SHARE_STORE

import logging

from typing	import Any, Callable


LOGGER = logging.getLogger("StoreOps")

_UNSET = object()


def store_recall(key: str, *, default: Any = _UNSET) -> Any:
	
	"""
	SHARE_STORE 的便捷 recall 转发 api
	default 不传且 SHARE_STORE 没有这个键就会报错
	"""
	
	if default is _UNSET:
		return SHARE_STORE.recall(key)
	
	return SHARE_STORE.recall(key, default=default)

def store_set(key: str, value: Any, *, overwrite: bool = False) -> Callable[[], None]:

	"""为全局容器赋值 返回 disposer"""
	
	# 对于重复设置而且调用点不传 overwrite 打日志但不拦截
	if SHARE_STORE.contains(key) and not overwrite:
		LOGGER.warning(f"共享容器的 {key} 被重复设置")
	
	SHARE_STORE.set(key, value)
	
	def undo() -> None:
		if SHARE_STORE.recall(key, default=_UNSET) is value: 
			SHARE_STORE.drop(key)
	
	return undo

def store_contains(key: str) -> bool:
	"""判断 key 是否已经存在"""
	return SHARE_STORE.contains(key)
