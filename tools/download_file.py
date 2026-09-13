from ..stores	import SHARE_STORE
from ..consts	import NCATBOT_API


async def download_qq_file(url: str) -> str:
	
	"""
	下载从 QQ 平台发来的文件
	文件会下载到指定路径 并在工具结果返回
	
	# 约束
	仅适用于 QQ 平台文件下载
	url 为非 QQ 平台文件时将会发生未定义情况
	"""
	
	nc_api = SHARE_STORE.recall(NCATBOT_API, None)
	if nc_api is None:
		return "ncatbot api is unavailable"
	
	download_result = await nc_api.qq.file.download_file(url=url)
	
	return download_result.model_dump_json()