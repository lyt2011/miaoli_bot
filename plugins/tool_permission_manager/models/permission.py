from pydantic	import BaseModel, Field
from typing		import Literal, List


PermissionT = Literal["admin", "white_list", "anyone"]


class Permission(BaseModel):
	tool_name	: str			= Field(..., description="要声明权限的工具名")
	permission	: PermissionT	= Field(..., description="权限类型")
	white_list	: List[str]		= Field(default_factory=list, description="白名单 (white_list时启用)")