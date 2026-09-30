from __future__ import annotations

from dataclasses import replace

import pytest

from floating_link_dock.link_service import (
    LinkValidationError,
    create_link,
    derive_name,
    normalize_url,
    reorder_links,
    validate_link,
)
from floating_link_dock.models import Link


def test_adds_https_to_bare_domain() -> None:
    assert normalize_url(" example.com/path ") == "https://example.com/path"


@pytest.mark.parametrize("url", ["http://example.com", "https://example.com/a"])
def test_preserves_http_and_https(url: str) -> None:
    assert normalize_url(url) == url


@pytest.mark.parametrize(
    "url", ["javascript:alert(1)", "file:///C:/secret.txt", "data:text/plain,hello"]
)
def test_rejects_unsafe_schemes(url: str) -> None:
    with pytest.raises(LinkValidationError):
        normalize_url(url)


@pytest.mark.parametrize("url", ["", "https://", "localhost", "https:///broken"])
def test_rejects_missing_host(url: str) -> None:
    with pytest.raises(LinkValidationError):
        normalize_url(url)


def test_derives_name_from_hostname() -> None:
    assert derive_name("https://www.example.com/path") == "example.com"
    assert validate_link("", "example.com").name == "example.com"


def test_create_link_assigns_uuid_and_requested_order() -> None:
    draft = validate_link("示例", "example.com")
    link = create_link(draft, order=4)

    assert link.name == "示例"
    assert link.url == "https://example.com"
    assert link.order == 4
    assert len(link.id) == 36


def test_reorder_returns_new_contiguous_order() -> None:
    links = [
        Link(id="a", name="A", url="https://a.example", order=0),
        Link(id="b", name="B", url="https://b.example", order=1),
        Link(id="c", name="C", url="https://c.example", order=2),
    ]

    result = reorder_links(links, source_index=2, target_index=0)

    assert [item.id for item in result] == ["c", "a", "b"]
    assert [item.order for item in result] == [0, 1, 2]
    assert links[2] == replace(links[2], order=2)


@pytest.mark.parametrize("source,target", [(-1, 0), (0, 3), (3, 0)])
def test_reorder_rejects_out_of_range_indices(source: int, target: int) -> None:
    links = [Link(id="a", name="A", url="https://a.example", order=0)]

    with pytest.raises(IndexError):
        reorder_links(links, source, target)
