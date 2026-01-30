from __future__ import annotations

from pathlib import Path

import pytest
import requests
import responses

from generator import core as gen_core
from generator.core import GeneratorError, RIPESTAT_URL, generate_resource


def _write_resource(base_dir: Path, asns=None, resource_id: str = "cloudflare") -> None:
    resources = base_dir / "resources"
    resources.mkdir(parents=True, exist_ok=True)
    if asns is None:
        asns = ["AS13335"]
    (resources / f"{resource_id}.yaml").write_text(
        f"resource_id: {resource_id}\n"
        "source_type: asn\n"
        "asns:\n"
        + "\n".join([f"  - {asn}" for asn in asns])
        + "\n"
    )


def _write_url_resource(
    base_dir: Path, resource_id: str, url: str, feed_format: str
) -> None:
    resources = base_dir / "resources"
    resources.mkdir(parents=True, exist_ok=True)
    (resources / f"{resource_id}.yaml").write_text(
        f"resource_id: {resource_id}\n"
        "source_type: url\n"
        f"url: {url}\n"
        f"format: {feed_format}\n"
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
def test_url_non_200_does_not_overwrite(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path, resource_id="aws", url="https://example.com/aws.json", feed_format="aws_ip_ranges_json"
    )
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "aws.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        "https://example.com/aws.json",
        status=500,
    )

    with pytest.raises(GeneratorError):
        generate_resource("aws", tmp_path)

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
def test_url_malformed_json_does_not_overwrite(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path, resource_id="aws", url="https://example.com/aws.json", feed_format="aws_ip_ranges_json"
    )
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "aws.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        "https://example.com/aws.json",
        body="not-json",
        status=200,
    )

    with pytest.raises(GeneratorError):
        generate_resource("aws", tmp_path)

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
def test_url_empty_prefixes_does_not_overwrite(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path, resource_id="aws", url="https://example.com/aws.json", feed_format="aws_ip_ranges_json"
    )
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "aws.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        "https://example.com/aws.json",
        json={"prefixes": []},
        status=200,
    )

    with pytest.raises(GeneratorError):
        generate_resource("aws", tmp_path)

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
def test_url_timeout_does_not_overwrite(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path, resource_id="aws", url="https://example.com/aws.json", feed_format="aws_ip_ranges_json"
    )
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "aws.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        "https://example.com/aws.json",
        body=requests.exceptions.Timeout(),
    )

    with pytest.raises(GeneratorError):
        generate_resource("aws", tmp_path)

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
    assert "list=$AddressList" in add_lines[0]


@responses.activate
def test_url_aws_json_success(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path, resource_id="aws", url="https://example.com/aws.json", feed_format="aws_ip_ranges_json"
    )

    responses.add(
        responses.GET,
        "https://example.com/aws.json",
        json={
            "prefixes": [
                {"ip_prefix": "3.5.140.0/22"},
                {"ip_prefix": "2001:db8::/32"},
            ],
            "ipv6_prefixes": [{"ipv6_prefix": "2600:9000::/28"}],
        },
        status=200,
    )

    path = generate_resource("aws", tmp_path)
    add_lines = [line for line in _read_add_lines(path) if line.startswith("/ip/firewall/address-list add")]

    assert len(add_lines) == 1
    assert "address=3.5.140.0/22" in add_lines[0]
    assert "list=$AddressList" in add_lines[0]


@responses.activate
def test_url_retries_then_success(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path, resource_id="aws", url="https://example.com/aws.json", feed_format="aws_ip_ranges_json"
    )

    def _callback(request):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise requests.exceptions.Timeout()
        return (200, {}, '{"prefixes":[{"ip_prefix":"3.5.140.0/22"}]}' )

    call_count = {"n": 0}
    responses.add_callback(
        responses.GET,
        "https://example.com/aws.json",
        callback=_callback,
        content_type="application/json",
    )

    path = generate_resource("aws", tmp_path)
    add_lines = [line for line in _read_add_lines(path) if line.startswith("/ip/firewall/address-list add")]

    assert len(add_lines) == 1
    assert "address=3.5.140.0/22" in add_lines[0]


@responses.activate
def test_plain_cidr_success_ignores_comments(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path, resource_id="cloudflare", url="https://example.com/cf.txt", feed_format="plain_cidr"
    )

    responses.add(
        responses.GET,
        "https://example.com/cf.txt",
        body=(
            "# comment\n"
            "\n"
            "1.1.1.0/24\n"
            "# another\n"
            "1.0.0.0/24\n"
        ),
        status=200,
    )

    path = generate_resource("cloudflare", tmp_path)
    add_lines = [line for line in _read_add_lines(path) if line.startswith("/ip/firewall/address-list add")]

    assert len(add_lines) == 2
    assert all("list=$AddressList" in line for line in add_lines)


