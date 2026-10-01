from miaoli_bot	import GraphRuntimeContext, GraphState
from typing		import Dict, Any, Optional, List

from langgraph.runtime			import Runtime
from langchain_core.messages	import HumanMessage, ToolMessage


DEFAULT_NOTICE	= "图片已附加到上下文"
IMAGE_PREFIX	= "以下是工具读取的图片："


def _pick_images(content: List[Any]) -> List[Dict[str, Any]]:
	
	"""挑出 content 里的图片块 并把 image_url 统一成对象写法"""
	
	images	= []
	
	for block in content:
		
		if not isinstance(block, dict):
			continue
		
		kind = block.get("type")
		
		if kind == "image":
			images.append(block)
		
		elif kind == "image_url":
			
			url = block.get("image_url")
			
			# 兼容 {"image_url": "data:..."} 字符串写法
			if isinstance(url, str):
				url = {"url": url}
			
			images.append({"type": "image_url", "image_url": url})
	
	return images


def _pick_text(content: List[Any]) -> str:
	
	"""挑出 content 里的文字块并拼起来"""
	
	texts = []
	
	for block in content:
		
		if not isinstance(block, dict) or block.get("type") != "text":
			continue
		
		texts.append(str(block.get("text") or block.get("content") or ""))
	
	return "\n".join(text for text in texts if text).strip()


async def attach_image(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""把工具结果里的图片挪进一条 user 消息
	
	AI Platform 的 tool 消息 content 只能是字符串 不能携带多模态 block
	所以这里做两件事：
		① 把带图的 ToolMessage 换成纯文本（同 id 替换）
		② 把所有图片合并成一条 HumanMessage 追加在工具消息之后
	"""
	
	messages	= state.get("messages", [])
	total		= len(messages)
	start		= total
	
	# 只处理末尾连续的一段 ToolMessage（并行工具调用会一次冒出多条）
	while start > 0 and isinstance(messages[start - 1], ToolMessage):
		start -= 1
	
	if start >= total:
		return None
	
	replaced	= []
	images		= []
	
	for message in messages[start:]:
		
		content = message.content
		
		if not isinstance(content, list):
			continue
		
		found = _pick_images(content)
		
		if not found:
			continue
		
		images.extend(found)
		
		replaced.append(ToolMessage(
			content				= _pick_text(content) or DEFAULT_NOTICE,
			tool_call_id	= message.tool_call_id,
			id				= message.id,
			name			= getattr(message, "name", None),
			status			= getattr(message, "status", "success"),
			artifact		= getattr(message, "artifact", None),
			additional_kwargs	= message.additional_kwargs,
			response_metadata	= message.response_metadata,
		))
	
	if not images:
		return None
	
	tool_call_ids	= "-".join(str(message.tool_call_id) for message in replaced)
	
	human_message = HumanMessage(
		content	= [
			{"type": "text", "text": IMAGE_PREFIX},
			*images,
		],
		id		= f"images-{tool_call_ids}",
	)
	
	return {"messages": [*replaced, human_message]}
