import argparse

from startup import boot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Boot the AnchorOS platform.")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Boot, verify, report, and exit without waiting for Ctrl+C.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open Mission Control in a browser.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    boot(verify_only=args.verify_only, open_browser=not args.no_browser)
