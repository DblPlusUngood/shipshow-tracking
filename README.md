# ShipShow Tracking

Personal read-only plugin for the local ChatGPT/Codex app. It uses the documented ShipShow REST API and avoids the currently failing OAuth connection. It is not a deployed ChatGPT web connector or a background bot.

## What it does

- Reads shipments, package titles, arrival estimates, recent carrier events and comments.
- Stores the API key in macOS Keychain; the key is never embedded in source, manifests or normal command arguments.
- Makes requests only to `https://api.shipshow.net/external/getTrackings`, refuses redirects, suppresses credential-bearing errors, and caches reads for 60 seconds.
- Exposes only `list_shipments` and `connection_status`; no modifications, purchases, forwarding, scheduling or package management.
- Shows delivery exceptions only when known and relevant. No routine signature/unknown clutter.

## Configure the key

Run `python3 scripts/shipshow.py setup-key` in an interactive terminal. Paste the existing ShipShow API key into the hidden prompt. It is saved under the Keychain service **Facilitate.Life ShipShow API**, account **shipshow-tracking**, then checked against ShipShow. An active ShipShow Pro subscription is required by the REST API.

macOS may ask for Keychain access. The plugin can alternatively read `SHIPSHOW_API_KEY` from its process environment. Do not put the key in chat, a Git repository, a browser URL or OAuth's client-secret field.

## Limits

Purchase quantities, prices and shipping charges still need order/invoice evidence. The plugin returns source-provided delivery messages; signature/freight field coverage is not established. Unrecognized field names are exposed for schema review without exporting arbitrary account configuration. Carrier URLs, media, arbitrary config and precise coordinates are not returned.

`has_more` and `next_offset` describe pagination. A different request within one minute returns a retry message; repeating the same request within one minute returns the cached result with its original timestamp. Nothing polls in the background. Cache and rate pacing are per server process, so multiple simultaneous clients must coordinate usage.

This plugin uses a local stdio connection. Using it from ChatGPT on the web would require a separately deployed, authenticated MCP endpoint; that is not installed by this package. Cursor can run the same server using an ordinary local MCP command entry.

Sources: [ShipShow API](https://www.shipshow.net/api), [ShipShow MCP](https://www.shipshow.net/mcp).

Project tracking: [Facilitate.Life in the Notion Projects database](https://app.notion.com/p/1ceaae1ec0e04d25a741ea513cbb748c)
