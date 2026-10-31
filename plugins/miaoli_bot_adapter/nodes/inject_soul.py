from pathlib			import Path
from typing				import Any, Dict
from langgraph.runtime	import Runtime

from miaoli_bot.api		import store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from ..consts			import WORKSPACE


async def inject_soul(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	"""注入人设提示词"""
	
	# 硬编码路径
	workspace	= store_recall(WORKSPACE)
	workspace	= Path(workspace)
	prompt_file	= workspace / "data" / "SOUL.md"
	
	return {"prompts": {"soul": prompt_file.read_text(encoding="utf-8")}}
