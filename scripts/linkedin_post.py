"""
Post content to LinkedIn via the LinkedIn API.

Prerequisites:
1. Create a LinkedIn Developer App at https://www.linkedin.com/developers/apps
2. Enable the "Share on LinkedIn" and "Sign In with LinkedIn" products
3. Add a redirect URL (e.g. http://localhost:8000/callback) in your app's Auth tab
4. Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET as environment variables

Usage:
    # First run: opens browser for OAuth consent, saves token
    python scripts/linkedin_post.py --auth

    # Post markdown file as a LinkedIn post
    python scripts/linkedin_post.py --file docs/linkedin-post.md

    # Post with a custom title (for article mode)
    python scripts/linkedin_post.py --file docs/linkedin-post.md --title "My Article Title"
"""

import argparse
import json
import os
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread
from urllib.parse import urlencode, urlparse, parse_qs

import requests

# --- Config ---
CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_PORT = 8000
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
TOKEN_FILE = Path(__file__).parent / ".linkedin_token.json"
SCOPES = ["w_member_social", "openid", "profile", "email"]

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
POSTS_URL = "https://api.linkedin.com/rest/posts"
ME_URL = "https://api.linkedin.com/v2/userinfo"


def check_credentials():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET environment variables.")
        print("Create an app at https://www.linkedin.com/developers/apps")
        sys.exit(1)


def save_token(token_data: dict):
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2))
    print(f"Token saved to {TOKEN_FILE}")


def load_token() -> dict | None:
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return None


def get_authorization_code() -> str:
    """Open browser for OAuth consent and capture the auth code via local server."""
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "state": "linkedin_post_tool",
    }
    auth_url = f"{AUTH_URL}?{urlencode(params)}"

    code_holder = {"code": None, "error": None}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            if "code" in qs:
                code_holder["code"] = qs["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Authorization successful! You can close this tab.</h1>")
            elif "error" in qs:
                code_holder["error"] = qs.get("error_description", qs["error"])[0]
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(f"<h1>Error: {code_holder['error']}</h1>".encode())
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):
            pass  # suppress request logs

    server = HTTPServer(("localhost", REDIRECT_PORT), CallbackHandler)
    server_thread = Thread(target=server.handle_request, daemon=True)

    print(f"Opening browser for LinkedIn authorization...")
    print(f"If it doesn't open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)
    server_thread.start()
    server_thread.join(timeout=120)
    server.server_close()

    if code_holder["error"]:
        print(f"Authorization error: {code_holder['error']}")
        sys.exit(1)
    if not code_holder["code"]:
        print("Authorization timed out.")
        sys.exit(1)

    return code_holder["code"]


def exchange_code_for_token(code: str) -> dict:
    """Exchange authorization code for access token."""
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    return resp.json()


def refresh_token(token_data: dict) -> dict:
    """Refresh an expired access token."""
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": token_data["refresh_token"],
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    new_token = resp.json()
    new_token.setdefault("refresh_token", token_data.get("refresh_token"))
    return new_token


def get_user_urn(access_token: str) -> str:
    """Get the authenticated user's LinkedIn URN."""
    resp = requests.get(ME_URL, headers={
        "Authorization": f"Bearer {access_token}",
    })
    resp.raise_for_status()
    data = resp.json()
    return f"urn:li:person:{data['sub']}"


def get_valid_token() -> tuple[str, str]:
    """Returns (access_token, user_urn), refreshing if needed."""
    check_credentials()
    token_data = load_token()
    if not token_data:
        print("No token found. Run with --auth first.")
        sys.exit(1)

    # Try refreshing if we have a refresh token
    try:
        refreshed = refresh_token(token_data)
        save_token(refreshed)
        access_token = refreshed["access_token"]
    except requests.HTTPError:
        # Refresh token may be expired; fall back to existing access token
        access_token = token_data["access_token"]

    user_urn = get_user_urn(access_token)
    return access_token, user_urn


def markdown_to_linkedin_text(md_content: str) -> str:
    """Convert markdown to LinkedIn-friendly plain text (basic conversion)."""
    import re
    lines = md_content.strip().split("\n")
    result = []
    for line in lines:
        # Skip YAML front matter
        if line.strip() == "---":
            continue
        # Headers -> bold text with newlines
        if line.startswith("#"):
            text = re.sub(r"^#+\s*", "", line).strip()
            result.append(f"\n{text}\n")
            continue
        # Horizontal rules -> spacing
        if line.strip() in ("---", "***", "___"):
            result.append("\n")
            continue
        # Bold/italic markers kept as-is (LinkedIn supports *bold* and _italic_)
        # Strip markdown link syntax but keep text
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        result.append(line)

    text = "\n".join(result)
    # Clean up excessive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def post_to_linkedin(access_token: str, user_urn: str, text: str, title: str | None = None):
    """Post content to LinkedIn using the Posts API."""
    payload = {
        "author": user_urn,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
        },
        "lifecycleState": "PUBLISHED",
    }

    if title:
        # Article mode — title creates a rich preview
        payload["content"] = {
            "article": {
                "title": title,
                "description": text[:200] + "..." if len(text) > 200 else text,
            }
        }
        # For articles, commentary becomes the share text
        payload["commentary"] = title

    resp = requests.post(POSTS_URL, headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": "202401",
        "X-Restli-Protocol-Version": "2.0.0",
    }, json=payload)

    if resp.status_code in (200, 201):
        post_id = resp.headers.get("x-restli-id", "unknown")
        print(f"✅ Post published successfully! (ID: {post_id})")
        print(f"   View at: https://www.linkedin.com/feed/update/{post_id}")
    else:
        print(f"❌ Failed to post (HTTP {resp.status_code})")
        print(f"   Response: {resp.text}")
        sys.exit(1)


def auth_flow():
    check_credentials()
    code = get_authorization_code()
    token_data = exchange_code_for_token(code)
    save_token(token_data)
    print("✅ Authorization complete! You can now post with --file.")


def main():
    parser = argparse.ArgumentParser(description="Post content to LinkedIn")
    parser.add_argument("--auth", action="store_true", help="Run OAuth authorization flow")
    parser.add_argument("--file", type=str, help="Markdown file to post")
    parser.add_argument("--title", type=str, help="Title for article-style post")
    parser.add_argument("--dry-run", action="store_true", help="Preview text without posting")
    args = parser.parse_args()

    if args.auth:
        auth_flow()
        return

    if not args.file:
        parser.error("--file is required (or use --auth)")

    md_content = Path(args.file).read_text(encoding="utf-8")
    text = markdown_to_linkedin_text(md_content)

    if args.dry_run:
        print("=== DRY RUN — LinkedIn post text ===\n")
        print(text)
        print(f"\n=== ({len(text)} characters) ===")
        return

    access_token, user_urn = get_valid_token()
    post_to_linkedin(access_token, user_urn, text, title=args.title)


if __name__ == "__main__":
    main()
