from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import ipaddress
import json
import os
from typing import Iterable, List, Optional

import requests
import yaml

RIPESTAT_URL = "https://stat.ripe.net/data/announced-prefixes/data.json"
DEFAULT_TIMEOUT = 10


@dataclass(frozen=True)
class ResourceConfig:
    resource_id: str
    source_type: str
    asns: Optional[List[str]]
    url: Optional[str]
    format: Optional[str]


class GeneratorError(RuntimeError):
    pass


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_resource_config(path: Path) -> ResourceConfig:
    try:
        data = yaml.safe_load(path.read_text())
    except Exception as exc:  # pragma: no cover - validated by callers
        raise GeneratorError(f"failed to read config {path}") from exc

    if not isinstance(data, dict):
        raise GeneratorError(f"invalid config structure in {path}")

    resource_id = data.get("resource_id")
    source_type = data.get("source_type")
    asns = data.get("asns")
    url = data.get("url")
    feed_format = data.get("format")

    if not resource_id or not isinstance(resource_id, str):
        raise GeneratorError(f"invalid resource_id in {path}")
    if source_type not in {"asn", "url"}:
        raise GeneratorError(f"invalid source_type in {path}")

    if source_type == "asn":
        if not asns or not isinstance(asns, list) or not all(isinstance(a, str) for a in asns):
            raise GeneratorError(f"invalid asns list in {path}")
        if url or feed_format:
            raise GeneratorError(f"unexpected url/format for asn source in {path}")
        return ResourceConfig(
            resource_id=resource_id, source_type=source_type, asns=asns, url=None, format=None
        )

    if not url or not isinstance(url, str):
        raise GeneratorError(f"invalid url in {path}")
    if feed_format not in {"aws_ip_ranges_json", "plain_cidr", "json_prefix_list"}:
        raise GeneratorError(f"invalid format in {path}")
    if asns:
        raise GeneratorError(f"unexpected asns for url source in {path}")

    return ResourceConfig(
        resource_id=resource_id, source_type=source_type, asns=None, url=url, format=feed_format
    )


def _fetch_json(url: str, params: Optional[dict] = None) -> dict:
    try:
        resp = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    except Exception as exc:
        raise GeneratorError(f"request failed for {url}") from exc

    if resp.status_code != 200:
        raise GeneratorError(f"non-200 from {url}: {resp.status_code}")

    try:
        return resp.json()
    except json.JSONDecodeError as exc:
        raise GeneratorError("malformed JSON response") from exc


def _fetch_text(url: str) -> str:
    try:
        resp = requests.get(url, timeout=DEFAULT_TIMEOUT)
    except Exception as exc:
        raise GeneratorError(f"request failed for {url}") from exc

    if resp.status_code != 200:
        raise GeneratorError(f"non-200 from {url}: {resp.status_code}")
    return resp.text


def _extract_prefixes(payload: dict) -> List[str]:
    data = payload.get("data") if isinstance(payload, dict) else None
    prefixes = data.get("prefixes") if isinstance(data, dict) else None

    if not prefixes:
        raise GeneratorError("empty prefixes")

    result: List[str] = []
    for item in prefixes:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict) and "prefix" in item:
            result.append(item["prefix"])
    return result


def _extract_aws_prefixes(payload: dict) -> List[str]:
    if not isinstance(payload, dict):
        raise GeneratorError("malformed JSON response")
    prefixes = payload.get("prefixes")
    if not prefixes:
        raise GeneratorError("empty prefixes")

    result: List[str] = []
    for item in prefixes:
        if isinstance(item, dict) and "ip_prefix" in item:
            result.append(item["ip_prefix"])
    return result


def _extract_plain_cidr(text: str) -> List[str]:
    prefixes = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        prefixes.append(line)
    if not prefixes:
        raise GeneratorError("empty prefixes")
    return prefixes


def _extract_json_prefix_list(payload: object) -> List[str]:
    if isinstance(payload, list):
        prefixes = [p for p in payload if isinstance(p, str)]
    elif isinstance(payload, dict):
        raw = payload.get("prefixes")
        if isinstance(raw, list):
            prefixes = []
            for item in raw:
                if isinstance(item, str):
                    prefixes.append(item)
                elif isinstance(item, dict) and "prefix" in item:
                    prefixes.append(item["prefix"])
        else:
            prefixes = []
    else:
        prefixes = []

    if not prefixes:
        raise GeneratorError("empty prefixes")
    return prefixes


def _normalize_ipv4(prefixes: Iterable[str]) -> List[ipaddress.IPv4Network]:
    networks: List[ipaddress.IPv4Network] = []
    for pfx in prefixes:
        try:
            net = ipaddress.ip_network(pfx, strict=False)
        except ValueError:
            continue
        if net.version == 4:
            networks.append(net)
    if not networks:
        raise GeneratorError("no IPv4 prefixes after filtering")
    return networks


