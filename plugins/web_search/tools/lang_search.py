from langchain_core.tools	import tool
from pydantic				import BaseModel, Field
from typing					import Any, Dict, List, Literal

from miaoli_bot.utils	import fail, success
from miaoli_bot.stores	import SHARE_STORE

from ..consts	import PLUGIN_CONFIG, CLIENT_SESSION


Freshness	= Literal["noLimit", "oneDay", "oneWeek", "oneMonth", "oneYear"]


class ToolSchema(BaseModel):
	query			: str		= Field(..., description="要搜索的关键词")
	count			: int		= Field(default=5, description="最大搜索结果数量", ge=1, le=50)
	freshness		: Freshness	= Field(default="noLimit", description="搜索结果的时间范围")
	include_domains	: List[str]	= Field(default_factory=list, description="必须包含的域名")
	exclude_domains	: List[str]	= Field(default_factory=list, description="必须排除的域名")
	timeout			: float		= Field(default=30.0, description="搜索超时")


@tool(args_schema=ToolSchema)
async def lang_search(
	query			: str,
	count			: int,
	freshness		: Freshness,
	include_domains	: List[str],
	exclude_domains	: List[str],
	timeout			: float,
) -> Dict[str, Any]:
	
	"""
	使用 langsearch 进行联网搜索
	**注意：任何时候都优先使用英文进行搜索，langsearch 对于中文检索效果极差**
	"""
	
	# 从全局容器拿配置
	plugin_config	= SHARE_STORE.recall(PLUGIN_CONFIG)
	client_session	= SHARE_STORE.recall(CLIENT_SESSION)
	
	# 更简短的命名
	base_url	= plugin_config.base_url
	api_key		= plugin_config.api_key
	
	# 构建请求头与请求体
	headers	= { "Authorization": f"Bearer {api_key}", "Content-Type": "application/json" }
	payload	= {
		"query": query,
		"count": count,
		"summary": False,
		"freshness": freshness,
		"includeDomains": include_domains,
		"excludeDomains": exclude_domains,
	}
	
	# 尝试联网搜索
	try:
		async with client_session.post(url=base_url, headers=headers, json=payload, timeout=timeout) as response:
			
			if response.status != 200:
				raise RuntimeError(f"服务器状态码: {response.status}")
			
			query_result = await response.json()
	
	except Exception as e:
		return fail(f"联网搜索出错: {type(e).__name__}: {e}")
	
	return success(query_result)