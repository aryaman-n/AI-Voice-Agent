# AI Voice Agent

An end-to-end prototype that connects [SignalWire](https://signalwire.com) real-time voice streams with OpenAI's `gpt-4o-realtime-mini` model. The service exposes a FastAPI server that SignalWire can use to stream audio from phone calls to the OpenAI Realtime API, allowing you to run fully programmable AI voice agents with custom system prompts.

> **Disclaimer:** This repository is a prototype inspired by [aryaman-n/AIVA](https://github.com/aryaman-n/AIVA). It focuses on clarity and extensibility so you can adapt it to your own needs before deploying to production.

## Features

- 🔄 Real-time websocket bridge between SignalWire call audio and OpenAI Realtime.
- 🎙️ Customisable system prompts, voices, and models through environment variables.
- ⚙️ FastAPI application with REST and websocket endpoints ready for SignalWire LaML webhooks.
- 🧪 Local development server with hot-reload via `uvicorn`.
- 📦 Modular Python package for reuse in other projects.

## Repository structure

```
AI-Voice-Agent/
├── .env.example                # Sample environment variables
├── README.md                   # Project documentation
├── requirements.txt            # Python dependencies
└── src/
    └── voice_agent/
        ├── __init__.py         # (optional) namespace init if you add it later
        ├── api.py              # FastAPI application entry point
        ├── config.py           # Environment configuration helpers
        ├── openai_client.py    # OpenAI realtime websocket helper
        └── signalwire_bridge.py# SignalWire ↔ OpenAI streaming bridge
```

## Prerequisites

1. **Python 3.10+**
2. **SignalWire account** with:
   - Space URL (e.g. `example.signalwire.com`)
   - Project ID
   - API token that has Relay permissions
3. **OpenAI API key** with access to the realtime mini models.
4. Publicly accessible HTTPS endpoint (e.g. via [ngrok](https://ngrok.com)) when testing with real phone calls.

## Setup

1. **Clone and install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   Copy `.env.example` to `.env` and fill in your credentials. At minimum you must set:

   ```env
   OPENAI_API_KEY=sk-your-key
   SIGNALWIRE_SPACE_URL=example.signalwire.com
   SIGNALWIRE_PROJECT_ID=your-project-id
   SIGNALWIRE_API_TOKEN=PTxxxxxxxxxxxxxxxxxxxx
   VOICE_AGENT_SYSTEM_PROMPT=You are a helpful, concise voice assistant.
   ```

   The optional variables `OPENAI_REALTIME_MODEL`, `OPENAI_VOICE`, `SIGNALWIRE_STREAM_URL`, and `LOG_LEVEL` let you fine-tune behaviour. Set `SIGNALWIRE_STREAM_URL` to the public websocket URL (for example `wss://your-ngrok-domain.ngrok.io/signalwire/stream`) so the generated LaML points callers to the right place.

3. **Load the environment**

   ```bash
   export $(grep -v '^#' .env | xargs)
   ```

## Running the development server

Start the FastAPI application with `uvicorn`:

```bash
uvicorn voice_agent.api:app --reload --host 0.0.0.0 --port 8000
```

- `GET /health` returns a simple status payload.
- `POST /signalwire/voice` returns LaML XML that instructs SignalWire to stream the call audio to `wss://<your-public-domain>/signalwire/stream`. Replace `{{YOUR_SERVER_DOMAIN}}` in `api.py` or override at runtime before going live.
- `WS /signalwire/stream` accepts the websocket stream from SignalWire and bridges it to OpenAI.

When running locally, expose the server to the internet using a tunnelling service and update the `<Stream url="...">` in `api.py` accordingly (for example, `wss://<your-ngrok-subdomain>.ngrok.io/signalwire/stream`).

## Configuring SignalWire

1. **Create a LaML application** in the SignalWire dashboard.
2. Set the **voice webhook** URL to `https://<your-public-domain>/signalwire/voice`.
3. Attach the application to a phone number.
4. Ensure that **Realtime Streaming** is enabled for your project.

SignalWire will invoke `/signalwire/voice` when a call arrives. The XML response instructs SignalWire to open a websocket connection to `/signalwire/stream`, which the bridge uses to forward audio to OpenAI and send audio replies back to the caller.

## Customising behaviour

- **System prompt**: change `VOICE_AGENT_SYSTEM_PROMPT` for high-level behaviour.
- **Model & voice**: set `OPENAI_REALTIME_MODEL` and `OPENAI_VOICE` to any realtime-capable model/voice pair supported by OpenAI.
- **Logging**: set `LOG_LEVEL=DEBUG` to trace websocket events while debugging call flows.

The `SignalWireRealtimeBridge` class is intentionally small so that you can extend it with features like call transcription, context storage, analytics, or CRM integrations.

## Making outbound calls (optional)

`signalwire_bridge.connect_to_signalwire_room` illustrates how to connect to a SignalWire video/voice room using Relay websockets. You can adapt it to place outbound calls or join rooms where agents participate. This helper is not invoked by default but is included for reference when building more advanced call flows.

## Testing without a phone call

While you cannot fully emulate the SignalWire websocket without their infrastructure, you can sanity-check the API server:

```bash
curl http://localhost:8000/health
uvicorn voice_agent.api:app --reload  # check logs for startup confirmation
```

For end-to-end validation, place a call to the configured SignalWire number after deploying and monitor the server logs to confirm audio frames flow between SignalWire and OpenAI.

## Troubleshooting

- **401 from OpenAI**: verify `OPENAI_API_KEY` and that your account has realtime access.
- **SignalWire websocket closes immediately**: double-check that the `<Stream>` URL is reachable over HTTPS and that the certificate is valid.
- **No audio responses**: ensure your system prompt encourages vocal replies and that the OpenAI voice you selected is supported by the model.

## License

This project is released under the MIT License. Use at your own risk and be mindful of telephony regulations in your jurisdiction.
