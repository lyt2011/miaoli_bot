from langchain_core.tools	import BaseTool

from ..core		import SHARE_STORE
from ..consts	import TOOL_REGISTRY

from typing	import Callable

import logging


LOGGER = logging.getLogger("ToolOps")


def register_tool(tool: BaseTool) -> Callable[[], None]:
	
	"""注册工具 返回注销函数"""
	
	tool_registry = SHARE_STORE.recall(TOOL_REGISTRY)
	
	# 对于同名工具打一行警告但不拦截
	if tool_registry.contains(tool):
		LOGGER.warning(f"{tool.name} 被多次注册")
	
	# 注册工具
	tool_registry.register(tool)
	
	# 封装闭包取消逻辑函数
	def undo() -> None:
		tool_registry.unregister(tool)
	
	return undo

# 不提供 unregister_tool
# 节点摘除工具的正确逻辑是
#   - 注册方: 直接调用 undo 让注册器注销工具
#   - 其他节点: 通过 tool_surface 删除本轮工具 不直接操作 registry
# 这样能保证 tool_registry 永远是初始状态