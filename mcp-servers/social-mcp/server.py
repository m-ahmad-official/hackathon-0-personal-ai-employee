#!/usr/bin/env python3
"""
Social Media MCP Server - Gold Tier Phase 2 (with Phase 3 Error Recovery)
Integrates Facebook, Instagram, and Twitter (X) via their APIs.

Platforms:
- Facebook Graph API (Page posting)
- Instagram Graph API (Business Account)
- Twitter X API v2 (User posting)

All credentials via environment variables.
"""

import os
import sys
import json
import logging
import time
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.types import Tool as ToolDefinition, CallToolRequest
from datetime import datetime

# Configure logging BEFORE any potential use
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("social-mcp")

# Add parent directory to path for error recovery utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'utils', 'error_recovery'))
try:
    from retry_circuit import with_retry, with_circuit_breaker, CircuitBreaker, CircuitState
    _error_recovery_available = True
except ImportError:
    _error_recovery_available = False
    logger.warning("Error recovery utilities not available, using basic retry")

# Add parent directory to path for audit logger
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'utils', 'audit'))
try:
    from logger import log_audit, get_audit_logger
    _audit_logger_available = True
except ImportError:
    _audit_logger_available = False
    logger.warning("Audit logger not available, skipping audit trail")

# Configuration from environment
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "")
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
INSTAGRAM_BUSINESS_ID = os.getenv("INSTAGRAM_BUSINESS_ID", "")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "")

# Circuit breaker instances
_breakers: Dict[str, CircuitBreaker] = {}

