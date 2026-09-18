from .base_bot_error	import BaseBotError


class MissFactoryError(BaseBotError):
	
	"""
	ensure_session 未命中缓存 且调用方没有传入建连工厂
	此时无法凭空建出 PiClient 只能报错

	携带 session_id 属性（出错的会话键） 异常消息为「<session_id> 工厂缺失」
	"""
	
	def __init__(self, session_id: str) -> None:
		
		self.session_id: str = session_id
		
		super().__init__(f"{session_id} 工厂缺失")