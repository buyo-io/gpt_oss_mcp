import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Union, Optional
from datetime import datetime, timedelta
from fastmcp import Context, FastMCP
from gpt_oss.tools.simple_browser import SimpleBrowserTool
from gpt_oss.tools.simple_browser.backend import ExaBackend
import requests

@dataclass
class AppContext:
    """Context برای نگهداری browser instances و cache اطلاعات کاربر"""
    browsers: dict[str, SimpleBrowserTool] = field(default_factory=dict)
    user_cache: dict = field(default_factory=lambda: {
        "token": None,
        "expires_at": None,
        "session_id": None,
        "llm_endpoint": None
    })

    def create_or_get_browser(self, session_id: str) -> SimpleBrowserTool:
        """ساخت یا دریافت browser instance برای session"""
        if session_id not in self.browsers:
            os.environ['EXA_API_KEY'] = "dbe54420-baba-48f4-abc7-e62f158d0586"
            backend = ExaBackend(source="web")
            self.browsers[session_id] = SimpleBrowserTool(backend=backend)
        return self.browsers[session_id]

    def remove_browser(self, session_id: str) -> None:
        """حذف browser instance"""
        self.browsers.pop(session_id, None)

    def get_cached_token(self) -> Optional[str]:
        """دریافت token از cache"""
        if self.user_cache["token"] and self.user_cache["expires_at"]:
            if datetime.now() < self.user_cache["expires_at"]:
                return self.user_cache["token"]
        return None

    def set_token(self, token: str, expires_in: int):
        """ذخیره token در cache"""
        self.user_cache["token"] = token
        self.user_cache["expires_at"] = datetime.now() + timedelta(seconds=expires_in - 300)

@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncIterator[AppContext]:
    """Lifespan برای مدیریت application context"""
    yield AppContext()

# ساخت FastMCP server
mcp = FastMCP(
    name="intelligent-search",
    instructions=r"""
An intelligent search and chat system that combines web search capabilities with LLM reasoning.
For search results, the `cursor` appears in brackets: `[{cursor}]`.
Cite search results using: `【{cursor}†L{line_start}(-L{line_end})?】`
Example: `【6†L9-L11】` or `【8†L3】`
""".strip(),
    lifespan=app_lifespan,
    port=8002,
)

# =============================================================================
# SEARCH TOOLS (Browser-based)
# =============================================================================

@mcp.tool(
    name="search",
    title="Search the web",
    description="جستجوی اطلاعات در وب و نمایش لینک‌های یافت شده",
)
async def search(
    ctx: Context,
    query: str,
    topn: int = 10,
) -> str:
    """جستجوی اطلاعات در وب - فقط لیست نتایج را برمی‌گرداند"""
    browser = ctx.request_context.lifespan_context.create_or_get_browser(
        ctx.client_id
    )
    messages = []
    async for message in browser.search(query=query, topn=topn):
        if message.content and hasattr(message.content[0], 'text'):
            messages.append(message.content[0].text)
    return "\n".join(messages)


@mcp.tool(
    name="search_and_get_content",
    title="Search and get full content",
    description="جستجو در وب و دریافت محتوای کامل اولین نتیجه یا نتیجه با شماره مشخص",
)
async def search_and_get_content(
    ctx: Context,
    query: str,
    result_index: int = 0,
    topn: int = 10,
) -> str:
    """جستجو و دریافت محتوای کامل یک نتیجه"""
    browser = ctx.request_context.lifespan_context.create_or_get_browser(
        ctx.client_id
    )
    
    # مرحله 1: جستجو
    search_messages = []
    async for message in browser.search(query=query, topn=topn):
        if message.content and hasattr(message.content[0], 'text'):
            search_messages.append(message.content[0].text)
    
    search_result = "\n".join(search_messages)
    
    # مرحله 2: باز کردن لینک با شماره result_index
    content_messages = []
    async for message in browser.open(id=result_index, loc=0, num_lines=-1):
        if message.content and hasattr(message.content[0], 'text'):
            content_messages.append(message.content[0].text)
    
    full_content = "\n".join(content_messages)
    
    return f"""=== نتایج جستجو ===
{search_result}

=== محتوای کامل نتیجه {result_index} ===
{full_content}
"""


@mcp.tool(
    name="open",
    title="Open a link or page",
    description="باز کردن یک لینک یا navigate در صفحه. id می‌تواند شماره لینک یا URL کامل باشد",
)
async def open_link(
    ctx: Context,
    id: Union[int, str] = -1,
    cursor: int = -1,
    loc: int = -1,
    num_lines: int = -1,
) -> str:
    """باز کردن لینک و دریافت محتوای کامل"""
    browser = ctx.request_context.lifespan_context.create_or_get_browser(
        ctx.client_id
    )
    messages = []
    async for message in browser.open(
        id=id,
        cursor=cursor,
        loc=loc,
        num_lines=num_lines,
        view_source=False,
    ):
        if message.content and hasattr(message.content[0], 'text'):
            messages.append(message.content[0].text)
    return "\n".join(messages)


