from pydantic	import BaseModel, Field


class Account(BaseModel):
	bot_id			: str = Field(..., description="机器人QQ号")
	admin_id		: str = Field(..., description="管理员QQ号")
	bot_nickname	: str = Field(..., description="机器人昵称")
	admin_nickname	: str = Field(..., description="管理员名称")