@responses.activate
def test_plain_cidr_ipv6_filtered(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path, resource_id="cloudflare", url="https://example.com/cf.txt", feed_format="plain_cidr"
    )

    responses.add(
        responses.GET,
        "https://example.com/cf.txt",
        body="2606:4700::/32\n1.1.1.0/24\n",
        status=200,
    )

    path = generate_resource("cloudflare", tmp_path)
    add_lines = [line for line in _read_add_lines(path) if line.startswith("/ip/firewall/address-list add")]

    assert len(add_lines) == 1
    assert "address=1.1.1.0/24" in add_lines[0]


@responses.activate
def test_plain_cidr_empty_fails_and_preserves_dist(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path, resource_id="cloudflare", url="https://example.com/cf.txt", feed_format="plain_cidr"
    )
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "cloudflare.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        "https://example.com/cf.txt",
        body="# only comments\n# another\n",
        status=200,
    )

    with pytest.raises(GeneratorError):
        generate_resource("cloudflare", tmp_path)

    assert target.read_text() == "OLD"


@responses.activate
def test_plain_cidr_malformed_line_fails(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path, resource_id="cloudflare", url="https://example.com/cf.txt", feed_format="plain_cidr"
    )
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "cloudflare.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        "https://example.com/cf.txt",
        body="1.1.1.0/24\nnot-a-cidr\n",
        status=200,
    )

    with pytest.raises(GeneratorError):
        generate_resource("cloudflare", tmp_path)

    assert target.read_text() == "OLD"


@responses.activate
def test_google_cloud_json_success_ipv4_only(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path,
        resource_id="googlecloud",
        url="https://example.com/cloud.json",
        feed_format="google_cloud_json",
    )

    responses.add(
        responses.GET,
        "https://example.com/cloud.json",
        json={
            "prefixes": [
                {"ipv4Prefix": "34.80.0.0/15"},
                {"ipv6Prefix": "2600:1900::/28"},
                {"ipv4Prefix": "35.190.0.0/17"},
            ]
        },
        status=200,
    )

    path = generate_resource("googlecloud", tmp_path)
    add_lines = [line for line in _read_add_lines(path) if line.startswith("/ip/firewall/address-list add")]

    assert len(add_lines) == 2
    assert any("address=34.80.0.0/15" in line for line in add_lines)
    assert any("address=35.190.0.0/17" in line for line in add_lines)


@responses.activate
def test_google_cloud_json_malformed_fails_and_preserves_dist(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path,
        resource_id="googlecloud",
        url="https://example.com/cloud.json",
        feed_format="google_cloud_json",
    )
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "googlecloud.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        "https://example.com/cloud.json",
        body="not-json",
        status=200,
    )

    with pytest.raises(GeneratorError):
        generate_resource("googlecloud", tmp_path)

    assert target.read_text() == "OLD"


@responses.activate
def test_google_cloud_json_empty_ipv4_fails_and_preserves_dist(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path,
        resource_id="googlecloud",
        url="https://example.com/cloud.json",
        feed_format="google_cloud_json",
    )
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "googlecloud.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        "https://example.com/cloud.json",
        json={"prefixes": [{"ipv6Prefix": "2600:1900::/28"}]},
        status=200,
    )

    with pytest.raises(GeneratorError):
        generate_resource("googlecloud", tmp_path)

    assert target.read_text() == "OLD"


@responses.activate
def test_generated_rsc_has_no_cr(tmp_path: Path) -> None:
    _write_resource(tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)

    responses.add(
        responses.GET,
        RIPESTAT_URL,
        json={"data": {"prefixes": [{"prefix": "1.1.1.0/24"}]}},
        status=200,
        match=[responses.matchers.query_param_matcher({"resource": "AS13335"})],
    )

    path = generate_resource("cloudflare", tmp_path)
    data = path.read_bytes()
    assert b"\r" not in data


@responses.activate
def test_fastly_public_ip_list_success_ipv4_only(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path,
        resource_id="fastly",
        url="https://example.com/fastly.json",
        feed_format="fastly_public_ip_list_json",
    )

    responses.add(
        responses.GET,
        "https://example.com/fastly.json",
        json={
            "addresses": ["23.235.32.0/20", "151.101.0.0/16"],
            "ipv6_addresses": ["2a04:4e42::/32"],
        },
        status=200,
    )

    path = generate_resource("fastly", tmp_path)
    add_lines = [line for line in _read_add_lines(path) if line.startswith("/ip/firewall/address-list add")]

    assert len(add_lines) == 2
    assert any("address=23.235.32.0/20" in line for line in add_lines)
    assert any("address=151.101.0.0/16" in line for line in add_lines)


@responses.activate
def test_fastly_public_ip_list_malformed_fails_and_preserves_dist(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path,
        resource_id="fastly",
        url="https://example.com/fastly.json",
        feed_format="fastly_public_ip_list_json",
    )
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "fastly.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        "https://example.com/fastly.json",
        body="not-json",
        status=200,
    )

    with pytest.raises(GeneratorError):
        generate_resource("fastly", tmp_path)

    assert target.read_text() == "OLD"


