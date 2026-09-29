# Backend connection guide

PlayzAI uses this flow:

```text
Android app --HTTPS + device/session auth--> PlayzAI backend --provider credential--> AI provider
Android app <--reply, status, request ID-- PlayzAI backend
```

The Android app defaults to local Demo / Offline Mode. It only displays `Connected` after it can reach `/health` and successfully authenticate against `/api/auth/status`. A configured URL without valid credentials is shown as authentication required, not connected.

## Required backend environment

Copy `backend/.env.example` to `backend/.env` or provide equivalent deployment environment variables. At minimum for real AI:

```text
AI_API_KEY=<provider secret, backend only>
AI_BASE_URL=<authorized OpenAI-compatible provider base URL>
AI_MODEL=<provider model identifier>
AUTH_SECRET=<long random backend secret>
```

Optional security variables:

```text
PLAYZAI_ENROLLMENT_SECRET=<protects device registration>
PLAYZAI_MASTER_KEY=<owner-only panic key>
SESSION_TTL_SECONDS=3600
```

No real values are included in this project. A provider credential must be supplied by the owner/operator before real AI calls can succeed.

## Android configuration

1. Start the backend behind HTTPS or an HTTPS reverse proxy.
2. Register the Android device using `/api/devices/register`.
3. Copy the one-time returned `api_key` into the Android Settings backend authentication section.
4. Enter the device ID and the HTTPS backend base URL.
5. Disable Demo / Offline Mode.
6. Use **Check connection**. The app must receive both a healthy backend response and an authenticated status response.

The API key is encrypted using the Android Keystore. It is not written to logs, source code, or the APK as a configured value.

## Provider limitations

The backend adapter expects an OpenAI-compatible `POST {AI_BASE_URL}/chat/completions` API and parses `choices[0].message.content`. If the configured provider uses a different contract, add a backend-only adapter; do not move provider credentials or provider-specific calls into Android.

The current repository backend does not contain a chat provider endpoint or a Windows pairing protocol. Those are now represented by authenticated, documented backend interfaces, while the existing safe command allowlist and agent components remain intact.
