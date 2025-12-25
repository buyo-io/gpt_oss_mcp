# Intelligent Search MCP Server

یک سرور MCP (Model Context Protocol) هوشمند که قابلیت‌های جستجوی وب و چت با LLM را ترکیب می‌کند.

An intelligent MCP server combining web search capabilities with LLM reasoning.

---

## 📋 فهرست مطالب | Table of Contents

- [ویژگی‌ها | Features](#-ویژگیها--features)
- [پیش‌نیازها | Prerequisites](#-پیشنیازها--prerequisites)
- [نصب | Installation](#-نصب--installation)
- [راه‌اندازی | Setup](#-راهاندازی--setup)
- [استفاده | Usage](#-استفاده--usage)
- [ابزارها | Tools](#-ابزارها--tools)
- [مثال‌ها | Examples](#-مثالها--examples)
- [عیب‌یابی | Troubleshooting](#-عیبیابی--troubleshooting)

---

## 🚀 ویژگی‌ها | Features

### جستجوی وب | Web Search
- ✅ جستجو در وب با Exa API
- ✅ دریافت محتوای کامل صفحات
- ✅ پشتیبانی از pagination
- ✅ جستجو و تحلیل ترکیبی

### یکپارچگی با LLM | LLM Integration
- ✅ چت با هر LLM endpoint (OpenAI-compatible)
- ✅ تحلیل هوشمند نتایج جستجو
- ✅ پشتیبانی از system prompts سفارشی

### مدیریت Session | Session Management
- ✅ مدیریت خودکار browser instances
- ✅ کش کردن اطلاعات کاربر
- ✅ پشتیبانی از چند کاربر همزمان

---

## 📦 پیش‌نیازها | Prerequisites

```bash
Python >= 3.10
Node.js >= 22.7.5
uv (Python package manager)
```

---

## 💾 نصب | Installation

### نصب وابستگی‌های Python | Install Python Dependencies

```bash
# با uv (توصیه می‌شود)
uv add fastmcp gpt-oss requests

# یا با pip
pip install fastmcp gpt-oss requests
```

### نصب وابستگی‌های Node.js | Install Node.js Dependencies

```bash
# نصب Node.js نسخه 22+
nvm install 22
nvm use 22

# نصب MCP Inspector
npm install -g @modelcontextprotocol/inspector
```

---

## ⚙️ راه‌اندازی | Setup

### 1. تنظیم API Key

کلید API خود را در فایل `echo.py` قرار دهید:

```python
os.environ['EXA_API_KEY'] = "your-exa-api-key-here"
```

یا از متغیر محیطی استفاده کنید:

```bash
export EXA_API_KEY="your-exa-api-key-here"
```

### 2. تنظیم LLM Endpoint (اختیاری)

برای استفاده از قابلیت‌های چت و تحلیل، endpoint LLM خود را تنظیم کنید.

---

## 🎯 استفاده | Usage

### روش 1: حالت Development با Inspector

```bash
uv run fastmcp dev echo.py
```

سپس به آدرس نمایش داده شده بروید (معمولاً `http://localhost:5173`)

### روش 2: اجرای HTTP Server

ابتدا فایل را تغییر دهید:

```python
if __name__ == "__main__":
    mcp.run(
        transport="streamable_http",
        host="0.0.0.0",
        port=8002,
        stateless_http=True,
        json_response=True
    )
```

سپس اجرا کنید:

```bash
uv run python echo.py
```

سرور روی `http://localhost:8002/mcp` در دسترس خواهد بود.

### روش 3: استفاده در Claude Desktop

فایل تنظیمات Claude Desktop را ویرایش کنید:

**مسیر (macOS):** `~/Library/Application Support/Claude/claude_desktop_config.json`

**مسیر (Windows):** `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "intelligent-search": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "/path/to/echo.py"
      ]
    }
  }
}
```

---

## 🛠️ ابزارها | Tools

### 1. `search`
جستجوی ساده در وب

```json
{
  "query": "python fastmcp tutorial",
  "topn": 10
}
```

### 2. `search_and_get_content`
جستجو و دریافت محتوای کامل یک نتیجه

```json
{
  "query": "machine learning",
  "result_index": 0,
  "topn": 5
}
```

### 3. `open`
باز کردن یک لینک یا navigate در صفحه

```json
{
  "id": 0,
  "loc": 0,
  "num_lines": -1
}
```

### 4. `find`
پیدا کردن pattern در صفحه جاری

```json
{
  "pattern": "python",
  "cursor": -1
}
```

### 5. `setup_llm`
تنظیم LLM endpoint برای چت

```json
{
  "api_endpoint": "https://api.openai.com/v1/chat/completions",
  "api_key": "sk-...",
  "model": "gpt-4"
}
```

### 6. `chat_with_llm`
چت با LLM

```json
{
  "message": "توضیح بده که MCP چیست",
  "system_prompt": "تو یک معلم خوب هستی",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

### 7. `search_and_analyze`
ترکیب جستجو و تحلیل با LLM

```json
{
  "query": "latest AI trends",
  "analysis_prompt": "خلاصه کن و نکات کلیدی رو بیرون بکش",
  "result_index": 0,
  "topn": 5
}
```

### 8. `get_status`
دریافت وضعیت سیستم

```json
{}
```

---

## 💡 مثال‌ها | Examples

### مثال 1: جستجوی ساده

```bash
curl -X POST http://localhost:8002/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "search",
      "arguments": {
        "query": "FastMCP tutorial",
        "topn": 5
      }
    }
  }'
```

### مثال 2: جستجو با محتوای کامل

```python
import requests

response = requests.post(
    "http://localhost:8002/mcp",
    json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "search_and_get_content",
            "arguments": {
                "query": "python asyncio",
                "result_index": 0,
                "topn": 3
            }
        }
    }
)

print(response.json())
```

### مثال 3: تحلیل با LLM

```python
# ابتدا LLM را تنظیم کنید
setup_response = requests.post(
    "http://localhost:8002/mcp",
    json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "setup_llm",
            "arguments": {
                "api_endpoint": "https://api.openai.com/v1/chat/completions",
                "api_key": "sk-...",
                "model": "gpt-4"
            }
        }
    }
)

# سپس جستجو و تحلیل کنید
analyze_response = requests.post(
    "http://localhost:8002/mcp",
    json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "search_and_analyze",
            "arguments": {
                "query": "quantum computing breakthroughs 2025",
                "analysis_prompt": "نکات کلیدی و پیشرفت‌های اصلی رو استخراج کن"
            }
        }
    }
)

