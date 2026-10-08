from dataclasses import dataclass
from pathlib import Path


class IntegrationError(RuntimeError):
    """A user-displayable platform integration failure."""


@dataclass(frozen=True)
class BrowserChoice:
    name: str
    executable: Path
