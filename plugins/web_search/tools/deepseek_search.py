from miaoli_bot.api			import store_recall
from langchain_core.tools	import tool
from pydantic				import BaseModel, Field, model_validator
from typing					import Any, Dict, Optional, Self

from ..consts	import PLUGIN_CONFIG, CLIENT_SESSION


class ToolSchema(BaseModel):
	
	query		: str			= Field(..., min_length=1, max_length=128, description="需要搜索的内容 不能传入全空字符串")
	count		: int			= Field(default=10, gt=0, le=50, description="限制返回的结果数量")
	ori_question: Optional[str]	= Field(default=None, min_length=1, max_length=128, description="用户的原始问题 便于引擎理解 不能传入全空字符型")
	timeout		: float			= Field(default=10.0, gt=0.0, description="搜索超时时间")
	
	
	@model_validator(mode="after")
	def empty_query_checker(self) -> Self:
		
		"""确保 query 不能全空"""
		
		if not self.query.strip():
			raise ValueError("query 字段不能为全空字符串")
		
		return self
	
	@model_validator(mode="after")
	def empty_ori_question_checker(self) -> Self:
		
		"""确保 ori_question 不能全空"""
		
		if self.ori_question is not None and not self.ori_question.strip():
			raise ValueError("ori_question 字段不能为全空字符串")
		
		return self


@tool("web_search", args_schema=ToolSchema)
async def deepseek_search(query: str, count: int, ori_question: Optional[str], timeout: float) -> Dict[str, Any]:
	
	"""
	使用 deepseek 官方提供的 search api 进行搜索
	
	query 参数支持 `site:` 与 `-site:` 还有引号等搜索语法
	"""
	
	# 从全局容器拿配置
	plugin_config	= store_recall(PLUGIN_CONFIG)
	client_session	= store_recall(CLIENT_SESSION)
	
	# 更简短的命名
	api_url		= plugin_config.api_url
	api_key		= plugin_config.api_key
	
	# 构造请求头
	headers	= {
		"Content-Type": "application/json",
		"Accept": "application/json",
		"Authorization": f"Bearer {api_key}",
	}
	
	# 构造请求参数
	payload	= {
		"query": query,
		"count": count,
		"ori_question": ori_question,
		"need_content": False, # 必须关不然会炸上下文
	}
	
	try:
		
		async with client_session.post(api_url, headers=headers, json=payload, timeout=timeout) as response:
			
			if response.status != 200:
				raise RuntimeError(f"服务器响应码: {response.status}")
			
			search_result = await response.json()
	
	except Exception as e:
		return { "message": f"联网搜索出错: {type(e).__name__}: {e}" }
	
	return { "results": search_result }
