"""Command-line entry point for the customer onboarding demonstration."""

import json

from .application import CustomerOnboardingDemo


def main() -> None:
    record, replay = CustomerOnboardingDemo().run()
    print("\nCustomer Onboarding Result")
    print("-" * 40)
    print(json.dumps(record, indent=2, sort_keys=True))
    print("\nReplay Result")
    print("-" * 40)
    print(json.dumps(replay, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
