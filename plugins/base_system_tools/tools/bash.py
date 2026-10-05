from langchain_core.tools	import tool
from pydantic				import BaseModel, Field
from typing					import Dict, Any, List
from asyncio				import wait_for
from asyncio.streams		import StreamReader
from asyncio.subprocess		import Process
from contextlib				import suppress

from miaoli_bot.utils	import custom
from miaoli_bot			import SHARE_STORE

from ..consts	import PLUGIN_CONFIG

import asyncio
import codecs


async def _read_stream(stream: StreamReader, buffer: List[bytes]) -> None:
	
	async for line in stream:
		buffer.append(line)
	
	return

async def _ensure_end(proc: Process, reader: StreamReader) -> None:
	
	with suppress(Exception):
		proc.kill()
		reader.cancel()
		await proc.wait()
	
	return

def _buffer_to_string(buffer: List[bytes], encoding: str) -> str:
	return b"".join(buffer).decode(encoding, errors="replace")


class ToolSchema(BaseModel):
	cmd		: str	= Field(..., description="需要执行的终端指令")
	encoding: str	= Field(default="utf-8", description=f"缓冲区编码")
	timeout	: float	= Field(default=60.0, gt=0, description=f"超时时间(秒)")


@tool(args_schema=ToolSchema)
async def bash(
	cmd		: str,
	encoding: str,
	timeout	: float,
) -> Dict[str, Any]:
	
	"""执行终端指令"""
	
	bash_config = SHARE_STORE.recall(PLUGIN_CONFIG).bash
	
	try:
		
		# 测试编码是否可用
		codecs.lookup(encoding)
		
		proc = await asyncio.create_subprocess_shell(
			cmd		= cmd,
			limit	= bash_config.limit,
			stdout	= asyncio.subprocess.PIPE,
			stderr	= asyncio.subprocess.STDOUT,
		)
		
		buffer	= []
		reader	= asyncio.create_task(_read_stream(stream=proc.stdout, buffer=buffer))
	
	except Exception as e:
		return custom(False, error=f"{type(e).__name__}: {str(e)}")
	
	try:
	
		# 确保进程与流读取器关闭
		await wait_for(proc.wait(), timeout=timeout)
		await wait_for(reader, timeout=bash_config.reader_timeout)
	
	except Exception as e:
		return custom(False, exit_code=proc.returncode, stdout=_buffer_to_string(buffer, encoding), error=f"{type(e).__name__}: {e}")
	
	finally:
		await _ensure_end(proc=proc, reader=reader)
	
	return custom(True, exit_code=proc.returncode, stdout=_buffer_to_string(buffer, encoding))