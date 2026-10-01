from abc	import ABC, abstractmethod
from copy	import copy
from typing	import Any, AsyncIterator, Collection, Iterator, Optional, Self, Sequence

from langchain_core.runnables	import RunnableConfig
from langgraph.checkpoint.base	import (
	BaseCheckpointSaver,
	ChannelVersions,
	Checkpoint,
	CheckpointMetadata,
	CheckpointTuple,
)

class BaseCheckpointerSaverAdapter(ABC, BaseCheckpointSaver):

	def __init__(self, inner: BaseCheckpointSaver) -> None:
		
		super().__init__(serde=inner.serde)
		self.inner = inner

	@property
	def config_specs(self) -> list:
		return self.inner.config_specs

	def get_next_version(self, current: Any, channel: None) -> Any:
		return self.inner.get_next_version(current, channel)

	def with_allowlist(self, extra_allowlist: Collection[tuple[str, ...]]) -> BaseCheckpointSaver:
		
		inner = self.inner.with_allowlist(extra_allowlist)
		if inner is self.inner:
			return self
		
		clone = copy(self)
		clone.inner = inner
		clone.serde = inner.serde
		
		return clone

	def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
		return self.inner.get_tuple(config)

	def list(
		self,
		config	: Optional[RunnableConfig],
		*,
		filter	: Optional[dict[str, Any]]	= None,
		before	: Optional[RunnableConfig]	= None,
		limit	: Optional[int]				= None,
	) -> Iterator[CheckpointTuple]:
		return self.inner.list(config, filter=filter, before=before, limit=limit)

	def put(
		self,
		config		: RunnableConfig,
		checkpoint	: Checkpoint,
		metadata	: CheckpointMetadata,
		new_versions: ChannelVersions,
	) -> RunnableConfig:
		return self.inner.put(config, checkpoint, metadata, new_versions)

	def put_writes(
		self,
		config		: RunnableConfig,
		writes		: Sequence[tuple[str, Any]],
		task_id		: str,
		task_path	: str = "",
	) -> None:
		return self.inner.put_writes(config, writes, task_id, task_path)

	def delete_thread(self, thread_id: str) -> None:
		return self.inner.delete_thread(thread_id)

	def delete_for_runs(self, run_ids: Sequence[str]) -> None:
		return self.inner.delete_for_runs(run_ids)

	def copy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
		return self.inner.copy_thread(source_thread_id, target_thread_id)

	def prune(self, thread_ids: Sequence[str], *, strategy: str = "keep_latest") -> None:
		return self.inner.prune(thread_ids, strategy=strategy)

	async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
		return await self.inner.aget_tuple(config)

	async def alist(
		self,
		config	: Optional[RunnableConfig],
		*,
		filter	: Optional[dict[str, Any]] = None,
		before	: Optional[RunnableConfig] = None,
		limit	: Optional[int] = None,
	) -> AsyncIterator[CheckpointTuple]:
		async for checkpoint_tuple in self.inner.alist(config, filter=filter, before=before, limit=limit):
			yield checkpoint_tuple

	async def aput(
		self,
		config		: RunnableConfig,
		checkpoint	: Checkpoint,
		metadata	: CheckpointMetadata,
		new_versions: ChannelVersions,
	) -> RunnableConfig:
		return await self.inner.aput(config, checkpoint, metadata, new_versions)

	async def aput_writes(
		self,
		config		: RunnableConfig,
		writes		: Sequence[tuple[str, Any]],
		task_id		: str,
		task_path	: str = "",
	) -> None:
		return await self.inner.aput_writes(config, writes, task_id, task_path)

	async def adelete_thread(self, thread_id: str) -> None:
		return await self.inner.adelete_thread(thread_id)

	async def adelete_for_runs(self, run_ids: Sequence[str]) -> None:
		return await self.inner.adelete_for_runs(run_ids)

	async def acopy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
		return await self.inner.acopy_thread(source_thread_id, target_thread_id)

	async def aprune(self, thread_ids: Sequence[str], *, strategy: str = "keep_latest") -> None:
		return await self.inner.aprune(thread_ids, strategy=strategy)

	@classmethod
	@abstractmethod
	async def connect(cls, connect_to: str, **kwargs) -> Self: ...

	@abstractmethod
	async def close(self) -> None: ...
