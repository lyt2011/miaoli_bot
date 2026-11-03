"""graph_pipeline：基于优先级的异步事件管线，把处理器编排进 langgraph 状态图。

具体符号从主包 core 层导入：

	from miaoli_bot.core	import GraphPipeline
	from miaoli_bot.core	import Goto, Continue, Abort
	from miaoli_bot.core	import BaseNodeAction
	from miaoli_bot.core	import SectionPatch
	from miaoli_bot.core	import Handler
	from miaoli_bot.core	import AgentAborted

子包可直接访问：`actions` / `channels` / `runtime`。
"""

from ...errors					import AgentAborted
from .runtime.handler			import Handler
from .graph_pipeline			import GraphPipeline
from .							import actions, channels, runtime
from .channels.section_patch	import SectionPatch
from .actions					import Goto, Continue, Abort, BaseNodeAction


__all__ = [

	# 具体符号
	"GraphPipeline",
	"Goto",
	"Continue",
	"Abort",
	"BaseNodeAction",
	"SectionPatch",
	"Handler",
	"AgentAborted",

	# 子包
	"actions",
	"channels",
	"runtime",

]