class SocialMediaMCPServer:
    """MCP Server for Social Media integrations."""

    def __init__(self):
        self.server = Server("social-mcp")
        self._setup_routes()
        # Find project root (directory containing AI_Employee_Vault)
        current_file = os.path.abspath(__file__)
        self.project_root = None
        for parent in [Path(current_file).parent] + list(Path(current_file).parents)[:10]:
            if (parent / "AI_Employee_Vault").exists():
                self.project_root = parent
                break

    def _create_receipt(self, platform: str, action: str, external_id: str, url: str,
                       parameters: Dict, result: Dict, duration_ms: Optional[int] = None):
        """Create a receipt file in the Done folder."""
        if not self.project_root:
            logger.warning("Project root not found, cannot create receipt")
            return

        done_dir = self.project_root / "AI_Employee_Vault" / "Done"
        done_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
        filename = f"{platform.upper()}_{action.upper()}_{timestamp}.md"
        filepath = done_dir / filename

        # Build frontmatter
        frontmatter = {
            "type": "external_action",
            "platform": platform,
            "action": action,
            "external_id": external_id,
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": duration_ms
        }

        # Format parameters and result for readability
        params_str = json.dumps(parameters, indent=2) if parameters else "None"
        result_str = json.dumps(result, indent=2) if result else "None"

        content = f"""---
{json.dumps(frontmatter, indent=2)[1:-1]}
---

# External Action Receipt

**Platform:** {platform}
**Action:** {action}
**External ID:** {external_id}
**URL:** {url}
**Completed:** {frontmatter['timestamp']}
{f"**Duration:** {duration_ms}ms" if duration_ms else ""}

## Parameters
```json
{params_str}
```

## Result
```json
{result_str}
```
"""

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Created receipt: {filepath}")
        except Exception as e:
            logger.warning(f"Failed to write receipt: {e}")

    def _setup_routes(self):
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> List[ToolDefinition]:
            """Return available social media tools."""
            tools = []

            # Facebook tools
            if FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN:
                tools.extend([
                    ToolDefinition(
                        name="facebook_post",
                        description="Post a message to Facebook Page",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "message": {"type": "string", "description": "Text message to post"},
                                "link": {"type": "string", "description": "Optional URL to share"},
                                "media_url": {"type": "string", "description": "Optional image/video URL"}
                            },
                            "required": ["message"]
                        }
                    ),
                    ToolDefinition(
                        name="facebook_get_insights",
                        description="Get page insights (reach, engagement, followers)",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "period": {"type": "string", "description": "Period: day, week, month (default: week)"}
                            }
                        }
                    )
                ])

            # Instagram tools
            if INSTAGRAM_BUSINESS_ID and FACEBOOK_ACCESS_TOKEN:
                tools.append(
                    ToolDefinition(
                        name="instagram_post",
                        description="Post an image with caption to Instagram Business",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "image_url": {"type": "string", "description": "Public URL of the image to post"},
                                "caption": {"type": "string", "description": "Caption for the post"},
                                "alt_text": {"type": "string", "description": "Accessibility alt text"}
                            },
                            "required": ["image_url", "caption"]
                        }
                    )
                )

            # Twitter tools
            if TWITTER_BEARER_TOKEN:
                tools.extend([
                    ToolDefinition(
                        name="twitter_tweet",
                        description="Post a tweet (text, optionally with media)",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "text": {"type": "string", "description": "Tweet text (max 280 chars)"},
                                "media_url": {"type": "string", "description": "Optional media URL to attach"}
                            },
                            "required": ["text"]
                        }
                    ),
                    ToolDefinition(
                        name="twitter_get_timeline",
                        description="Get recent tweets from your timeline",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "count": {"type": "integer", "description": "Number of tweets (default 10, max 100)"}
                            }
                        }
                    ),
                    ToolDefinition(
                        name="twitter_get_mentions",
                        description="Get recent mentions of your account",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "count": {"type": "integer", "description": "Number of mentions (default 10)"}
                            }
                        }
                    )
                ])

            return tools

        @self.server.call_tool()
        async def call_tool(request: CallToolRequest) -> List[Dict[str, Any]]:
            """Handle tool invocations."""
            import time as _time
            tool_name = request.params.name
            arguments = request.params.arguments or {}
            start_time = _time.time()

            try:
                # Route to appropriate handler
                if tool_name == "facebook_post":
                    result = self._facebook_post(**arguments)
                elif tool_name == "facebook_get_insights":
                    result = self._facebook_get_insights(**arguments)
                elif tool_name == "instagram_post":
                    result = self._instagram_post(**arguments)
                elif tool_name == "twitter_tweet":
                    result = self._twitter_tweet(**arguments)
                elif tool_name == "twitter_get_timeline":
                    result = self._twitter_get_timeline(**arguments)
                elif tool_name == "twitter_get_mentions":
                    result = self._twitter_get_mentions(**arguments)
                else:
                    return [{"type": "error", "text": f"Unknown tool: {tool_name}"}]

                duration_ms = int((_time.time() - start_time) * 1000)

                # Audit logging
                if _audit_logger_available:
                    try:
                        log_audit(
                            actor="social-mcp",
                            action=tool_name,
                            target=result.get("post_id") or result.get("tweet_id") or result.get("media_id"),
                            parameters=arguments,
                            result=result,
                            duration_ms=duration_ms
                        )
                    except Exception as audit_error:
                        logger.warning(f"Failed to write audit log: {audit_error}")

                return [{"type": "text", "text": json.dumps(result, indent=2)}]

            except Exception as e:
                duration_ms = int((_time.time() - start_time) * 1000)
                logger.error(f"Error in {tool_name}: {e}", exc_info=True)

                # Audit logging for errors
                if _audit_logger_available:
                    try:
                        log_audit(
                            actor="social-mcp",
                            action=tool_name,
                            parameters=arguments,
                            error=str(e),
                            duration_ms=duration_ms,
                            level="error"
                        )
                    except Exception as audit_error:
                        logger.warning(f"Failed to write audit log: {audit_error}")

                return [{"type": "error", "text": f"Error: {str(e)}"}]

    # === Facebook Methods ===

    def _get_circuit_breaker(self, platform: str) -> CircuitBreaker:
        """Get or create circuit breaker for a platform."""
        global _breakers
        if platform not in _breakers and _error_recovery_available:
            _breakers[platform] = CircuitBreaker(
                name=f"{platform}_api",
                failure_threshold=5,
                recovery_timeout=60,
                success_threshold=3,
                expected_exceptions=(ConnectionError, requests.exceptions.RequestException, TimeoutError)
            )
        return _breakers.get(platform)

    def _facebook_post(self, message: str, link: Optional[str] = None, media_url: Optional[str] = None) -> Dict:
        """Post to Facebook Page with retry and circuit breaker."""
        if not FACEBOOK_PAGE_ID or not FACEBOOK_ACCESS_TOKEN:
            raise Exception("Facebook credentials not configured")

        start_time = time.time()
        breaker = self._get_circuit_breaker("facebook")

        def do_post():
            url = f"https://graph.facebook.com/v20.0/{FACEBOOK_PAGE_ID}/feed"
            params = {
                "message": message,
                "access_token": FACEBOOK_ACCESS_TOKEN
            }
            if link:
                params["link"] = link
            if media_url:
                # For photos, use /photos endpoint
                url = f"https://graph.facebook.com/v20.0/{FACEBOOK_PAGE_ID}/photos"
                params["url"] = media_url

            response = requests.post(url, data=params, timeout=30)
            response.raise_for_status()
            return response.json()

        if breaker:
            # Use circuit breaker with retry
            max_attempts = 3
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    # Check circuit breaker state before calling
                    if breaker.state.value == "open":
                        raise Exception(f"Circuit breaker '{breaker.name}' is OPEN - Facebook API unavailable")

                    result = breaker.call(do_post)
                    # On success, circuit breaker automatically handles state transitions

                    post_id = result.get("id")
                    logger.info(f"Posted to Facebook: {post_id}")

                    # Audit logging (direct call to bypass MCP layer)
                    if _audit_logger_available:
                        try:
                            log_audit(
                                actor="social-mcp",
                                action="facebook_post",
                                target=post_id,
                                parameters={"message": message[:100], "link": link},
                                result={"post_id": post_id, "url": f"https://facebook.com/{post_id}"},
                                duration_ms=int((time.time() - start_time) * 1000) if 'start_time' in locals() else None
                            )
                        except Exception as audit_error:
                            logger.warning(f"Failed to write audit log: {audit_error}")

                    # Create receipt in Done folder
                    self._create_receipt(
                        platform="facebook",
                        action="post",
                        external_id=post_id,
                        url=f"https://facebook.com/{post_id}",
                        parameters={"message": message, "link": link},
                        result={"post_id": post_id},
                        duration_ms=int((time.time() - start_time) * 1000) if 'start_time' in locals() else None
                    )

                    return {
                        "success": True,
                        "platform": "facebook",
                        "post_id": post_id,
                        "url": f"https://facebook.com/{post_id}"
                    }

                except requests.exceptions.RequestException as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        break
                    # Exponential backoff
                    delay = min(2 ** attempt, 60)
                    time.sleep(delay)

            # All retries exhausted
            raise Exception(f"Facebook post failed after {max_attempts} attempts: {last_exception}")

        else:
            # Fallback: direct call without retry/circuit breaker
            result = do_post()
            post_id = result.get("id")
            logger.info(f"Posted to Facebook: {post_id}")

            # Audit logging
            if _audit_logger_available:
                try:
                    log_audit(
                        actor="social-mcp",
                        action="facebook_post",
                        target=post_id,
                        parameters={"message": message[:100], "link": link},
                        result={"post_id": post_id, "url": f"https://facebook.com/{post_id}"},
                        duration_ms=int((time.time() - start_time) * 1000) if 'start_time' in locals() else None
                    )
                except Exception as audit_error:
                    logger.warning(f"Failed to write audit log: {audit_error}")

            # Create receipt
            self._create_receipt(
                platform="facebook",
                action="post",
                external_id=post_id,
                url=f"https://facebook.com/{post_id}",
                parameters={"message": message, "link": link},
                result={"post_id": post_id},
                duration_ms=int((time.time() - start_time) * 1000) if 'start_time' in locals() else None
            )

            return {
                "success": True,
                "platform": "facebook",
                "post_id": post_id,
                "url": f"https://facebook.com/{post_id}"
            }

    def _facebook_get_insights(self, period: str = "week") -> Dict:
        """Get Facebook Page insights with retry."""
        if not FACEBOOK_PAGE_ID or not FACEBOOK_ACCESS_TOKEN:
            raise Exception("Facebook credentials not configured")

        breaker = self._get_circuit_breaker("facebook")

        def do_get():
            page_id = FACEBOOK_PAGE_ID
            url = f"https://graph.facebook.com/{page_id}/insights"
            params = {
                "access_token": FACEBOOK_ACCESS_TOKEN,
                "period": period
            }
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()

        if breaker:
            max_attempts = 3
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    if breaker.state.value == "open":
                        raise Exception(f"Circuit breaker '{breaker.name}' is OPEN")

                    data = breaker.call(do_get)

                    insights = {}
                    for item in data.get("data", []):
                        insights[item["name"]] = {
                            "value": item["values"][0]["value"] if item["values"] else None,
                            "period": item["period"]
                        }

                    return {
                        "platform": "facebook",
                        "page_id": FACEBOOK_PAGE_ID,
                        "period": period,
                        "insights": insights
                    }

                except requests.exceptions.RequestException as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        break
                    delay = min(2 ** attempt, 60)
                    time.sleep(delay)

            raise Exception(f"Facebook insights failed after {max_attempts} attempts: {last_exception}")

        else:
            data = do_get()
            insights = {}
            for item in data.get("data", []):
                insights[item["name"]] = {
                    "value": item["values"][0]["value"] if item["values"] else None,
                    "period": item["period"]
                }
            return {
                "platform": "facebook",
                "page_id": FACEBOOK_PAGE_ID,
                "period": period,
                "insights": insights
            }

    # === Instagram Methods ===

    def _instagram_post(self, image_url: str, caption: str, alt_text: Optional[str] = None) -> Dict:
        """Post to Instagram Business Account with retry."""
        if not INSTAGRAM_BUSINESS_ID or not FACEBOOK_ACCESS_TOKEN:
            raise Exception("Instagram credentials not configured")

        start_time = time.time()
        breaker = self._get_circuit_breaker("instagram")

        def do_create_container():
            url = f"https://graph.facebook.com/{INSTAGRAM_BUSINESS_ID}/media"
            params = {
                "image_url": image_url,
                "caption": caption,
                "access_token": FACEBOOK_ACCESS_TOKEN
            }
            if alt_text:
                params["alt_text"] = alt_text
            response = requests.post(url, data=params, timeout=30)
            response.raise_for_status()
            return response.json()

        def do_publish(container_id: str):
            publish_url = f"https://graph.facebook.com/{INSTAGRAM_BUSINESS_ID}/media_publish"
            publish_params = {
                "creation_id": container_id,
                "access_token": FACEBOOK_ACCESS_TOKEN
            }
            response = requests.post(publish_url, data=publish_params, timeout=30)
            response.raise_for_status()
            return response.json()

        if breaker:
            # Retry container creation
            max_attempts = 3
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    if breaker.state.value == "open":
                        raise Exception(f"Circuit breaker '{breaker.name}' is OPEN")

                    container = breaker.call(do_create_container)
                    container_id = container["id"]
                    break
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        raise Exception(f"Instagram container creation failed: {last_exception}")
                    delay = min(2 ** attempt, 60)
                    time.sleep(delay)

            # Retry publish (usually quicker, fewer failures)
            try:
                result = do_publish(container_id)
            except requests.exceptions.RequestException as e:
                raise Exception(f"Instagram publish failed: {e}")

        else:
            container = do_create_container()
            container_id = container["id"]
            result = do_publish(container_id)

        media_id = result.get("id")
        logger.info(f"Posted to Instagram: {media_id}")

        # Audit logging (direct call to bypass MCP layer)
        if _audit_logger_available:
            try:
                log_audit(
                    actor="social-mcp",
                    action="instagram_post",
                    target=media_id,
                    parameters={"image_url": image_url[:100] if len(image_url) > 100 else image_url, "caption": caption[:100]},
                    result={"media_id": media_id, "container_id": container_id, "url": f"https://instagram.com/p/{media_id}"},
                    duration_ms=int((time.time() - start_time) * 1000) if 'start_time' in locals() else None
                )
            except Exception as audit_error:
                logger.warning(f"Failed to write audit log: {audit_error}")

        # Create receipt in Done folder
        self._create_receipt(
            platform="instagram",
            action="post",
            external_id=media_id,
            url=f"https://instagram.com/p/{media_id}",
            parameters={"image_url": image_url, "caption": caption, "alt_text": alt_text},
            result={"media_id": media_id, "container_id": container_id},
            duration_ms=int((time.time() - start_time) * 1000) if 'start_time' in locals() else None
        )

        return {
            "success": True,
            "platform": "instagram",
            "media_id": media_id,
            "container_id": container_id,
            "url": f"https://instagram.com/p/{media_id}"
        }

    # === Twitter (X) Methods ===

    def _twitter_tweet(self, text: str, media_url: Optional[str] = None) -> Dict:
        """Post a tweet with OAuth 1.0a, retry, and circuit breaker."""
        if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
            raise Exception("Twitter OAuth 1.0a credentials required for posting (API key/secret + access token/secret)")

        breaker = self._get_circuit_breaker("twitter")

        def do_tweet():
            from requests_oauthlib import OAuth1
            url = "https://api.twitter.com/2/tweets"
            payload = {"text": text}
            # Note: Media attachment requires separate upload flow - not implemented here
            headers = {}

            auth = OAuth1(
                client_key=TWITTER_API_KEY,
                client_secret=TWITTER_API_SECRET,
                resource_owner_key=TWITTER_ACCESS_TOKEN,
                resource_owner_secret=TWITTER_ACCESS_SECRET
            )

            response = requests.post(url, json=payload, auth=auth, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()

        if breaker:
            max_attempts = 3
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    if breaker.state.value == "open":
                        raise Exception(f"Circuit breaker '{breaker.name}' is OPEN")

                    result = breaker.call(do_tweet)
                    tweet_id = result["data"]["id"]
                    logger.info(f"Posted to Twitter: {tweet_id}")

                    return {
                        "success": True,
                        "platform": "twitter",
                        "tweet_id": tweet_id,
                        "url": f"https://twitter.com/i/web/status/{tweet_id}"
                    }

                except requests.exceptions.RequestException as e:
                    last_exception = e
                    # Handle rate limits specifically - wait for reset even within retry loop
                    if hasattr(e, 'response') and e.response is not None:
                        if e.response.status_code == 429:
                            reset_time = int(e.response.headers.get('x-rate-limit-reset', time.time() + 60))
                            wait_time = max(reset_time - time.time(), 0)
                            logger.warning(f"Twitter rate limit hit, waiting {wait_time}s")
                            time.sleep(wait_time)
                            # Don't count this as a retry attempt? Continue loop
                            continue
                        elif e.response.status_code >= 500:
                            # Server error, retry with backoff
                            if attempt < max_attempts - 1:
                                delay = 2 ** attempt
                                logger.warning(f"Twitter server error, retrying in {delay}s")
                                time.sleep(delay)
                                continue

                    if attempt == max_attempts - 1:
                        break
                    delay = min(2 ** attempt, 60)
                    time.sleep(delay)

            raise Exception(f"Twitter tweet failed after {max_attempts} attempts: {last_exception}")

        else:
            result = do_tweet()
            tweet_id = result["data"]["id"]
            logger.info(f"Posted to Twitter: {tweet_id}")

            return {
                "success": True,
                "platform": "twitter",
                "tweet_id": tweet_id,
                "url": f"https://twitter.com/i/web/status/{tweet_id}"
            }

    def _twitter_get_timeline(self, count: int = 10) -> Dict:
        """Get recent tweets from user's timeline with circuit breaker."""
        if not TWITTER_BEARER_TOKEN:
            raise Exception("Twitter Bearer Token not configured")

        breaker = self._get_circuit_breaker("twitter")

        def do_get_timeline():
            url = "https://api.twitter.com/2/users/me/timeline/reverse_chronological"
            headers = {
                "Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"
            }
            params = {
                "max_results": min(count, 100)
            }
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()

        if breaker:
            try:
                result = breaker.call(do_get_timeline)
            except Exception as e:
                logger.error(f"Twitter timeline fetch failed: {e}")
                raise
        else:
            result = do_get_timeline()

        tweets = []
        for item in result.get("data", []):
            tweets.append({
                "id": item["id"],
                "text": item["text"],
                "created_at": item.get("created_at"),
                "public_metrics": item.get("public_metrics", {})
            })

        return {
            "platform": "twitter",
            "count": len(tweets),
            "tweets": tweets
        }

    def _twitter_get_mentions(self, count: int = 10) -> Dict:
        """Get recent mentions with circuit breaker."""
        if not TWITTER_BEARER_TOKEN:
            raise Exception("Twitter Bearer Token not configured")

        breaker = self._get_circuit_breaker("twitter")

        def do_get_user():
            user_url = "https://api.twitter.com/2/users/me"
            headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
            user_resp = requests.get(user_url, headers=headers, timeout=30)
            user_resp.raise_for_status()
            return user_resp.json()["data"]["id"]

        def do_get_mentions(user_id: str):
            url = f"https://api.twitter.com/2/users/{user_id}/mentions"
            headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
            params = {"max_results": min(count, 100)}
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()

        if breaker:
            try:
                user_id = do_get_user()  # Getting user ID is quick, no retry needed but could be wrapped
                result = breaker.call(do_get_mentions, user_id)
            except Exception as e:
                logger.error(f"Twitter mentions fetch failed: {e}")
                raise
        else:
            user_id = do_get_user()
            result = do_get_mentions(user_id)

        mentions = []
        for item in result.get("data", []):
            mentions.append({
                "id": item["id"],
                "text": item["text"],
                "author_id": item.get("author_id"),
                "created_at": item.get("created_at")
            })

        return {
            "platform": "twitter",
            "user_id": user_id,
            "count": len(mentions),
            "mentions": mentions
        }

    async def run(self):
        """Run the MCP server."""
        from mcp.server.stdio import stdio_server
        logger.info("Starting Social Media MCP Server...")
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Social Media MCP Server is running")
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Entry point for the Social Media MCP server."""
    server = SocialMediaMCPServer()
    import asyncio
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
