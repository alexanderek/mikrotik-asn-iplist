from __future__ import annotations

from pathlib import Path

import pytest
import requests
import responses

from generator.core import (
    GeneratorError,
    RIPESTAT_URL,
    generate_resource,
)


def _write_resource(base_dir: Path, asns=None) -> None:
    resources = base_dir / "resources"
    resources.mkdir(parents=True, exist_ok=True)
    if asns is None:
        asns = ["AS13335"]
    (resources / "cloudflare.yaml").write_text(
        "resource_id: cloudflare\n"
        "asns:\n"
        + "\n".join([f"  - {asn}" for asn in asns])
        + "\n"
        "target_list: blacklist_eu\n"
    )


def _read_add_lines(path: Path) -> list[str]:
    return [line for line in path.read_text().splitlines() if line.startswith("/ip/")]


@responses.activate
def test_non_200_does_not_overwrite(tmp_path: Path) -> None:
    _write_resource(tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "cloudflare.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        RIPESTAT_URL,
        status=500,
        match=[responses.matchers.query_param_matcher({"resource": "AS13335"})],
    )

    with pytest.raises(GeneratorError):
        generate_resource("cloudflare", tmp_path)

    assert target.read_text() == "OLD"


@responses.activate
def test_malformed_json_fails(tmp_path: Path) -> None:
    _write_resource(tmp_path)

    responses.add(
        responses.GET,
        RIPESTAT_URL,
        body="not-json",
        status=200,
        match=[responses.matchers.query_param_matcher({"resource": "AS13335"})],
    )

    with pytest.raises(GeneratorError):
        generate_resource("cloudflare", tmp_path)


@responses.activate
def test_malformed_json_does_not_overwrite(tmp_path: Path) -> None:
    _write_resource(tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "cloudflare.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        RIPESTAT_URL,
        body="not-json",
        status=200,
        match=[responses.matchers.query_param_matcher({"resource": "AS13335"})],
    )

    with pytest.raises(GeneratorError):
        generate_resource("cloudflare", tmp_path)

    assert target.read_text() == "OLD"


@responses.activate
def test_empty_prefixes_fails(tmp_path: Path) -> None:
    _write_resource(tmp_path)

    responses.add(
        responses.GET,
        RIPESTAT_URL,
        json={"data": {"prefixes": []}},
        status=200,
        match=[responses.matchers.query_param_matcher({"resource": "AS13335"})],
    )

    with pytest.raises(GeneratorError):
        generate_resource("cloudflare", tmp_path)


@responses.activate
def test_empty_prefixes_does_not_overwrite(tmp_path: Path) -> None:
    _write_resource(tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "cloudflare.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        RIPESTAT_URL,
        json={"data": {"prefixes": []}},
        status=200,
        match=[responses.matchers.query_param_matcher({"resource": "AS13335"})],
    )

    with pytest.raises(GeneratorError):
        generate_resource("cloudflare", tmp_path)

    assert target.read_text() == "OLD"


@responses.activate
def test_timeout_does_not_overwrite(tmp_path: Path) -> None:
    _write_resource(tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "cloudflare.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        RIPESTAT_URL,
        body=requests.exceptions.Timeout(),
        match=[responses.matchers.query_param_matcher({"resource": "AS13335"})],
    )

    with pytest.raises(GeneratorError):
        generate_resource("cloudflare", tmp_path)

    assert target.read_text() == "OLD"


@responses.activate
def test_ipv6_excluded(tmp_path: Path) -> None:
    _write_resource(tmp_path)

    responses.add(
        responses.GET,
        RIPESTAT_URL,
        json={
            "data": {
                "prefixes": [
                    {"prefix": "2001:db8::/32"},
                    {"prefix": "1.1.1.0/24"},
                ]
            }
        },
        status=200,
        match=[responses.matchers.query_param_matcher({"resource": "AS13335"})],
    )

    path = generate_resource("cloudflare", tmp_path)
    add_lines = [line for line in _read_add_lines(path) if line.endswith('"iplist:auto:cloudflare"')]

    assert len(add_lines) == 1
    assert "address=1.1.1.0/24" in add_lines[0]


@responses.activate
def test_dedup_and_order(tmp_path: Path) -> None:
    _write_resource(tmp_path)

    responses.add(
        responses.GET,
        RIPESTAT_URL,
        json={
            "data": {
                "prefixes": [
                    {"prefix": "1.1.2.0/24"},
                    {"prefix": "1.1.1.0/24"},
                    {"prefix": "1.1.1.0/25"},
                    {"prefix": "1.1.1.0/24"},
                ]
            }
        },
        status=200,
        match=[responses.matchers.query_param_matcher({"resource": "AS13335"})],
    )

    path = generate_resource("cloudflare", tmp_path)
    add_lines = [line for line in _read_add_lines(path) if line.startswith("/ip/firewall/address-list add")]

    assert len(add_lines) == 3
    assert "address=1.1.1.0/24" in add_lines[0]
    assert "address=1.1.1.0/25" in add_lines[1]
    assert "address=1.1.2.0/24" in add_lines[2]


@responses.activate
def test_first_non_comment_is_remove(tmp_path: Path) -> None:
    _write_resource(tmp_path)

    responses.add(
        responses.GET,
        RIPESTAT_URL,
        json={"data": {"prefixes": [{"prefix": "1.1.1.0/24"}]}},
        status=200,
        match=[responses.matchers.query_param_matcher({"resource": "AS13335"})],
    )

    path = generate_resource("cloudflare", tmp_path)
    lines = path.read_text().splitlines()
    first_non_comment = next(line for line in lines if line and not line.startswith("#"))

    assert (
        first_non_comment
        == '/ip/firewall/address-list remove [find where comment="iplist:auto:cloudflare"]'
    )
