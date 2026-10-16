from typing		import Dict, List, Literal, Optional, Union
from pathlib	import Path
from pydantic	import Field

from .base_transport	import BaseTransport


CWD = Union[str, Path]


class StdioTransport(BaseTransport):
	
	""" stdio 的传输方式 """
	
	transport: Literal["stdio"]	= Field(default="stdio", description="默认就是 stdio 的传输方式")
	
	command	: str				= Field(..., description="指向一个可执行文件")
	cwd		: Optional[CWD]		= Field(default=None, description="工作目录")
	args	: List[str]			= Field(default_factory=list, description="参数列表")
	env		: Dict[str, str]	= Field(default_factory=dict, description="环境变量配置")
