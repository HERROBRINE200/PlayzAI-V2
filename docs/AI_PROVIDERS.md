# PlayzAI V2 — Multi-AI Provider Architecture & Setup Guide

PlayzAI V2 integrates a genuine multi-provider AI subsystem supporting multiple concurrent provider configurations, granular model selection, dynamic model discovery, intelligent fallback routing, and backend secret encryption.

---

## 1. Supported AI Providers

### 1.1 Google Gemini
- **Protocol**: Google Generative Language REST API (`/v1beta`)
- **Base URL**: `https://generativelanguage.googleapis.com`
- **Default Model**: `gemini-1.5-flash` (also supports `gemini-1.5-pro`, `gemini-2.0-flash-exp`, `gemini-1.0-pro`)
- **Authentication**: API key parameter `?key={API_KEY}`
- **Model Discovery**: `GET /v1beta/models?key={API_KEY}`
- **System Instructions**: Native `systemInstruction` parts payload
- **Setup**:
  1. Obtain an API key from Google AI Studio (`https://aistudio.google.com`).
  2. In the Dashboard under **AI Providers**, click **Add AI Provider**.
  3. Select **Google Gemini**, enter display name and API key.
  4. Click **Test** to verify connection and discover models.

### 1.2 OpenAI (Official)
- **Protocol**: OpenAI Chat Completions REST API (`/v1/chat/completions`)
- **Base URL**: `https://api.openai.com/v1`
- **Default Model**: `gpt-4o-mini` (also supports `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`, `o1-mini`, `o1-preview`)
- **Authentication**: `Authorization: Bearer {API_KEY}`
- **Model Discovery**: `GET /v1/models`
- **Setup**:
  1. Obtain API key from OpenAI Platform (`https://platform.openai.com/api-keys`).
  2. In Dashboard, click **Add AI Provider**, choose **OpenAI**, and save.

### 1.3 Anthropic Claude
- **Protocol**: Anthropic Messages REST API (`/v1/messages`)
- **Base URL**: `https://api.anthropic.com/v1`
- **Default Model**: `claude-3-5-sonnet-20241022` (also supports `claude-3-5-haiku-20241022`, `claude-3-opus-20240229`, `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`)
- **Headers**: `x-api-key: {API_KEY}`, `anthropic-version: 2023-06-01`
- **Setup**:
  1. Obtain API key from Anthropic Console (`https://console.anthropic.com`).
  2. In Dashboard, click **Add AI Provider**, select **Anthropic Claude**, and save.

### 1.4 OpenAI-Compatible Endpoints
- **Supported Providers**: Groq, Together AI, DeepSeek, Ollama, OpenRouter, Mistral, Perplexity, local vLLM.
- **Protocol**: Standard `/chat/completions` and `/models`.
- **Examples**:
  - **Groq**: Base URL `https://api.groq.com/openai/v1`, Model `llama-3.3-70b-versatile`
  - **DeepSeek**: Base URL `https://api.deepseek.com/v1`, Model `deepseek-chat`
  - **Ollama**: Base URL `http://localhost:11434/v1`, Model `llama3:latest` (no API key required)

### 1.5 Custom AI Endpoints
- **Protocol**: Flexible HTTP JSON payload for internal services or custom AI proxies.

---

## 2. Dynamic Fallback Routing

When multiple providers are configured, PlayzAI uses priority-ordered fallback:

```
User Message
     ↓
Primary Provider (e.g., Gemini Pro)
     ↓ (Transient Failure: 429 Rate Limit / 503 / Timeout)
Secondary Provider (e.g., OpenAI GPT-4o)
     ↓ (Transient Failure)
Tertiary Provider (e.g., Claude 3.5 Sonnet)
     ↓
Truthful AI Reply returned with 'provider_used' & 'fallback_occurred=True'
```

- **Transient Failures**: Triggers fallback to ensure maximum availability.
- **Permanent Auth Errors** (401 Invalid Key): Returns safe error immediately so operators can fix credentials.

---

## 3. Secret Protection & Masking

- API keys are stored exclusively in the backend SQLite database.
- The Dashboard only receives masked tokens (e.g., `sk-proj-••••••••4a2b`).
- Secrets are NEVER logged to console stdout, audit logs, or client APKs.
- Environment variable `.env.example` contains only non-secret placeholders.
