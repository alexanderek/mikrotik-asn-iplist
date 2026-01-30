from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import ipaddress
import json
import os
from typing import Iterable, List

import requests
import yaml

RIPESTAT_URL = "https://stat.ripe.net/data/announced-prefixes/data.json"
DEFAULT_TIMEOUT = 10


@dataclass(frozen=True)
class ResourceConfig:
    resource_id: str
    asns: List[str]
    target_list: str


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
    asns = data.get("asns")
    target_list = data.get("target_list")

    if not resource_id or not isinstance(resource_id, str):
        raise GeneratorError(f"invalid resource_id in {path}")
    if not asns or not isinstance(asns, list) or not all(isinstance(a, str) for a in asns):
        raise GeneratorError(f"invalid asns list in {path}")
    if not target_list or not isinstance(target_list, str):
        raise GeneratorError(f"invalid target_list in {path}")

    return ResourceConfig(resource_id=resource_id, asns=asns, target_list=target_list)


def _fetch_json(url: str, params: dict) -> dict:
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
            f"/ip/firewall/address-list add list={resource.target_list} address={net} "
            f"comment=\"iplist:auto:{resource.resource_id}\""
        )
    return "\n".join(header + lines) + "\n"


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
    for asn in resource.asns:
        all_prefixes.extend(fetch_prefixes_for_asn(asn))

    networks = _dedup_sort(_normalize_ipv4(all_prefixes))
    contents = _render_rsc(resource, networks)

    tmp_path = dist_dir / f"{resource_id}.rsc.tmp"
    final_path = dist_dir / f"{resource_id}.rsc"

    try:
        tmp_path.write_text(contents)
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
