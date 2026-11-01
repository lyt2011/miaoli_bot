from ..core		import SHARE_STORE
from ..core		import HandlerRegistry, ToolRegistry
from ..consts	import HANDLER_REGISTRY, TOOL_REGISTRY


def get_tool_registry() -> ToolRegistry:
	"""取工具注册表"""
	return SHARE_STORE.recall(TOOL_REGISTRY)

def get_handler_registry() -> HandlerRegistry:
	"""取事件处理器注册入口"""
	return SHARE_STORE.recall(HANDLER_REGISTRY)