@mcp.tool(
    name="find",
    title="Find pattern in page",
    description="پیدا کردن pattern در صفحه جاری",
)
async def find_pattern(
    ctx: Context,
    pattern: str,
    cursor: int = -1
) -> str:
    """پیدا کردن pattern در صفحه جاری"""
    browser = ctx.request_context.lifespan_context.create_or_get_browser(
        ctx.client_id
    )
    messages = []
    async for message in browser.find(pattern=pattern, cursor=cursor):
        if message.content and hasattr(message.content[0], 'text'):
            messages.append(message.content[0].text)
    return "\n".join(messages)


# =============================================================================
# LLM CHAT TOOLS (بدون تغییر - همان کد قبلی)
# =============================================================================

@mcp.tool(
    name="setup_llm",
    title="Setup LLM endpoint",
    description="Configure the LLM endpoint and authentication for chat functionality.",
)
def setup_llm(
    ctx: Context,
    api_endpoint: str,
    api_key: Optional[str] = None,
    model: str = "gpt-4"
) -> dict:
    """تنظیم endpoint و authentication برای LLM"""
    try:
        app_ctx = ctx.request_context.lifespan_context
        app_ctx.user_cache["llm_endpoint"] = api_endpoint
        app_ctx.user_cache["api_key"] = api_key
        app_ctx.user_cache["model"] = model
        
        return {
            "success": True,
            "message": "LLM endpoint configured successfully",
            "endpoint": api_endpoint,
            "model": model
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(
    name="chat_with_llm",
    title="Chat with LLM",
    description="Send a message to the LLM and get a reasoned response.",
)
def chat_with_llm(
    ctx: Context,
    message: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000
) -> dict:
    """چت با LLM برای reasoning و تحلیل"""
    try:
        app_ctx = ctx.request_context.lifespan_context
        
        llm_endpoint = app_ctx.user_cache.get("llm_endpoint")
        if not llm_endpoint:
            return {
                "success": False,
                "error": "LLM endpoint not configured. Use setup_llm first."
            }
        
        api_key = app_ctx.user_cache.get("api_key")
        model = app_ctx.user_cache.get("model", "gpt-4")
        
        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        messages = []
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        messages.append({
            "role": "user",
            "content": message
        })
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        response = requests.post(
            llm_endpoint,
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        
        llm_response = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        return {
            "success": True,
            "response": llm_response,
            "model": model,
            "usage": result.get("usage", {})
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(
    name="search_and_analyze",
    title="Search and analyze with LLM",
    description="ترکیب جستجوی وب با تحلیل LLM - محتوای کامل اولین نتیجه را دریافت و تحلیل می‌کند",
)
async def search_and_analyze(
    ctx: Context,
    query: str,
    analysis_prompt: str,
    result_index: int = 0,
    topn: int = 5,
    temperature: float = 0.7
) -> dict:
    """ترکیب سرچ (با محتوای کامل) و تحلیل با LLM"""
    try:
        browser = ctx.request_context.lifespan_context.create_or_get_browser(
            ctx.client_id
        )
        
        # مرحله 1: جستجو
        search_messages = []
        async for message in browser.search(query=query, topn=topn):
            if message.content and hasattr(message.content[0], 'text'):
                search_messages.append(message.content[0].text)
        
        # مرحله 2: دریافت محتوای کامل
        content_messages = []
        async for message in browser.open(id=result_index, loc=0, num_lines=-1):
            if message.content and hasattr(message.content[0], 'text'):
                content_messages.append(message.content[0].text)
        
        full_content = "\n".join(content_messages)
        
        # مرحله 3: تحلیل با LLM
        app_ctx = ctx.request_context.lifespan_context
        llm_endpoint = app_ctx.user_cache.get("llm_endpoint")
        
        if not llm_endpoint:
            return {
                "success": True,
                "search_results": "\n".join(search_messages),
                "full_content": full_content,
                "analysis": None,
                "message": "Search completed but LLM not configured for analysis"
            }
        
        combined_prompt = f"""بر اساس محتوای زیر، {analysis_prompt}

محتوای کامل صفحه:
{full_content}
"""
        
        llm_result = chat_with_llm(
            ctx=ctx,
            message=combined_prompt,
            temperature=temperature,
            max_tokens=2000
        )
        
        return {
            "success": True,
            "search_query": query,
            "search_results": "\n".join(search_messages),
            "full_content": full_content,
            "analysis": llm_result.get("response") if llm_result.get("success") else None,
            "llm_error": llm_result.get("error") if not llm_result.get("success") else None
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool(
    name="get_status",
    title="Get system status",
    description="Check the current configuration and status of the intelligent search system.",
)
def get_status(ctx: Context) -> dict:
    """دریافت وضعیت سیستم"""
    app_ctx = ctx.request_context.lifespan_context
    
    return {
        "browser_sessions": len(app_ctx.browsers),
        "llm_configured": bool(app_ctx.user_cache.get("llm_endpoint")),
        "llm_endpoint": app_ctx.user_cache.get("llm_endpoint"),
        "llm_model": app_ctx.user_cache.get("model"),
        "cache_info": {
            "has_token": bool(app_ctx.user_cache.get("token")),
            "token_expires_at": app_ctx.user_cache.get("expires_at").isoformat()
                if app_ctx.user_cache.get("expires_at") else None
        }
    }