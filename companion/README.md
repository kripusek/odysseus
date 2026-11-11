# Companion bridge

A thin, additive layer so a LAN client (e.g. a phone) can discover what an
Odysseus server offers and pair to it, without duplicating any LLM logic.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/companion/ping` | session or token | cheap, auth-validated health check |
| GET | `/api/companion/info` | session or token | server identity + capability flags |
| GET | `/api/companion/models` | session or token | the **caller's own** model endpoints |
| GET | `/api/companion/pair` | **admin cookie** | pairing page (a form; never mints) |
| POST | `/api/companion/pair` | **admin cookie** | mint a one-time pairing token (`?format=json` for an in-app screen) |

`/models` scopes to the caller's real owner plus legacy null-owner shared rows
(same rule as `owner_filter`) and never returns API-key material.

## Pairing CSRF posture

Minting happens **only on POST**. The session cookie is `SameSite=Lax`
(`routes/auth_routes.py`), so a browser will not send it on a cross-site POST —
the same protection `POST /api/tokens` relies on. A `GET` would be unsafe (Lax
cookies ride top-level GET navigations), so `GET /pair` only renders a form.
Minting invalidates the auth middleware's token cache, so a freshly minted token
works on the next request without a restart.

The pairing/scoping rules live in small, tested units (`token_owner`,
`owner_can_see`, `mint_pairing_token`, `pairing.*`) — see
`tests/test_companion_readonly.py` and `tests/test_companion_pairing.py`.

## HTTPS pairing through Cloudflare Access

The optional v2 QR is enabled only when `COMPANION_BASE_URL` is exactly
`https://ai.kripusek.top` and `COMPANION_ACCESS_CREDENTIALS_FILE` names an
operator-managed private JSON file outside the repository and served folders.
The file contains exactly `cf_access_client_id` and `cf_access_client_secret`
strings. Restrict its Windows ACL to the server account and the administrator;
the application does not verify the Windows ACL. Restart or reconfigure the
server separately to apply environment changes. Never put these values in logs,
command arguments, source control, or screenshots.

The v2 payload has `v`, `base_url`, `token`, `cf_access_client_id` and
`cf_access_client_secret`. It contains both a chat-scoped Odysseus bearer token
and a Cloudflare service token: either may grant access independently, and
revoking the Odysseus token does not revoke Cloudflare credentials. Use a
separate, narrowly scoped Cloudflare Access policy and rotate credentials if a
QR is exposed. This feature neither creates nor changes that policy. Responses
containing pairing data are marked `no-store`. The HTML v2 page shows secrets
only in the QR image; JSON responses still contain the raw payload. If QR
rendering fails, no Odysseus token is persisted. Generation requires an
authenticated administrator cookie and is disabled when authentication is off.
Legacy v1 LAN QR remains available when HTTPS is not configured.

## Confined text chat

New v2 HTTPS pairing tokens carry `chat,companion`; v1 LAN tokens retain `chat`. On authenticated routes, middleware
limits these tokens to `POST /api/companion/safe-chat` and `GET` ping/info.
This does not change previously issued tokens; revoke older pairing tokens
separately. The endpoint accepts only `{"messages":[{"role":"user",
"content":"..."}]}` with user/assistant text history, 1?16 messages,
up to 8000 characters each and 32000 total; the last role must be user. It
returns `{"response":"..."}`. No history is stored by this endpoint.
It makes one request to `127.0.0.1:17012` using the private model key file
under `%LOCALAPPDATA%/Odysseus-kripusek-data/private-model/llama-api-key.txt`;
there are no agent tools, provider selection or webhook dispatch. HTTP 503
means that the key or local model is unavailable. It does not expose the
model service to the network.
