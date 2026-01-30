# MikroTik_ASN_IPList

Automated generation of MikroTik RouterOS v7.x firewall address-list entries from ASN announced IPv4 prefixes.

- Source of truth: `generator/`
- Output: `dist/*.rsc`
- RouterOS loader scripts: `routeros/loader_eu.rsc`, `routeros/loader_ru.rsc`

## RouterOS loaders

- Use `routeros/loader_eu.rsc` and `routeros/loader_ru.rsc`.
- Policy is managed by the `resources` list inside each loader.
- Each resource maps to a single `dist/<resource>.rsc`.
- To enable a provider, add its `resource_id` to the resources list in the desired loader (EU/RU). By default loaders can be shipped with empty lists.

## Migration

- Previously there was a per-resource loader script.
- Now use `routeros/loader_eu.rsc` and `routeros/loader_ru.rsc` only.
- Policy is controlled by membership in each loader’s `resources` list.
- `dist/<resource>.rsc` is parameterized via `$AddressList`.

## Official feeds

- Example: Cloudflare IPv4 feed.
- URL: https://www.cloudflare.com/ips-v4
- Format: plain CIDR per line.
- Parsing: IPv4 only; IPv6 ignored; malformed line => fail-hard.
- Example: Google Cloud feed.
- URL: https://www.gstatic.com/ipranges/cloud.json
- Format: JSON prefixes[], use ipv4Prefix (IPv4 only; ignore ipv6Prefix).
- Parsing: fail-hard on malformed/empty result.
- Example: Fastly public IP list.
- URL: https://api.fastly.com/public-ip-list
- Format: JSON addresses[] (IPv4 only; ignore ipv6_addresses).
- Parsing: fail-hard on malformed/empty result.

## Loader logging

- Example start: `iplist: event=start scope=EU list=blacklist_eu resources_count=1 runId=2026-01-30 15:00:00`
- Example fetch: `iplist: event=fetch scope=EU list=blacklist_eu resource=cloudflare url=... runId=...`
- Example import_ok: `iplist: event=import_ok scope=EU list=blacklist_eu resource=cloudflare bytes=1234 total=15 runId=...`

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

python -m generator generate --resource cloudflare
python -m generator generate --all

pytest
```
