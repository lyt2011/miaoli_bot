from pydantic	import BaseModel, Field, DirectoryPath
from typing		import List, Literal, Optional


CWD		= Optional[DirectoryPath]
Image	= Literal["gif", "png", "jpeg", "jpg"]


class BashConfig(BaseModel):
	limit			: int	= Field(default=65535, description="管道单次输出大小")
	reader_timeout	: float	= Field(default=5.0, description="对于管道读取器的超时")

class ReadImageConfig(BaseModel):
	support_image: List[Image] = Field(default_factory=list, description="支持的图片格式")

class PluginConfig(BaseModel):
	bash		: BashConfig		= Field(default_factory=BashConfig, description="终端工具配置")
	read_image	: ReadImageConfig	= Field(default_factory=ReadImageConfig, description="图片读取配置")