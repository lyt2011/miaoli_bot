from pydantic	import BaseModel, Field, model_validator

from typing		import List, Literal, Self, Union


Allowed = Union[Literal["all"], List[str], None]
# all		-> 全部放行
# None		-> 全部拒绝
# list[str]	-> 内部 thread_id 放行


class Permission(BaseModel):
	
	name	: str		= Field(..., description="要声明权限的工具名")
	allowed	: Allowed	= Field(default_factory=list, description="可以使用该工具的的 thread_id 列表")