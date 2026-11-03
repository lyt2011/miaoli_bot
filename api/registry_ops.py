from ..core		import SHARE_STORE
from ..core		import HandlerRegistry
from ..consts	import HANDLER_REGISTRY


def get_handler_registry() -> HandlerRegistry:
	"""取事件处理器注册入口"""
	return SHARE_STORE.recall(HANDLER_REGISTRY)