@responses.activate
def test_fastly_public_ip_list_empty_fails_and_preserves_dist(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path,
        resource_id="fastly",
        url="https://example.com/fastly.json",
        feed_format="fastly_public_ip_list_json",
    )
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "fastly.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        "https://example.com/fastly.json",
        json={"addresses": []},
        status=200,
    )

    with pytest.raises(GeneratorError):
        generate_resource("fastly", tmp_path)

    assert target.read_text() == "OLD"


@responses.activate
def test_fastly_public_ip_list_invalid_cidr_fails(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path,
        resource_id="fastly",
        url="https://example.com/fastly.json",
        feed_format="fastly_public_ip_list_json",
    )
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "fastly.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        "https://example.com/fastly.json",
        json={"addresses": ["23.235.32.0/20", "bad-cidr"]},
        status=200,
    )

    with pytest.raises(GeneratorError):
        generate_resource("fastly", tmp_path)

    assert target.read_text() == "OLD"


def test_url_allow_cache_fallback(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path, resource_id="aws", url="https://example.com/aws.json", feed_format="aws_ip_ranges_json"
    )
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "aws.json").write_text('{"prefixes":[{"ip_prefix":"3.5.140.0/22"}]}')

    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "aws.rsc"
    target.write_text("OLD")

    def _raise(*_args, **_kwargs):
        raise requests.exceptions.Timeout()

    original = requests.get
    requests.get = _raise
    try:
        path = generate_resource("aws", tmp_path, allow_cache=True)
        assert path.read_text() != "OLD"
    finally:
        requests.get = original


def test_url_no_cache_fails(tmp_path: Path) -> None:
    _write_url_resource(
        tmp_path, resource_id="aws", url="https://example.com/aws.json", feed_format="aws_ip_ranges_json"
    )
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "aws.rsc"
    target.write_text("OLD")

    def _raise(*_args, **_kwargs):
        raise requests.exceptions.Timeout()

    original = requests.get
    requests.get = _raise
    try:
        with pytest.raises(GeneratorError):
            generate_resource("aws", tmp_path, allow_cache=False)
        assert target.read_text() == "OLD"
    finally:
        requests.get = original


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
    assert all("list=$AddressList" in line for line in add_lines)


@responses.activate
def test_first_non_comment_is_global_addresslist(tmp_path: Path) -> None:
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

    assert first_non_comment == ":global AddressList"


@responses.activate
def test_self_check_blocks_bad_rsc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_resource(tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / "cloudflare.rsc"
    target.write_text("OLD")

    responses.add(
        responses.GET,
        RIPESTAT_URL,
        json={"data": {"prefixes": [{"prefix": "1.1.1.0/24"}]}},
        status=200,
        match=[responses.matchers.query_param_matcher({"resource": "AS13335"})],
    )

    def _bad_render(resource, networks) -> str:
        return (
            "# iplist-rsc v1\n"
            "# resource=cloudflare\n"
            "# generated=2026-01-30T00:00:00Z\n"
            "# count=2\n"
            "\n"
            "/ip/firewall/address-list add list=blacklist_eu address=1.1.1.0/24 "
            "comment=\"iplist:auto:cloudflare\"\n"
        )

    monkeypatch.setattr(gen_core, "_render_rsc", _bad_render)

    with pytest.raises(GeneratorError):
        generate_resource("cloudflare", tmp_path)

    assert target.read_text() == "OLD"


@responses.activate
@pytest.mark.parametrize(
    "resource_id,asn",
    [
        ("cloudflare", "AS13335"),
        ("digitalocean", "AS14061"),
        ("hetzner", "AS24940"),
        ("ovh", "AS16276"),
        ("oracle", "AS31898"),
        ("aws", "AS16509"),
        ("googlecloud", "AS396982"),
        ("fastly", "AS54113"),
        ("akamai_us", "AS16625"),
        ("akamai_pl", "AS20940"),
        ("cdn77", "AS60068"),
        ("contabo", "AS51167"),
        ("scaleway", "AS12876"),
        ("constant", "AS20473"),
    ],
)
def test_generated_rsc_has_addresslist_and_no_remove(
    tmp_path: Path, resource_id: str, asn: str
) -> None:
    _write_resource(tmp_path, asns=[asn], resource_id=resource_id)

    responses.add(
        responses.GET,
        RIPESTAT_URL,
        json={"data": {"prefixes": [{"prefix": "1.2.3.0/24"}]}},
        status=200,
        match=[responses.matchers.query_param_matcher({"resource": asn})],
    )

    path = generate_resource(resource_id, tmp_path)
    lines = path.read_text().splitlines()
    first_non_comment = next(line for line in lines if line and not line.startswith("#"))
    assert first_non_comment == ":global AddressList"
    add_lines = [line for line in lines if line.startswith("/ip/firewall/address-list add ")]
    assert add_lines
    assert all("list=$AddressList" in line for line in add_lines)
    assert all(f'comment="iplist:auto:{resource_id}"' in line for line in add_lines)
    assert all("/ip/firewall/address-list remove" not in line for line in lines)
