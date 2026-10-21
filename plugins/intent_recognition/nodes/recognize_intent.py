from miaoli_bot.api		import store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

import logging

from typing				import Any, Dict, Optional
from pathlib			import Path
from langgraph.runtime	import Runtime

from ..consts	import PLUGIN_CONFIG
from ..utils	import build_prompt, get_content


LOGGER = logging.getLogger()


async def recognize_intent(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""识别本轮意图 并据此增提示词段"""
	
	plugin_cfg = store_recall(PLUGIN_CONFIG)
	
	messages = state.get("messages", [])
	if not messages or not hasattr(messages[-1], "content"):
		return None
	
	# 不管最后一条信息是什么都提取正文并判断
	latest_content	= get_content(messages[-1])
	field_prompts	= {}
	
	for matcher in plugin_cfg.matchers:
		
		# 防止炸节点
		try:
			
			# 需要匹配器规则全通过才算命中
			if all([rule.is_hit(latest_content) for rule in matcher.rules]):
				
				# 读取提示词比根据实际需求注入路径
				prompt = Path(matcher.file).read_text(encoding=matcher.encoding)
				if plugin_cfg.with_path:
					prompt = f"{prompt} (from {matcher.file})"
								
				field_prompts[matcher.name] = prompt
		
		except Exception as e:
			LOGGER.error(f"匹配 {matcher.name} 时出现错误: {type(e).__name__}: {e}")
	
	return {"prompt": {"intent_recognition": build_prompt(field_prompts)}}
