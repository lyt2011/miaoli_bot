from typing						import Dict
from io							import BytesIO
from base64						import b64decode
from PIL						import Image as PIL

import math


def b64_to_image(b64: str) -> BytesIO:
	"""将b64转为字节IO"""	
	return BytesIO(b64decode(b64))

def image_to_tokens(content: Dict[str, Dict[str, str]]) -> int:
	
	"""图片多模态转token数"""
	
	# 不校验格式 直接get尝试提取
	image_b64 = content.get("image_url", {}).get("url", "")
	if not image_b64:
		return 0
	
	# 过滤data:...前缀
	if "," in image_b64:
		image_b64 = image_b64.split(",")[-1]
	
	try:
	
		# 打开图片并归一化长宽
		image	= PIL.open(b64_to_image(image_b64))
		image_w	= min(image.width, 1920)
		image_h	= min(image.height, 1080)
		
		# 长乘宽并开方
		real_px	= int(math.sqrt(image_w * image_h))
	
	except Exception:
		return 1000 # 出错则统一1000token
	
	return real_px # 估算的token数
