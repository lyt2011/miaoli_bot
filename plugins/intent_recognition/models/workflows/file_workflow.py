from pydantic	import BaseModel, Field, FilePath

from ...protocols	import BaseWorkflow

from ..rules	import Rule

from pathlib	import Path
from typing		import List, Literal


class FileWorkflow(BaseModel, BaseWorkflow):
	
	"""规则全部命中时 把 file 的内容当作工作流注入"""
	
	mode	: Literal["file"]	= Field(default="file", description="工作流来源为文件")
	
	name	: str				= Field(..., description="注入后的标签名")
	rules	: List[Rule]		= Field(default_factory=list, min_length=1, description="全部命中才算命中")
	
	file	: FilePath			= Field(..., description="工作流文件")
	encoding: str				= Field(default="utf-8", description="读取 file 用的编码")
	
	@property
	def content(self) -> str:
		"""读取工作流正文"""
		return Path(self.file).read_text(encoding=self.encoding)
