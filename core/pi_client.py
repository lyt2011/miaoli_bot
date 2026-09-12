from pi_bridge	import PiClient as _PiClient

from ncatbot.utils		import get_log
from collections.abc	import AsyncIterator

import aiofiles


PI_LOGGER = get_log("PiClient")


class PiClient(_PiClient):
	
	async def prompt(self, *args, **kwargs) -> AsyncIterator[str]:
		
		try:
			async for event in super().prompt(*args, **kwargs):
				yield event
		
		except ValueError as e:
			
			PI_LOGGER.error(f"prompt 出错: {e}")
			
			buffer: bytes = await self._transport._io._process.stdout.read(1024 * 32)
			async with aiofiles.open("/root/lastest_crash.log", "wb") as file:
				await file.write(buffer)
			
			raise