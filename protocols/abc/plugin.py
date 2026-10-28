from abc	import ABC, abstractmethod


class PluginProtocol(ABC):
	
	@abstractmethod
	async def on_load(self) -> None: ...
	
	@abstractmethod
	async def on_close(self) -> None: ...