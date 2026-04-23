#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys

from app.config import get_settings
from app.services.entitlement_service import sign_entitlement_token


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a signed entitlement token for orchestration APIs.")
    parser.add_argument("--tier", choices=["free", "pro", "power"], default="pro", help="Subscription tier to encode.")
    parser.add_argument("--ttl-seconds", type=int, default=3600, help="Token lifetime in seconds.")
    parser.add_argument("--secret", default="", help="Signing secret override; defaults to APP_ENTITLEMENT_SECRET.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    secret = args.secret or settings.entitlement_secret
    if not secret:
        print(
            "Missing secret. Set APP_ENTITLEMENT_SECRET or pass --secret.",
            file=sys.stderr,
        )
        return 2

    token = sign_entitlement_token(
        secret=secret,
        tier=args.tier,
        ttl_seconds=max(1, int(args.ttl_seconds)),
    )
    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
