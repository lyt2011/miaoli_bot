from miaoli_bot.models	import GraphRuntimeContext, GraphState
from typing				import Any, Dict

from langgraph.runtime	import Runtime


MEME_HELPER = (
	"回答用户问题前，请先调用 list_memes 看看有什么表情包**适合在当前情景下**用于回应对方的\n"
	"若有表情包契合当前情景，你可以使用**send_meme_to_qq**工具把他发送出去，这是被鼓励的做法"
)


async def inject_helper(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:
	
	"""注入表情包使用提示"""
	
	return {"prompt": {"meme_helper": MEME_HELPER}}