print(analyze_response.json())
```

### مثال 4: کلاینت Python کامل

```python
import asyncio
from fastmcp.client import Client

async def main():
    async with Client("http://localhost:8002/mcp") as client:
        # لیست ابزارها
        tools = await client.list_tools()
        print("Available tools:")
        for tool in tools:
            print(f"  - {tool.name}")
        
        # جستجو
        result = await client.call_tool("search", {
            "query": "MCP protocol",
            "topn": 5
        })
        print("\nSearch results:", result)

asyncio.run(main())
```

---

## 🔧 عیب‌یابی | Troubleshooting

### مشکل: "Not Acceptable: Client must accept text/event-stream"

**راه حل:**
```python
# در echo.py
if __name__ == "__main__":
    mcp.run(
        transport="streamable_http",
        stateless_http=True,
        json_response=True
    )
```

### مشکل: "ERR_MODULE_NOT_FOUND" برای Node.js

**راه حل:**
```bash
rm -rf ~/.npm/_npx
npm cache clean --force
npm install -g @modelcontextprotocol/inspector
```

### مشکل: نسخه Node.js قدیمی است

**راه حل:**
```bash
nvm install 22
nvm use 22
node --version  # باید >= 22.7.5 باشد
```

### مشکل: خطای شبکه در نصب npm

**راه حل:**
```bash
# تنظیم timeout
npm config set fetch-timeout 60000

# یا استفاده از registry دیگر
npm config set registry https://registry.npmmirror.com
```

### مشکل: EXA_API_KEY کار نمی‌کند

**راه حل:**
- کلید API خود را از [exa.ai](https://exa.ai) دریافت کنید
- در فایل `echo.py` یا متغیر محیطی قرار دهید

---

## 📚 منابع | Resources

- [FastMCP Documentation](https://gofastmcp.com)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Exa API Documentation](https://docs.exa.ai)
- [Claude Desktop Integration Guide](https://docs.anthropic.com/claude/docs)

---

## 🤝 مشارکت | Contributing

مشارکت‌ها استقبال می‌شوند! لطفاً:

1. Fork کنید
2. یک branch جدید بسازید (`git checkout -b feature/amazing-feature`)
3. تغییرات خود را commit کنید (`git commit -m 'Add amazing feature'`)
4. به branch خود push کنید (`git push origin feature/amazing-feature`)
5. یک Pull Request باز کنید

---

## 📝 لایسنس | License

این پروژه تحت لایسنس MIT منتشر شده است.

---

## 👨‍💻 نویسنده | Author

ساخته شده با ❤️ توسط تیم توسعه

---

## 🔗 لینک‌های مفید | Useful Links

- [GitHub Repository](https://github.com/yourusername/intelligent-search-mcp)
- [Issue Tracker](https://github.com/yourusername/intelligent-search-mcp/issues)
- [Discussions](https://github.com/yourusername/intelligent-search-mcp/discussions)

---

**نکته:** این سرور در حال توسعه فعال است. برای آخرین به‌روزرسانی‌ها به مخزن GitHub مراجعه کنید.

**Note:** This server is under active development. Check the GitHub repository for the latest updates.
