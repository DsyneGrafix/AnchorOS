from version import (
    BOOT,
    BUILD,
    CODENAME,
    COMPANY,
    DESCRIPTION,
    PRODUCT,
    STAGE,
    VERSION,
)


def print_banner() -> None:
    """Display the AnchorOS startup identity."""

    width = 58

    print("=" * width)
    print(f"{PRODUCT:^{width}}")
    print(f"{DESCRIPTION:^{width}}")
    print()
    print(f"Product   : {PRODUCT}")
    print(f"Version   : {VERSION}")
    print(f"Codename  : {CODENAME}")
    print(f"Stage     : {STAGE}")
    print(f"Boot      : {BOOT}")
    print(f"Build     : {BUILD}")
    print()
    print(f"{COMPANY:^{width}}")
    print("=" * width)
