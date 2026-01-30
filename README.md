# MikroTik_ASN_IPList

Automated generation of MikroTik RouterOS v7.x firewall address-list entries from ASN announced IPv4 prefixes.

- Source of truth: `generator/`
- Output: `dist/*.rsc`
- RouterOS loader scripts: `routeros/`

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

python -m generator generate --resource cloudflare
python -m generator generate --all

pytest
```
