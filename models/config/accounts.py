from pydantic	import BaseModel, Field


class Accounts(BaseModel):
	bot_id			: str = Field(..., description="机器人QQ号")
	root_id			: str = Field(..., description="管理员QQ号")
	bot_nickname	: str = Field(..., description="机器人昵称")
	root_nickname	: str = Field(..., description="管理员名称")