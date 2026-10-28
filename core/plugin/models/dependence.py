from typing		import Literal
from pydantic	import BaseModel, Field


Specifier = Literal["==", "!=", "<=", ">=", "<", ">", "~=", "==="]


class Dependence(BaseModel):
	
	name		: str		= Field(description="依赖的模块名")
	version		: str		= Field(description="版本限制")
	specifier	: Specifier	= Field(default="==", description="版本限定符")
	required	: bool		= Field(default=True, description="是否必须(True) 还是可选(False)")