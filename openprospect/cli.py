from .config import env_value
import argparse, os, webbrowser
from dotenv import load_dotenv
import uvicorn
from .db import list_companies
from .training import train_website


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(prog="zero-hawk")
    parser.add_argument("command", nargs="?", default="dashboard", choices=["dashboard", "status", "companies", "mcp", "train", "run"])
    parser.add_argument("url", nargs="?")
    parser.add_argument("--limit", type=int, default=5, help="Maximum companies to profile in one run cycle")
    args = parser.parse_args()
    if args.command == "dashboard":
        host = env_value("OPENPROSPECT_HOST", "127.0.0.1")
        port = int(env_value("OPENPROSPECT_PORT", "5555"))
        if host not in {"127.0.0.1", "::1", "localhost"}:
            parser.error("Dashboard host must be loopback-only (127.0.0.1, ::1 or localhost).")
        from .app import app
        from .security import get_dashboard_token
        url = f"http://{host}:{port}"
        private_url = url + "/#token=" + get_dashboard_token()
        print(f"Private Zero Hawk dashboard: {private_url}")
        print("Keep this link private. Press CTRL+C to stop.")
        webbrowser.open(private_url)
        uvicorn.run(app, host=host, port=port)
    elif args.command == "status":
        print("Zero Hawk status")
        print("Saved companies:", len(list_companies(100000)))
        print("Outbound sending: manual SMTP / explicit approval only; no automatic campaigns")
    elif args.command == "companies":
        for company in list_companies():
            print(f"#{company['id']} {company['name']} | {company['website']} | {company['industry']} | {company['location']}")
    elif args.command == "mcp":
        from .mcp_server import main as run_mcp
        run_mcp()
    elif args.command == "run":
        from .automation import run_once
        result = run_once(args.limit)
        print("Companies profiled:", result.get("processed", 0))
        print("Errors:", len(result.get("errors", [])))
        print("Outbound messaging:", "disabled; approval required")
    elif args.command == "train":
        if not args.url:
            parser.error("train requires a website URL, e.g. zero-hawk train https://example.com")
        data = train_website(args.url)
        print("Website training saved.")
        print("Config:", data["_config_path"])
        print("Pages read:", len(data["pages_read"]))
        print("Product excerpts:", len(data["product"]))
        print("Published emails:", len(data["emails_published"]))
        print("Edit the result in the dashboard at /train or in the JSON config file.")


if __name__ == "__main__":
    main()
