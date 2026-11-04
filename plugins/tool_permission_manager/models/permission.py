from pydantic	import BaseModel, Field

from typing	import Literal


Mode = Literal["allow", "refuse"]


class Permission(BaseModel):
	
	name: str	= Field(..., description="要声明权限的工具名")
	mode: Mode	= Field(default="refuse", description="权限类型 默认拒绝")
