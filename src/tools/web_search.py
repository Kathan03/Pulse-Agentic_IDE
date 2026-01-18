"""
Tier 3 Intelligence Tool: Web Search via DuckDuckGo (Phase 3).

Provides web search capability for documentation research, Stack Overflow answers,
and technical resources when workspace search returns insufficient results.

Why DuckDuckGo:
- Free, no API key required
- Good for documentation and technical queries
- Privacy-focused

Implementation:
- Uses DDGS (Dux Distributed Global Search) library
- Returns results with title, URL, snippet
- Handles offline/rate-limit errors gracefully
- Bounded output (max 10 results, 500 char snippets)
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Check if DDGS is available
try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS = None
    DDGS_AVAILABLE = False
    logger.warning(
        "DDGS library not installed. Install with: pip install ddgs\n"
        "Web search functionality will be disabled."
    )


# ============================================================================
# TIER 3 TOOL: web_search
# ============================================================================

def web_search(
    query: str,
    num_results: int = 5,
    region: str = "us-en",
    safesearch: str = "moderate"
) -> List[Dict[str, Any]]:
    """
    Tier 3 tool: Search the web for documentation and technical resources.

    Uses DuckDuckGo metasearch to find current documentation, Stack Overflow
    answers, PLC manuals, and technical tutorials.

    Args:
        query: Search query (e.g., "Flet ExpansionTile documentation",
               "Siemens TIA Portal timer examples", "IEC 61131-3 TON timer").
        num_results: Number of results to return (default: 5, max: 10).
        region: Geographic region for results (default: "us-en").
        safesearch: Content filtering - "on", "moderate", or "off" (default: "moderate").

    Returns:
        List of dicts with keys:
            - title: str (result headline)
            - url: str (result URL)
            - snippet: str (brief description, max 500 chars)
            - source: str (always "web_search")

    Example:
        >>> results = web_search("Flet ExpansionTile documentation", num_results=3)
        >>> results[0]["title"]
        'ExpansionTile - Flet'
        >>> results[0]["url"]
        'https://flet.dev/docs/controls/expansiontile'
        >>> results[0]["snippet"][:50]
        'A single-line ListTile with an expansion arrow...'

    Error Handling:
        - If DDGS not installed: Returns error result
        - If network offline: Returns graceful error message
        - If rate limited: Returns rate limit notice
        - If search fails: Returns empty list with error logged

    Use Cases:
        - "How do I use Flet's ExpansionTile?" → Search flet.dev docs
        - "Siemens TIA Portal timer examples" → Find Siemens resources
        - "Python asyncio best practices 2025" → Stack Overflow + blogs
        - "IEC 61131-3 structured text syntax" → PLC documentation
    """
    logger.info(f"Web search query: {query} (num_results={num_results})")

    # Check if DDGS is available
    if not DDGS_AVAILABLE:
        logger.error("Web search failed: DDGS library not installed")
        return [{
            "title": "Web Search Unavailable",
            "url": "",
            "snippet": "Web search requires the 'ddgs' library. Install with: pip install ddgs",
            "source": "web_search",
            "error": "library_not_installed"
        }]

    # Validate num_results
    num_results = max(1, min(num_results, 10))  # Clamp to [1, 10]

    try:
        # Execute DuckDuckGo search
        ddgs = DDGS()
        raw_results = ddgs.text(
            query,
            region=region,
            safesearch=safesearch,
            max_results=num_results
        )

        # Format results
        formatted_results = []
        for result in raw_results:
            # Extract fields (DDGS returns: title, href, body)
            title = result.get("title", "No title")
            url = result.get("href", "")
            body = result.get("body", "")

            # Truncate snippet to 500 chars
            snippet = body[:500] + ("..." if len(body) > 500 else "")

            formatted_results.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": "web_search"
            })

        logger.info(f"Web search returned {len(formatted_results)} results")
        return formatted_results

    except Exception as e:
        error_msg = str(e).lower()

        # Handle specific error types
        if "rate" in error_msg or "limit" in error_msg:
            logger.warning(f"Web search rate limited: {e}")
            return [{
                "title": "Search Rate Limited",
                "url": "",
                "snippet": (
                    "DuckDuckGo search is temporarily rate limited. "
                    "Please try again in a few moments, or check the official documentation directly."
                ),
                "source": "web_search",
                "error": "rate_limited"
            }]

        elif "network" in error_msg or "connection" in error_msg or "timeout" in error_msg:
            logger.warning(f"Web search network error: {e}")
            return [{
                "title": "Network Error",
                "url": "",
                "snippet": (
                    "Could not connect to the internet. Please check your network connection. "
                    "I'll answer based on my training data instead."
                ),
                "source": "web_search",
                "error": "network_error"
            }]

        else:
            # Generic error
            logger.error(f"Web search failed: {e}", exc_info=True)
            return [{
                "title": "Search Failed",
                "url": "",
                "snippet": f"Web search encountered an error: {str(e)}",
                "source": "web_search",
                "error": "unknown_error"
            }]


def format_search_results_for_llm(results: List[Dict[str, Any]]) -> str:
    """
    Format web search results for LLM consumption.

    Args:
        results: List of search result dicts from web_search().

    Returns:
        Formatted string with numbered results, titles, URLs, and snippets.

    Example:
        >>> results = web_search("Flet ExpansionTile", num_results=2)
        >>> formatted = format_search_results_for_llm(results)
        >>> print(formatted)
        Web Search Results for "Flet ExpansionTile":

        1. ExpansionTile - Flet
           URL: https://flet.dev/docs/controls/expansiontile
           A single-line ListTile with an expansion arrow icon...

        2. Flet Controls - Flet Documentation
           URL: https://flet.dev/docs/controls
           Complete reference of all Flet controls including ExpansionTile...
    """
    if not results:
        return "No web search results found."

    # Check for error results
    if len(results) == 1 and "error" in results[0]:
        error_result = results[0]
        return f"Web Search Error: {error_result['snippet']}"

    # Format results
    lines = []
    for i, result in enumerate(results, start=1):
        lines.append(f"{i}. {result['title']}")
        if result.get('url'):
            lines.append(f"   URL: {result['url']}")
        lines.append(f"   {result['snippet']}")
        lines.append("")  # Blank line between results

    return "\n".join(lines)


__all__ = [
    "web_search",
    "format_search_results_for_llm",
]
