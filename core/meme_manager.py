from ..models	import Meme

from typing		import UUID, Optional, Self, Dict
from pathlib	import Path


# TODO: 未完成


class MemeManager:
	
	def __init__(self, path: str) -> None:
		self.path: str = path
	
	