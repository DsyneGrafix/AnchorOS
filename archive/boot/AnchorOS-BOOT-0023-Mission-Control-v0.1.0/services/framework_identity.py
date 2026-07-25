from dataclasses import dataclass


@dataclass(frozen=True)
class FrameworkIdentity:
    """Standard identity contract for AnchorOS frameworks."""

    name: str
    description: str
    motto: str
    version: str
    status: str

    def display(self) -> None:
        """Display the framework identity banner."""

        width = 58

        print()
        print("-" * width)
        print(f"{self.name:^{width}}")
        print(f"{self.description:^{width}}")
        print()
        print(f"{self.motto:^{width}}")
        print()
        print(f"Version : {self.version}")
        print(f"Status  : {self.status}")
        print(f"{'Built on AnchorOS':^{width}}")
        print("-" * width)
