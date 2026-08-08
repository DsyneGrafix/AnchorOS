"""AIN-303.2 bounded live HTTP acquisition provider.

This module provides a deliberately small network boundary for Version 1.
It retrieves one approved HTTP/HTTPS source at a time and returns immutable
bytes plus the response media type to the existing AIN-303.1 acquisition
service.

It is NOT a crawler. It does not discover links, execute JavaScript, bypass
access controls, rotate identities, or admit evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .models import CandidateSource


class LiveAcquisitionError(Exception):
    """Base exception for bounded live-acquisition failures."""


class UnsupportedLiveSource(LiveAcquisitionError):
    """Raised when a source cannot be acquired by the V1 HTTP provider."""


class LiveSourceTooLarge(LiveAcquisitionError):
    """Raised when a response exceeds the configured acquisition limit."""


@dataclass(frozen=True)
class LiveHTTPAcquisitionProvider:
    """Acquire one explicitly approved HTTP/HTTPS source.

    The provider is intentionally narrow. AIN-303 source discovery remains
    responsible for deciding which URLs are candidates. This provider only
    retrieves the candidate it is given.
    """

    timeout_seconds: float = 15.0
    maximum_bytes: int = 5_000_000
    user_agent: str = "AnchorInsight/303.2 (+bounded-live-acquisition)"

    SUPPORTED_MEDIA_TYPES = frozenset(
        {
            "text/html",
            "text/plain",
            "text/markdown",
            "application/json",
            "application/xml",
            "text/xml",
            "application/xhtml+xml",
        }
    )

    def __call__(self, source: CandidateSource) -> tuple[bytes, str]:
        parsed = urlparse(source.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise UnsupportedLiveSource(
                f"Live acquisition requires an absolute HTTP/HTTPS URL: {source.url}"
            )

        request = Request(
            source.url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,text/plain,application/json,application/xml;q=0.9,*/*;q=0.1",
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                media_type = (
                    response.headers.get_content_type()
                    if response.headers is not None
                    else "application/octet-stream"
                )

                if media_type not in self.SUPPORTED_MEDIA_TYPES:
                    raise UnsupportedLiveSource(
                        f"Unsupported live-acquisition media type: {media_type}"
                    )

                declared_length = response.headers.get("Content-Length")
                if declared_length is not None:
                    try:
                        if int(declared_length) > self.maximum_bytes:
                            raise LiveSourceTooLarge(
                                f"Source exceeds maximum acquisition size of {self.maximum_bytes} bytes."
                            )
                    except ValueError:
                        pass

                content = response.read(self.maximum_bytes + 1)
                if len(content) > self.maximum_bytes:
                    raise LiveSourceTooLarge(
                        f"Source exceeds maximum acquisition size of {self.maximum_bytes} bytes."
                    )

                return content, media_type

        except (UnsupportedLiveSource, LiveSourceTooLarge):
            raise
        except HTTPError as exc:
            raise LiveAcquisitionError(
                f"HTTP acquisition failed with status {exc.code}: {source.url}"
            ) from exc
        except URLError as exc:
            raise LiveAcquisitionError(
                f"Live acquisition failed for {source.url}: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise LiveAcquisitionError(
                f"Live acquisition timed out for {source.url}"
            ) from exc
