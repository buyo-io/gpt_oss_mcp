import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Union, Optional
from datetime import datetime, timedelta
from fastmcp import Context, FastMCP
from gpt_oss.tools.simple_browser import SimpleBrowserTool
from gpt_oss.tools.simple_browser.backend import YouComBackend, ExaBackend
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
            tool_backend = os.getenv("BROWSER_BACKEND", "exa")
            if tool_backend == "youcom":
                backend = YouComBackend(source="web")
            elif tool_backend == "exa":
                os.environ['EXA_API_KEY'] = "dbe54420-baba-48f4-abc7-e62f158d0586"  # Hardcoded Exa API key
                backend = ExaBackend(source="web")
            else:
                raise ValueError(f"Invalid tool backend: {tool_backend}")
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
For LLM chat: Use natural language to query the AI assistant for reasoning and analysis.
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
    description="Searches for information related to `query` and displays `topn` results from the web.",
)
async def search(
    ctx: Context,
    query: str,
    topn: int = 10,
    source: Optional[str] = None
) -> str:
    """جستجوی اطلاعات در وب"""
    browser = ctx.request_context.lifespan_context.create_or_get_browser(
        ctx.client_id
    )
    messages = []
    async for message in browser.search(query=query, topn=topn, source=source):
        if message.content and hasattr(message.content[0], 'text'):
            messages.append(message.content[0].text)
    return "\n".join(messages)

@mcp.tool(
    name="open",
    title="Open a link or page",
    description="""
Opens the link `id` from search results indicated by `cursor`, starting at line `loc`.
Shows `num_lines` lines. If `id` is a string, treats it as a full URL.
Use without `id` to scroll within the current page.
""".strip(),
)
async def open_link(
    ctx: Context,
    id: Union[int, str] = -1,
    cursor: int = -1,
    loc: int = -1,
    num_lines: int = -1,
    view_source: bool = False,
    source: Optional[str] = None
) -> str:
    """باز کردن لینک یا navigate در صفحه"""
    browser = ctx.request_context.lifespan_context.create_or_get_browser(
        ctx.client_id
    )
    messages = []
    async for message in browser.open(
        id=id,
        cursor=cursor,
        loc=loc,
        num_lines=num_lines,
        view_source=view_source,
        source=source
    ):
        if message.content and hasattr(message.content[0], 'text'):
            messages.append(message.content[0].text)
    return "\n".join(messages)

@mcp.tool(
    name="find",
    title="Find pattern in page",
    description="Finds exact matches of `pattern` in the current page or page given by `cursor`.",
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
# LLM CHAT TOOLS
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
    description="Send a message to the LLM and get a reasoned response. Use for analysis, reasoning, or synthesis of information.",
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
        
        # بررسی تنظیمات
        llm_endpoint = app_ctx.user_cache.get("llm_endpoint")
        if not llm_endpoint:
            return {
                "success": False,
                "error": "LLM endpoint not configured. Use setup_llm first."
            }
        
        api_key = app_ctx.user_cache.get("api_key")
        model = app_ctx.user_cache.get("model", "gpt-4")
        
        # ساخت headers
        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # ساخت payload
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
        
        # ارسال request
        response = requests.post(
            llm_endpoint,
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        
        # استخراج پاسخ
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
    description="Combines web search with LLM analysis. Searches for query, then uses LLM to analyze and synthesize results.",
)
async def search_and_analyze(
    ctx: Context,
    query: str,
    analysis_prompt: str,
    topn: int = 5,
    temperature: float = 0.7
) -> dict:
    """ترکیب سرچ و تحلیل با LLM"""
    try:
        # مرحله 1: سرچ کردن
        browser = ctx.request_context.lifespan_context.create_or_get_browser(
            ctx.client_id
        )
        
        search_messages = []
        async for message in browser.search(query=query, topn=topn):
            if message.content and hasattr(message.content[0], 'text'):
                search_messages.append(message.content[0].text)
        
        search_results = "\n".join(search_messages)
        
        # مرحله 2: تحلیل با LLM
        app_ctx = ctx.request_context.lifespan_context
        llm_endpoint = app_ctx.user_cache.get("llm_endpoint")
        
        if not llm_endpoint:
            return {
                "success": True,
                "search_results": search_results,
                "analysis": None,
                "message": "Search completed but LLM not configured for analysis"
            }
        
        # ارسال نتایج به LLM
        combined_prompt = f"""Based on the following search results, {analysis_prompt}
Search Results:
{search_results}
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
            "search_results": search_results,
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
