from pydantic	import BaseModel, Field
from typing		import Optional


class HelpDocConfig(BaseModel):
	
	path		: Optional[str]	= Field(default=None, description="表情包扩展帮助文档文件")
	encoding	: str			= Field(default="utf-8", description="文件编码")
