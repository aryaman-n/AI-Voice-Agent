"""FastAPI application exposing the SignalWire voice agent endpoints."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .signalwire_bridge import SignalWireRealtimeBridge

LOGGER = logging.getLogger(__name__)

app = FastAPI(title="AI Voice Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def configure_logging() -> None:
    logging.basicConfig(level=settings.log_level)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


@app.post("/signalwire/voice")
async def signalwire_voice_webhook() -> Response:
    """Respond to SignalWire call webhook with instructions to stream audio."""
    stream_url = settings.signalwire.stream_url or "wss://YOUR_SERVER_DOMAIN/signalwire/stream"
    xml_response = (
        """
    <Response>
        <Connect>
            <Stream url="{stream_url}"/>
        </Connect>
    </Response>
    """
        .strip()
        .format(stream_url=stream_url)
    )
    return Response(content=xml_response, media_type="application/xml")


@app.websocket("/signalwire/stream")
async def signalwire_stream(websocket: WebSocket) -> None:
    LOGGER.info("SignalWire websocket connected from %s", websocket.client)
    bridge = SignalWireRealtimeBridge(websocket)
    await bridge.run()


@app.get("/")
async def root() -> dict:
    return {
        "message": "AI Voice Agent server is running",
        "documentation": str(Path("/docs")),
    }
