import asyncio
import json
import logging
from typing import Dict, List, Optional
from fastapi import WebSocket

logger = logging.getLogger("guardianshield.websocket")


class ConnectionManager:
    """Manages active WebSockets for GuardianShield devices."""

    def __init__(self):
        # Maps device_id -> WebSocket
        self._active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, device_id: str, websocket: WebSocket) -> None:
        """Accepts and stores the WebSocket connection for a device."""
        await websocket.accept()
        async with self._lock:
            # If device already has an open socket, close the previous one cleanly
            if device_id in self._active_connections:
                old_ws = self._active_connections[device_id]
                try:
                    await old_ws.close(code=1000, reason="New connection opened for device")
                except Exception:
                    pass
            self._active_connections[device_id] = websocket
        logger.info(f"Device connected: {device_id} (Total online: {len(self._active_connections)})")

    async def disconnect(self, device_id: str) -> None:
        """Removes the device's WebSocket from active connections."""
        async with self._lock:
            if device_id in self._active_connections:
                del self._active_connections[device_id]
        logger.info(f"Device disconnected: {device_id} (Total online: {len(self._active_connections)})")

    def is_online(self, device_id: str) -> bool:
        """Checks if a device currently has an open WebSocket."""
        return device_id in self._active_connections

    def get_online_devices(self) -> List[str]:
        """Returns a list of all currently connected device IDs."""
        return list(self._active_connections.keys())

    def get_online_count(self) -> int:
        """Returns total connected devices count."""
        return len(self._active_connections)

    async def send_personal_message(self, message: dict, device_id: str) -> bool:
        """Sends a JSON message directly to a target device."""
        ws: Optional[WebSocket] = None
        async with self._lock:
            ws = self._active_connections.get(device_id)

        if not ws:
            logger.warning(f"Failed to send message: Device {device_id} is offline")
            return False

        try:
            await ws.send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Error sending message to {device_id}: {e}")
            await self.disconnect(device_id)
            return False

    async def broadcast(self, message: dict, exclude_device_id: Optional[str] = None) -> None:
        """Broadcasts a JSON message to all connected devices."""
        async with self._lock:
            active_items = list(self._active_connections.items())

        for dev_id, ws in active_items:
            if exclude_device_id and dev_id == exclude_device_id:
                continue
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Broadcast error to {dev_id}: {e}")
                await self.disconnect(dev_id)


manager = ConnectionManager()
