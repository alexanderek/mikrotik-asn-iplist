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

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

python -m generator generate --resource cloudflare
python -m generator generate --all

pytest
```
