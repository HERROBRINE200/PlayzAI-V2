# Security rules

1. Never expose the backend directly to the public internet without TLS and a hardened reverse proxy.
2. Never give the language model arbitrary shell access.
3. Use a strict action allowlist and validate every argument.
4. Require explicit confirmation for destructive operations.
5. Store credentials in a secret manager/environment, never in source control.
6. Rotate device keys and revoke compromised devices.
7. Rate-limit authentication and command endpoints.
8. Treat observed IPs as evidence, not identity. WhatsApp does not expose a sender's network IP to the bot in the ordinary message API.
9. Security alerts should offer block/unblock decisions; no retaliation against suspected attackers.
