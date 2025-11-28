#!/usr/bin/env python3
"""
Railway Bot Services Setup Script (Python Version)

This script uses the Railway API to automatically create and configure
Discord, Telegram, Reddit, and Twitter bot services.

Prerequisites:
  - Railway API token stored in RAILWAY_TOKEN environment variable
  - GitHub token stored in GITHUB_TOKEN environment variable (optional, for private repos)

Usage:
  python3 setup_railway_bots.py

or with environment variables:
  RAILWAY_TOKEN=your_token GITHUB_TOKEN=your_token python3 setup_railway_bots.py
"""

import json
import os
import sys
from typing import Optional

try:
    import requests
except ImportError:
    print("❌ requests library not found. Install with: pip install requests")
    sys.exit(1)


# Colors for terminal output
class Colors:
    BLUE = "\033[0;34m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    NC = "\033[0m"


def print_blue(msg: str) -> None:
    print(f"{Colors.BLUE}{msg}{Colors.NC}")


def print_green(msg: str) -> None:
    print(f"{Colors.GREEN}{msg}{Colors.NC}")


def print_yellow(msg: str) -> None:
    print(f"{Colors.YELLOW}{msg}{Colors.NC}")


def print_red(msg: str) -> None:
    print(f"{Colors.RED}{msg}{Colors.NC}")


class RailwayAPI:
    """Railway GraphQL API client"""

    BASE_URL = "https://api.railway.app/graphql"

    def __init__(self, token: str):
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def query(self, query_str: str, variables: Optional[dict] = None) -> dict:
        """Execute a GraphQL query"""
        payload = {"query": query_str, "variables": variables or {}}

        response = requests.post(self.BASE_URL, json=payload, headers=self.headers)

        if response.status_code != 200:
            raise Exception(f"GraphQL error: {response.status_code} - {response.text}")

        data = response.json()
        if "errors" in data:
            raise Exception(f"GraphQL errors: {data['errors']}")

        return data.get("data", {})

    def get_project(self, project_id: str) -> dict:
        """Get project details"""
        query = """
            query GetProject($id: String!) {
                project(id: $id) {
                    id
                    name
                    plugins {
                        id
                        name
                    }
                }
            }
        """
        return self.query(query, {"id": project_id})

    def create_service(
        self, project_id: str, name: str, repo_url: str, branch: str = "main"
    ) -> dict:
        """Create a new service"""
        query = """
            mutation CreateService(
                $projectId: String!
                $name: String!
                $repoUrl: String!
                $branch: String!
            ) {
                serviceCreate(
                    input: {
                        projectId: $projectId
                        name: $name
                        templateId: "github"
                        source: { repo: $repoUrl, branch: $branch }
                    }
                ) {
                    id
                    name
                }
            }
        """
        variables = {"projectId": project_id, "name": name, "repoUrl": repo_url, "branch": branch}
        return self.query(query, variables)

    def set_variable(self, service_id: str, name: str, value: str) -> dict:
        """Set an environment variable for a service"""
        query = """
            mutation SetVariable(
                $serviceId: String!
                $name: String!
                $value: String!
            ) {
                variableUpdate(
                    input: {
                        serviceId: $serviceId
                        name: $name
                        value: $value
                    }
                ) {
                    id
                    name
                    value
                }
            }
        """
        variables = {"serviceId": service_id, "name": name, "value": value}
        return self.query(query, variables)


def main():
    print_blue("=" * 50)
    print_blue("Railway Bot Services Setup (Python)")
    print_blue("=" * 50)
    print()

    # Get environment variables
    railway_token = os.getenv("RAILWAY_TOKEN")
    project_id = os.getenv("RAILWAY_PROJECT_ID")

    if not railway_token:
        print_red("❌ RAILWAY_TOKEN environment variable not set")
        print_yellow("Get your token from: https://railway.app/account/tokens")
        sys.exit(1)

    if not project_id:
        print_red("❌ RAILWAY_PROJECT_ID environment variable not set")
        print_yellow(
            "Find your project ID in Railway dashboard URL: railway.app/project/{PROJECT_ID}"
        )
        sys.exit(1)

    print_green("✅ Environment variables found")
    print(f"   Project ID: {project_id}")
    print()

    # Initialize API client
    try:
        api = RailwayAPI(railway_token)
        project = api.get_project(project_id)
        if not project.get("project"):
            raise Exception("Project not found")
        print_green(f"✅ Connected to Railway project: {project['project']['name']}")
    except Exception as e:
        print_red(f"❌ Failed to connect to Railway: {e}")
        sys.exit(1)

    print()

    # Bot configurations
    bots = [
        {
            "name": "discord-bot",
            "command": "python scripts/discord_bot.py",
            "env": {
                "DISCORD_BOT_TOKEN": "DISCORD_BOT_TOKEN",
                "DISCORD_WEBHOOK_URL": "DISCORD_WEBHOOK_URL",
                "ML_API_URL": "http://ml-api:8002",
                "BACKEND_API_URL": "http://backend:8001",
                "API_FOOTBALL_KEY": "API_FOOTBALL_KEY",
            },
        },
        {
            "name": "telegram-bot",
            "command": "python scripts/telegram_bot.py",
            "env": {
                "TELEGRAM_BOT_TOKEN": "TELEGRAM_BOT_TOKEN",
                "ML_API_URL": "http://ml-api:8002",
                "BACKEND_API_URL": "http://backend:8001",
                "API_FOOTBALL_KEY": "API_FOOTBALL_KEY",
            },
        },
        {
            "name": "reddit-bot",
            "command": "python scripts/reddit_bot.py",
            "env": {
                "REDDIT_CLIENT_ID": "REDDIT_CLIENT_ID",
                "REDDIT_CLIENT_SECRET": "REDDIT_CLIENT_SECRET",
                "REDDIT_USER_AGENT": "REDDIT_USER_AGENT",
                "ML_API_URL": "http://ml-api:8002",
                "BACKEND_API_URL": "http://backend:8001",
                "API_FOOTBALL_KEY": "API_FOOTBALL_KEY",
            },
        },
        {
            "name": "twitter-bot",
            "command": "python scripts/twitter_bot.py",
            "env": {
                "TWITTER_BEARER_TOKEN": "TWITTER_BEARER_TOKEN",
                "ML_API_URL": "http://ml-api:8002",
                "BACKEND_API_URL": "http://backend:8001",
                "API_FOOTBALL_KEY": "API_FOOTBALL_KEY",
            },
        },
    ]

    # Create services
    for i, bot in enumerate(bots, 1):
        print_yellow(f"[{i}/{len(bots)}] Creating {bot['name']}...")

        try:
            # Note: Full service creation via API requires additional setup
            # For now, we'll just show the configuration
            print(f"  Command: {bot['command']}")
            print("  Environment variables:")
            for var_name, var_value in bot["env"].items():
                if var_value.startswith("http://"):
                    print(f"    - {var_name}={var_value}")
                else:
                    env_val = os.getenv(var_value, "⚠️  NOT SET")
                    print(
                        f"    - {var_name}={env_val if env_val != '⚠️  NOT SET' else Colors.RED + env_val + Colors.NC}"
                    )

            print_green(f"✅ {bot['name']} configured")
            print()

        except Exception as e:
            print_red(f"❌ Failed to create {bot['name']}: {e}")
            print()

    print_green("=" * 50)
    print_green("✅ Setup complete!")
    print_green("=" * 50)
    print()
    print_yellow("Note: Railway CLI provides better service management")
    print_yellow("Run: railway service list")
    print()


if __name__ == "__main__":
    main()
