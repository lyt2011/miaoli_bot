from langgraph.runtime	import Runtime

from miaoli_bot.models	import GraphRuntimeContext, GraphState

from datetime	import datetime
from typing		import Any, Dict


async def inject_current_time(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	"""注入当前时间 格式 年-月-日-小时-分钟-秒"""
	
	return {"prompts": {"current_time": datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}}
