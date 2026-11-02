from pydantic	import BaseModel, Field

from pathlib	import Path
from typing		import Optional


OPTIONAL_PATH	= Optional[Path]


class CompactConfig(BaseModel):
	
	recall_system_prompt: bool	= Field(default=True, description="是否带回消息列表中的提示词(存在的话)")
	
	keep_count	: int	= Field(default=5, description="最多保留多少条消息")
	
	encoding	: str			= Field(default="utf-8", description="指定提示词编码")
	prompt_file	: OPTIONAL_PATH	= Field(default=None, description="压缩时使用的提示词")
