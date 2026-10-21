from miaoli_bot.api		import store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from typing				import Any, Dict
from pathlib			import Path
from langgraph.runtime	import Runtime

from ..consts	import PLUGIN_CONFIG


async def inject_doc(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	"""注入表情包使用提示文档"""
	
	doc_config = store_recall(PLUGIN_CONFIG).help_doc
	
	return {"prompts": {"meme_helper": Path(doc_config.path).read_text(encoding=doc_config.encoding)}}
