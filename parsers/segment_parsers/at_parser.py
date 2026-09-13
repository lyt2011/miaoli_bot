from ...protocols	import Parser

from ncatbot.types	import At
from typing			import Any, Dict


class AtSegmentParser(Parser):
	
	async def is_accept(self, data: Any) -> bool:
		return isinstance(data, At)
	
	async def handle(self, data: Any) -> Dict[str, Any]:
		return {"at": data.user_id}