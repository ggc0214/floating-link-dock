from __future__ import annotations

from dataclasses import replace
from ipaddress import ip_address
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

from .models import Link, LinkDraft


class LinkValidationError(ValueError):
    """Raised when a link cannot safely be opened as a web URL."""


def _has_public_style_host(hostname: str) -> bool:
    if "." in hostname:
        return True
    try:
        ip_address(hostname)
    except ValueError:
        return False
    return True


def normalize_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise LinkValidationError("请输入网址")

    parsed_before_prefix = urlparse(value)
    if not parsed_before_prefix.scheme:
        value = f"https://{value}"

    parsed = urlparse(value)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise LinkValidationError("仅支持 http 或 https 网址")
    if not parsed.hostname or not _has_public_style_host(parsed.hostname):
        raise LinkValidationError("请输入完整的网站域名")

    return urlunparse(parsed._replace(scheme=scheme))


def derive_name(url: str) -> str:
    hostname = (urlparse(url).hostname or "").lower()
    return hostname.removeprefix("www.")


def validate_link(name: str, raw_url: str) -> LinkDraft:
    normalized = normalize_url(raw_url)
    cleaned_name = name.strip() or derive_name(normalized)
    if not cleaned_name:
        raise LinkValidationError("请输入网站名称")
    return LinkDraft(name=cleaned_name, url=normalized)


def create_link(draft: LinkDraft, order: int) -> Link:
    return Link(id=str(uuid4()), name=draft.name, url=draft.url, order=order)


def reorder_links(
    links: list[Link], source_index: int, target_index: int
) -> list[Link]:
    if not 0 <= source_index < len(links):
        raise IndexError("source index out of range")
    if not 0 <= target_index < len(links):
        raise IndexError("target index out of range")

    reordered = list(links)
    item = reordered.pop(source_index)
    reordered.insert(target_index, item)
    return [replace(link, order=index) for index, link in enumerate(reordered)]
