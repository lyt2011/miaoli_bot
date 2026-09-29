from ..stores	import SHARE_STORE
from ..consts	import NCATBOT_API
from ..errors	import APIUnavailableError
from ..utils	import success

from pydantic				import BaseModel, Field
from typing					import Dict, Any
from langchain_core.tools	import tool


class ToolSchema(BaseModel):
	url: str = Field(..., description="目标 QQ 文件的url")


@tool(args_schema=ToolSchema)
async def download_qq_file(url: str) -> Dict[str, Any]:
	
	"""
	下载从 QQ 平台发来的文件
	文件会下载到指定路径 并在工具结果返回
	url 为非 QQ 平台文件时将会发生未定义情况
	"""
	
	nc_api = SHARE_STORE.recall(NCATBOT_API, None)
	if nc_api is None:
		raise APIUnavailableError("Ncatbot api is unavailable")
	
	download_result = await nc_api.qq.file.download_file(url=url)
	
	return success(download_result.model_dump())