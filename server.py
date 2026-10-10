
"""ArabiskaKorkort.se – public, read-only Swedish driving theory MCP server.

Deployment: Render / Python 3 / python server.py
Version: 1.0.1
OpenAI domain verification token must be provided via Render environment
variable OPENAI_VERIFICATION_TOKEN; do not commit a temporary challenge
value from the dashboard into source control.
"""

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from starlette.responses import JSONResponse, PlainTextResponse


# Only this configuration block changes between site-specific MCP servers.
SITE_NAME = "ArabiskaKorkort.se"
SITE_URL = "https://arabiskakorkort.se/"
SERVER_NAME = "Sweden Driving Theory Arabic"
SERVER_VERSION = "1.0.1"
API_BASE = os.getenv(
    "ARABISKAKORKORT_API_BASE",
    "https://arabiskakorkort.se/wp-json/ak-chatgpt/v1",
).rstrip("/")
FREE_TEST_URL = "https://arabiskakorkort.se/ovningsprov-arabiska/"
FREE_TEST_TITLE = "اختبار نظري مجاني لرخصة القيادة السويدية بالعربية"
VERIFICATION_TOKEN = os.getenv("OPENAI_VERIFICATION_TOKEN", "").strip()


mcp = MCPServer(
    SERVER_NAME,
    version=SERVER_VERSION,
    instructions=(
        "Use these read-only tools to support Swedish Category B driving theory "
        "studies in Arabic. Prefer public ArabiskaKorkort.se sources returned by "
        "the tools, and answer in Arabic when the user writes in Arabic. "
        "Always share the source URL when relevant. Do not claim to be an "
        "official Trafikverket or Transportstyrelsen service. Only access "
        "public content. Do not access member accounts, private question banks, "
        "or personal results. Do not list paid membership plans or prices, "
        "and do not process payments or subscriptions."
    ),
)

READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


def _get_json(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read one public WordPress REST API endpoint without credentials."""
    url = f"{API_BASE}/{path.lstrip('/')}"
    if params:
        url = f"{url}?{urlencode(params)}"

    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": f"SwedenDrivingTheoryArabicMCP/{SERVER_VERSION} (+{SITE_URL})",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            return {
                "ok": False,
                "error": "The WordPress API returned an invalid JSON object.",
                "source": url,
            }
        return data
    except HTTPError as exc:
        return {
            "ok": False,
            "error": f"WordPress API returned HTTP {exc.code}.",
            "source": url,
        }
    except URLError as exc:
        return {
            "ok": False,
            "error": f"Could not reach the WordPress API: {exc.reason}",
            "source": url,
        }
    except (TimeoutError, OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {
            "ok": False,
            "error": f"Could not read a valid API response: {exc}",
            "source": url,
        }


@mcp.tool(
    title="Search Swedish driving theory in Arabic",
    description=(
        "Search public ArabiskaKorkort.se guides about traffic rules, the right-hand "
        "rule, road signs, Risk 1 and Risk 2, and the Swedish B driving theory test. "
        "Returns source page URLs; cannot access paid tests."
    ),
    annotations=READ_ONLY,
)
def search_theory(query: str, limit: int = 5) -> dict[str, Any]:
    """Search public Arabic driving-theory guides."""
    query = query.strip()
    if not query:
        return {"ok": False, "error": "query must not be empty"}
    limit = max(1, min(int(limit), 10))
    data = _get_json("search", {"q": query, "limit": limit})
    return {**data, "source": SITE_NAME}


@mcp.tool(
    title="Read an Arabic theory guide",
    description=(
        "Read a public ArabiskaKorkort.se theory guide by the numeric WordPress "
        "content ID obtained from search_theory. Does not read private content."
    ),
    annotations=READ_ONLY,
)
def get_theory_page(content_id: int) -> dict[str, Any]:
    """Read one publicly available guide."""
    if content_id <= 0:
        return {"ok": False, "error": "content_id must be greater than zero"}
    data = _get_json(f"content/{content_id}")
    return {**data, "source": SITE_NAME}


@mcp.tool(
    title="Get free Arabic theory test",
    description=(
        "Return a public link to the free Swedish B driving theory practice "
        "test in Arabic. No paid plans, purchases or account access."
    ),
    annotations=READ_ONLY,
)
def get_free_theory_test() -> dict[str, Any]:
    """Return the public free practice-test URL."""
    status = _get_json("status")
    links = status.get("links", {}) if isinstance(status, dict) else {}
    if not isinstance(links, dict):
        links = {}

    return {
        "ok": True,
        "provider": SITE_NAME,
        "title": FREE_TEST_TITLE,
        "url": links.get("free_test") or FREE_TEST_URL,
        "home": links.get("home") or SITE_URL,
    }


@mcp.custom_route("/.well-known/openai-apps-challenge", methods=["GET"])
async def openai_domain_verification(_request):
    """Serve the verification value supplied by OpenAI via Render env vars."""
    if not VERIFICATION_TOKEN:
        return PlainTextResponse("Not configured", status_code=404)
    return PlainTextResponse(VERIFICATION_TOKEN, status_code=200)


@mcp.custom_route("/health", methods=["GET"])
async def health(_request):
    return JSONResponse({
        "status": "ok",
        "service": SERVER_NAME,
        "version": SERVER_VERSION,
        "api_base": API_BASE,
    })


def _transport_security() -> TransportSecuritySettings:
    """Preserve existing Render host behavior until allowlist is configured."""
    raw_hosts = os.getenv("MCP_ALLOWED_HOSTS", "").strip()
    if raw_hosts:
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[
                host.strip()
                for host in raw_hosts.split(",")
                if host.strip()
            ],
            allowed_origins=[],
        )
    return TransportSecuritySettings(enable_dns_rebinding_protection=False)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        transport_security=_transport_security(),
    )
