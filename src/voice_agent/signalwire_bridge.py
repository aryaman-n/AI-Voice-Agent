"""Websocket bridge between SignalWire voice streams and OpenAI realtime."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Optional

import websockets
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from .config import settings
from .openai_client import OpenAIRealtimeClient

LOGGER = logging.getLogger(__name__)


class SignalWireRealtimeBridge:
    """Handle a SignalWire websocket session and mirror audio to OpenAI."""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self._openai_client = OpenAIRealtimeClient(settings.openai)
        self._stream_id: Optional[str] = None
        self._ready = asyncio.Event()

    async def run(self) -> None:
        await self.websocket.accept()
        async with self._openai_client:
            receiver = asyncio.create_task(self._receive_from_signalwire())
            forwarder = asyncio.create_task(self._forward_openai_responses())
            done, pending = await asyncio.wait(
                {receiver, forwarder},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            for task in done:
                if task.exception():
                    raise task.exception()

    async def _receive_from_signalwire(self) -> None:
        while True:
            try:
                message = await self.websocket.receive_text()
            except WebSocketDisconnect:
                LOGGER.info("SignalWire websocket disconnected")
                break
            payload = json.loads(message)
            event_type = payload.get("event") or payload.get("type")
            LOGGER.debug("SignalWire event: %s", event_type)

            if event_type == "start":
                self._stream_id = payload.get("streamId") or payload.get("stream_id")
                await self._on_start(payload)
            elif event_type == "media":
                await self._on_media(payload)
            elif event_type in {"mark", "connected"}:
                continue
            elif event_type in {"stop", "close"}:
                await self._openai_client.send_json({"type": "input_audio_buffer.commit"})
                await self._openai_client.send_json({"type": "response.create", "response": {}})
                break

    async def _on_start(self, payload: Dict) -> None:
        stream_id = payload.get("streamId") or payload.get("stream_id")
        if not stream_id:
            LOGGER.warning("Missing stream id in start event: %s", payload)
            return
        self._stream_id = stream_id
        await self._send_signalwire({"event": "ready"})
        self._ready.set()
        LOGGER.info("SignalWire stream ready: %s", stream_id)

    async def _on_media(self, payload: Dict) -> None:
        if "media" not in payload:
            return
        audio_payload = payload["media"].get("payload")
        if not audio_payload:
            return
        await self._openai_client.send_audio_chunk(audio_payload)

    async def _forward_openai_responses(self) -> None:
        await self._ready.wait()
        async for event in self._openai_client.responses():
            event_type = event.get("type")
            if event_type == "response.output_audio.delta":
                delta = event.get("delta", {})
                audio_chunk = delta.get("audio")
                if audio_chunk:
                    await self._send_audio_to_signalwire(audio_chunk)
            elif event_type == "response.completed":
                LOGGER.debug("OpenAI response completed")
            elif event_type == "error":
                LOGGER.error("OpenAI error: %s", event)

    async def _send_audio_to_signalwire(self, audio_base64: str) -> None:
        if not self._stream_id:
            LOGGER.debug("Ignoring audio before stream id assignment")
            return
        response = {
            "event": "media",
            "streamId": self._stream_id,
            "media": {
                "payload": audio_base64,
            },
        }
        await self._send_signalwire(response)

    async def _send_signalwire(self, payload: Dict) -> None:
        LOGGER.debug("Sending to SignalWire: %s", payload.get("event"))
        await self.websocket.send_text(json.dumps(payload))


async def connect_to_signalwire_room(room_name: str) -> None:
    """Example helper showing how to create an outbound call via SignalWire."""

    relay_url = f"wss://{settings.signalwire.space_url}/relay"
    headers = {
        "Authorization": settings.signalwire.api_token,
        "SW-Project": settings.signalwire.project_id,
    }

    async with websockets.connect(relay_url, extra_headers=headers) as socket:
        await socket.send(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "signalwire.connect",
                    "params": {"project": settings.signalwire.project_id},
                }
            )
        )
        await socket.recv()

        await socket.send(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "video.room.connect",
                    "params": {
                        "room": room_name,
                    },
                }
            )
        )
        LOGGER.info("Joined SignalWire room %s", room_name)
        while True:
            message = await socket.recv()
            LOGGER.debug("Relay message: %s", message)
