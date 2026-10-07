本插件提供了 LLM 基础的系统工具：
- `bash`: 执行终端指令
- `read_file`: 读取一个文件的内容
- `write`: 把内容写入指定文件
- `replace`: 替换文件里的指定内容
- `read_image`: 读取一张图片

## `read_image` 的格式过滤

`config.yaml` 的 `read_image.support_image` 与 `models/plugin_config.py` 的 `Image`（`Literal`）**是同一个开关**：
前者是实际生效的名单，后者只负责让名单里的值能通过加载期校验。

> ⚠️ **这是用于限制 `read_image` 的读取，而不是为了给模型过滤不同类型的图片。**
> 如果不做这个过滤，读取什么都会弄成 b64 当成图片塞进上下文里，导致 400。

`read_image` 的实现是「用 `filetype` 嗅探类型 → 拿嗅探出的扩展名比对 `support_image` → 通过则把文件整个读成 base64 拼成 `image_url` 块」。
所以**过滤发生在读盘之前**，拦下的是「压根不是图片的文件」：

| 输入 | 结果 |
|---|---|
| 不在 `support_image` 里的图片（如 `bmp`） | `fail("不支持的数据类型 bmp")`，**不读盘、不塞上下文** |
| 不是图片的文件（如 `svg` / `txt`） | `fail("无法识别 … 的类型")`（`filetype` 返回 `None`） |

没有这道过滤，任何路径都会被无条件 `b64encode` 后当作图片塞进 `messages`，
模型 API 会直接回 **400**（实测报错为 `You have uploaded an unsupported image`）。

注意 `Image` 里列的是「`filetype` 能嗅探出的全部图片扩展名」，**宽于模型 API 实际支持的格式**
（实测 `deepseek-flash` 只接受 `webp` / `png` / `jpeg` / `gif`）。
因此 `Literal` 只是保证「值能声明」，**真正的开关是 `config.yaml` 的 `support_image`** ——
往里加值时请确认目标模型确实支持该格式。