def _dedup_sort(networks: Iterable[ipaddress.IPv4Network]) -> List[ipaddress.IPv4Network]:
    uniq = {str(net): net for net in networks}
    return sorted(uniq.values(), key=lambda n: (int(n.network_address), n.prefixlen))


def fetch_prefixes_for_asn(asn: str) -> List[str]:
    payload = _fetch_json(RIPESTAT_URL, params={"resource": asn})
    return _extract_prefixes(payload)


def fetch_prefixes_for_url(resource: ResourceConfig) -> List[str]:
    if not resource.url or not resource.format:
        raise GeneratorError("invalid url resource configuration")

    if resource.format == "aws_ip_ranges_json":
        payload = _fetch_json(resource.url)
        return _extract_aws_prefixes(payload)
    if resource.format == "plain_cidr":
        text = _fetch_text(resource.url)
        return _extract_plain_cidr(text)
    if resource.format == "json_prefix_list":
        payload = _fetch_json(resource.url)
        return _extract_json_prefix_list(payload)

    raise GeneratorError("unsupported url format")


def _render_rsc(resource: ResourceConfig, networks: List[ipaddress.IPv4Network]) -> str:
    header = [
        "# iplist-rsc v1",
        f"# resource={resource.resource_id}",
        f"# generated={_iso_utc_now()}",
        f"# count={len(networks)}",
        "",
    ]
    remove_line = (
        f"/ip/firewall/address-list remove [find where comment=\"iplist:auto:{resource.resource_id}\"]"
    )
    lines = [remove_line]
    for net in networks:
        lines.append(
            f"/ip/firewall/address-list add list=$AddressList address={net} "
            f"comment=\"iplist:auto:{resource.resource_id}\""
        )
    return "\n".join(header + lines) + "\n"


def _self_check_rsc(resource: ResourceConfig, contents: str) -> None:
    remove_line = (
        f"/ip/firewall/address-list remove [find where comment=\"iplist:auto:{resource.resource_id}\"]"
    )
    if remove_line not in contents:
        raise GeneratorError("self-check failed: remove line missing")

    lines = contents.splitlines()
    first_non_comment = next(
        (line for line in lines if line and not line.startswith("#")),
        None,
    )
    if first_non_comment != remove_line:
        raise GeneratorError("self-check failed: remove line not first command")

    count_line = next((line for line in lines if line.startswith("# count=")), None)
    if not count_line:
        raise GeneratorError("self-check failed: count header missing")
    try:
        expected_count = int(count_line.split("=", 1)[1].strip())
    except ValueError as exc:
        raise GeneratorError("self-check failed: count header invalid") from exc

    add_lines = [
        line for line in lines if line.startswith("/ip/firewall/address-list add ")
    ]
    for line in add_lines:
        if "list=$AddressList" not in line:
            raise GeneratorError("self-check failed: add line missing $AddressList")
    add_count = len(add_lines)
    if add_count < 1:
        raise GeneratorError("self-check failed: add_count < 1")
    if add_count != expected_count:
        raise GeneratorError("self-check failed: count header mismatch")


def generate_resource(resource_id: str, base_dir: Path) -> Path:
    resources_dir = base_dir / "resources"
    dist_dir = base_dir / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    config_path = resources_dir / f"{resource_id}.yaml"
    if not config_path.exists():
        raise GeneratorError(f"resource config not found: {config_path}")

    resource = load_resource_config(config_path)
    if resource.resource_id != resource_id:
        raise GeneratorError("resource_id mismatch between file and contents")

    all_prefixes: List[str] = []
    if resource.source_type == "asn":
        if not resource.asns:
            raise GeneratorError("asn source missing asns")
        for asn in resource.asns:
            all_prefixes.extend(fetch_prefixes_for_asn(asn))
    else:
        all_prefixes.extend(fetch_prefixes_for_url(resource))

    networks = _dedup_sort(_normalize_ipv4(all_prefixes))
    contents = _render_rsc(resource, networks)

    tmp_path = dist_dir / f"{resource_id}.rsc.tmp"
    final_path = dist_dir / f"{resource_id}.rsc"

    try:
        tmp_path.write_text(contents)
        _self_check_rsc(resource, tmp_path.read_text())
        os.replace(tmp_path, final_path)
    except Exception as exc:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise GeneratorError(f"failed to write {final_path}") from exc

    return final_path


def generate_all(base_dir: Path) -> List[Path]:
    resources_dir = base_dir / "resources"
    if not resources_dir.exists():
        raise GeneratorError("resources directory not found")

    results = []
    for path in sorted(resources_dir.glob("*.yaml")):
        resource = load_resource_config(path)
        results.append(generate_resource(resource.resource_id, base_dir))

    return results
