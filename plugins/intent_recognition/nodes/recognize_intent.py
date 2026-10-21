from miaoli_bot.api		import store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

import logging

from typing				import Any, Dict, Optional
from pathlib			import Path
from langgraph.runtime	import Runtime

from ..consts	import PLUGIN_CONFIG
from ..utils	import build_prompt, get_content, get_latest_human


LOGGER	= logging.getLogger()
GUIDE	= "以下本轮的意图识别注入内容，不会保留；对于有关信息必须读取 (from <file>) 提到的文件持久化进上下文。"


async def recognize_intent(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""识别本轮意图 并据此增提示词段"""
	
	plugin_cfg = store_recall(PLUGIN_CONFIG)
	
	# 稳定使用用户原始请求
	human_message = get_latest_human(state.get("messages", []))
	if not human_message:
		return None
	
	human_content	= get_content(human_message)
	field_prompts	= {}
	
	for matcher in plugin_cfg.matchers:
		
		# 防止炸节点
		try:
			
			# 需要匹配器规则全通过才算命中
			if all([rule.is_hit(human_content) for rule in matcher.rules]):
				
				# 读取提示词比根据实际需求注入路径
				prompt = Path(matcher.file).read_text(encoding=matcher.encoding)
				prompt = f"{prompt} (from {matcher.file})"
								
				field_prompts[matcher.name] = prompt
		
		except Exception as e:
			LOGGER.error(f"匹配 {matcher.name} 时出现错误: {type(e).__name__}: {e}")
	
	return {"prompts": {"intent_recognition": f"{GUIDE}\n{build_prompt(field_prompts)}"}}
