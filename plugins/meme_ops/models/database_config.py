from pydantic	import BaseModel, Field
from typing		import Optional


class DatabaseConfig(BaseModel):
	
	path	: Optional[str]	= Field(default=None, description="meme 的 sql 数据库路径")
