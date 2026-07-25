"""Run the BOOT-0021 Security Core demonstration."""

import json

from .application import SecurityCoreDemo


def main() -> None:
    result = SecurityCoreDemo().run()
    print("\nBOOT-0021 Security Core Demonstration")
    print("-" * 48)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
