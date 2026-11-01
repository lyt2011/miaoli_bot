from pathlib			import Path
from typing				import Any, Dict
from langgraph.runtime	import Runtime

from miaoli_bot.api		import store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from ..consts	import WORKSPACE


async def inject_output_protocol(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	"""注入输出协议提示词"""
	
	# 硬编码路径
	workspace	= store_recall(WORKSPACE)
	workspace	= Path(workspace)
	prompt_file	= workspace / "data" / "output_protocol.md"
	
	return {"prompts": {"output_protocol": prompt_file.read_text(encoding="utf-8")}}
