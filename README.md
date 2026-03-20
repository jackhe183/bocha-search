# bocha-search-mcp

博查搜索 MCP 工具，供 Claude Code agent 调用。

---

## 工程结构与设计说明

```
bocha-search-mcp/          ← 本地开发目录（你随时可以改这里的文件）
├── server.py              ← MCP 服务入口，全部逻辑在这一个文件
├── pyproject.toml         ← uv 依赖声明
├── .env                   ← API Key（本地，不提交 git）
├── .env.example           ← Key 格式示例（提交 git）
└── .gitignore
```

**为什么只有一个 `server.py`？**
MCP 工具的本质是一个 stdio 进程，Claude Code 每次调用时启动、用完就退出。
不需要路由、不需要持久化、不需要多文件拆分，单文件反而更好维护。

**为什么用 `load_dotenv()` 而不是在 Claude Code 配置里写 `env`？**
`.env` 文件放在工程目录里，和代码在一起，不用在多个地方同步 Key。
`load_dotenv()` 在读取环境变量之前调用，之后 `os.environ.get()` 就能取到值。

**为什么 `HEADERS` 在模块级别构建？**
MCP 服务每次都是全新进程，模块加载即初始化，没有"运行中修改 Key"的场景。
模块级构建比每次请求重建更简洁。

---

## 第一步：初始化工程

```powershell
# 进入你的本地开发目录
cd D:\projects\bocha-search-mcp

# 用 uv 安装依赖
uv sync
```


---

## 第二步：配置 API Key

```powershell
copy .env.example .env
```

编辑 `.env`：

```env
BOCHA_API_KEY="sk-xxx"
```

---

## 第三步：创建软连接

**目的**：Claude Code 从固定路径加载 MCP，但实际文件在你的开发目录。
修改开发目录的 `server.py` 立即生效，不需要复制文件。

以**管理员身份**打开 PowerShell：

```powershell
# 创建 Claude MCP 存放目录
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\mcp-servers"

# 创建 Junction（Windows 目录软连接）
# 左边：Claude Code 读取的路径  右边：你的开发目录
cmd /c mklink /J `
    "$env:USERPROFILE\.claude\mcp-servers\bocha-search" `
    "D:\projects\bocha-search-mcp"

# 验证软连接建立成功
dir "$env:USERPROFILE\.claude\mcp-servers"
```

预期输出中能看到 `bocha-search [D:\projects\bocha-search-mcp]`。

---

## 第四步：注册到 Claude Code

编辑 `%USERPROFILE%\.claude\settings.json`，添加以下配置：

```json
{
  "mcpServers": {
    "bocha-search": {
      "type": "stdio",
      "command": "C:\\Users\\jackHe\\.claude\\mcp-servers\\bocha-search\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\jackHe\\.claude\\mcp-servers\\bocha-search\\server.py"
      ],
      "env": {}
    }
  }
}
```

> **路径说明**
> - Windows 下 `.venv` 的 Python 在 `Scripts\python.exe`，不是 macOS 的 `bin/python`
> - 路径里用 `\\` 双反斜杠（JSON 转义要求）
> - `env` 留空即可，Key 由 `.env` 文件提供

---

## 测试流程

### 测试 1：直接运行 Python 脚本（验证环境和 Key 是否正确）

```powershell
cd D:\projects\bocha-search-mcp
.\.venv\Scripts\python.exe server.py
```

正常启动后会阻塞等待（stdio 模式），`Ctrl+C` 退出即可。
如果报 `ModuleNotFoundError`，说明依赖没装好，重新执行 `uv pip install -e .`。

### 测试 2：用 Python 直接调用搜索函数（验证 API Key 和网络）

新建一个临时脚本 `test_api.py`：

```python
import asyncio
from server import bocha_web_search, bocha_ai_search

async def main():
    print("=== Web Search ===")
    result = await bocha_web_search("Claude Code MCP 使用教程", count=3)
    print(result)

    print("\n=== AI Search ===")
    result = await bocha_ai_search("今天北京天气", count=3)
    print(result)

asyncio.run(main())
```

```powershell
.\.venv\Scripts\python.exe test_api.py
```

能看到搜索结果说明 API Key 有效、网络通畅。

### 测试 3：用 MCP Inspector 验证 MCP 协议（可选）

```powershell
# 需要 Node.js 环境
npx @modelcontextprotocol/inspector `
    .\.venv\Scripts\python.exe `
    server.py
```

浏览器打开 `http://localhost:5173`，在 Tools 面板能看到 `bocha_web_search` 和 `bocha_ai_search`，
可以手动填参数测试返回值。

### 测试 4：在 Claude Code 中调用

重启 Claude Code 后，在对话中直接说：

```
用 bocha_web_search 搜索"fastmcp 使用文档"
```

Claude Code 会调用 MCP 工具并返回结果。

---

## 后续修改工作流

1. 编辑 `D:\projects\bocha-search-mcp\server.py`
2. 保存
3. 在 Claude Code 里重新调用工具（Claude Code 每次调用都重启 MCP 进程，无需手动重启）

不需要重新安装、不需要重新建软连接、不需要改任何配置。