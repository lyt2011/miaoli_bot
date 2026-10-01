from pydantic	import BaseModel, Field, model_validator
from typing		import Literal, Optional, Self


Database = Literal["memory", "sqlite", "postgresql"]


class CheckPointerConfig(BaseModel):
	database	: Database		= Field(default="memory", description="要使用的数据库")
	connect_to	: Optional[str]	= Field(default=None, description="数据库地址")
	
	@model_validator(mode="after")
	def ensure_database(self) -> Self:
		
		if self.database != "memory" and not self.connect_to:
			raise ValueError("非 memory 模式必须提供 connect_to")
		
		return self