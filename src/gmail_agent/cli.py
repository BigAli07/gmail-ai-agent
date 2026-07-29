from __future__ import annotations

import argparse
import json
import sys

from filelock import FileLock, Timeout

from .agent import GmailAgent
from .auth import AccountMismatchError, load_credentials, verify_authenticated_account
from .classifier import HybridAnalyzer
from .config import Settings
from .gmail import GmailClient
from .logging_config import configure_logging
from .state import StateRepository


def main() -> int:
    parser = argparse.ArgumentParser(description="Process unread Gmail messages once")
    parser.add_argument("command", nargs="?", default="run-once", choices=["run-once", "auth"])
    args = parser.parse_args()
    settings = Settings()  # type: ignore[call-arg]
    configure_logging(settings.log_level)
    try:
        with FileLock(str(settings.lock_file), timeout=0):
            credentials = load_credentials(
                settings.gmail_credentials_file, settings.gmail_token_file
            )
            # Deliberately verify identity before GmailClient constructs a Gmail service.
            authenticated = verify_authenticated_account(
                credentials, str(settings.gmail_account_email)
            )
            if args.command == "auth":
                print(f"OAuth authorized and verified for {authenticated}.")
                return 0
            gmail = GmailClient(credentials)
            agent = GmailAgent(
                settings,
                gmail,
                HybridAnalyzer(
                    settings.openai_api_key,
                    settings.openai_model,
                    settings.classification_confidence_threshold,
                ),
                StateRepository(settings.database_path),
            )
            print(json.dumps(agent.run_once(), indent=2))
            return 0
    except AccountMismatchError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 3
    except Timeout:
        print("Another Gmail AI agent run is active; exiting cleanly.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
