Target	= Literal["group", "private"]
SubT	= Literal["record", "image", "file"]

class ToolSchema(BaseModel):
	
	id		: str		= Field(..., description="发送目标id")
	target	: Target	= Field(..., description="发送的目标 群或是私聊")
	
	file	: Path	= Field(..., description="目标文件路径") # Path 类型防路径爆破
	sub_type: SubT	= Field(default="file", description="该文件的子类型")


@tool(args_schema=ToolSchema)
async def send_file_to_qq(id: str, target: Target, file: Path, sub_type: SubT) -> str:
	
	"""
	把文件发送给 QQ 渠道的私聊或群聊会话
	
	sub_type: record -> 把文件当做音频发送
	sub_type: image -> 把文件当做图片发送
	sub_type: file -> 把文件当做基础文件发送 (需要发送纯文件时才使用这个)
	
	系统基于 target 参数决定 id 用途
	target: group -> 向群号为 id 的群发送文件
	target: private -> 向QQ号为 id 的用户发送文件
	"""
	
	config		= store_recall(PLUGIN_CONFIG)
	ncatbot_api	= store_recall(NCATBOT_API)
	
	if not any[file.is_relative_to(allow_path) for allow_path in config.file.allow_paths]:
		return f"[不可操作 {file}]"
	
	# 根据 sub_type 构建 segment 字段
	if sub_type == "record":
		segment = Record(file=file)
	
	elif sub_type == "image":
		segment = Image(file=file)
	
	elif sub_type == "file":
		segment = File(file=file)
	
	else:
		return f"[未知的文件类型: {sub_type}]"
	
	result = await easier_send(
		ncatbot_api	= store_recall(NCATBOT_API)
		chat_id		= id,
		to_group	= bool(target == "group"),
		message		= [segment.to_dict()]
	)
	
	return result.model_dump_json()