from ncatbot.types	import MessageArray, File

from ..utils	import easier_send, success, fail
from ..stores	import SHARE_STORE
from ..consts	import NCATBOT_API
from ..errors	import APIUnavailableError

from pydantic				import BaseModel, Field, FilePath
from typing					import Union, Dict, Any
from langchain_core.tools	import tool

import os


def get_size_MB(path: str) -> Union[int, float]:
	return os.path.getsize(path) / (1024 * 1024)


class ToolSchema(BaseModel):
	path	: FilePath	= Field(..., description="文件路径")
	chat_id	: str		= Field(..., description="接收方ID")
	to_group: bool		= Field(default=False, description="是否发送到群，布尔类型，默认私聊")


@tool(args_schema=ToolSchema)
async def send_file_to_qq(path: str, chat_id: str, to_group: bool = False) -> Dict[str, Any]:
	
	"""
	发送一个文件到 QQ
	文件大小最大 20 MB
	
	to_group 的值决定了 chat_id 的用途
	true: chat_id 作为群聊ID，将信息发送到 chat_id 对应的群聊
	false: chat_id 作为用户QQ号，将信息以私聊的方式发送到 chat_id 对应的用户
	"""
	
	nc_api = SHARE_STORE.recall(NCATBOT_API, None)
	if nc_api is None:
		raise APIUnavailableError("Ncatbot api is unavailable")
	
	if not os.path.isfile(path):
		return fail(f"{path} 不存在或不是一个文件")
	
	size_MB = get_size_MB(path)
	if size_MB >= 20:
		return fail(f"{path} 过大: {size_MB}MB > 20MB")
	
	send_result = await easier_send(
		ncatbot_api	= nc_api,
		chat_id		= chat_id,
		to_group	= to_group,
		message		= MessageArray([File(file=path)])
	)
	
	return success(send_result.model_dump())