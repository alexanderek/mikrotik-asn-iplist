# mikrotik-asn-iplist

IPv4 address-list files for MikroTik RouterOS v7. Use the loader scripts to fetch and import lists from `dist/`.

## What is this

- `dist/*.rsc` — ready-to-import address-list files (one resource per file).
- `routeros/loader_eu.rsc` and `routeros/loader_ru.rsc` — the only policy point on the router.

## What you need on MikroTik

1. Upload and schedule **one** loader (`routeros/loader_eu.rsc` or `routeros/loader_ru.rsc`).
2. Edit the loader:
   - `listName` — target address-list name (e.g. `blacklist_eu` / `blacklist_ru`).
   - `resources` — list of enabled providers (resource_id strings).

Example scheduler:

```routeros
/system/scheduler
add name=iplist_auto_ru interval=1w on-event="/system script run loader_ru"
```

## How loaders work (high-level)

- Fetch `dist/<resource>.rsc` from GitHub raw.
- Validate file and metadata.
- Remove old entries for that resource (by comment tag).
- Import the new file.
- Clean up temp file.

## Configuring resources

The place to enable/disable providers is the loader’s `resources` list:

```routeros
:global resources {
  "cloudflare";
  "fastly";
  "googlecloud";
  "aws"
}
```

Each resource maps to exactly one `dist/<resource>.rsc`.

## Data sources (official vs ASN)

- Official provider feeds are preferred (Cloudflare, Google Cloud, AWS, Telegram, etc.).
- ASN/BGP sources are used only when no official feed exists or coverage is insufficient.
- ASN/BGP is fallback, not default.

## Guarantees & limitations

- IPv4 only.
- Fail-hard on bad source data (non-200, malformed, empty) — old lists stay in place.
- Default `collapse=shadowed`: removes only fully-covered subnets (no aggressive aggregation).
- One resource = one `.rsc` file; loaders decide which resources to apply.

## For developers (optional)

- Generator is the source of truth for `dist/`.
- Cache policy:
  - `--allow-cache` uses cache **only** on HTTP 304.
  - Stale cache requires `--allow-stale-cache` and is explicitly logged.
- Collapse mode:
  - `--collapse=shadowed` (default) or `--collapse=none`.

Common commands:

```bash
python -m generator generate --all --allow-cache
python -m generator generate --all --collapse=none --allow-cache
pytest -q
```
