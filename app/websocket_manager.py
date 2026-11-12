
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Each chat can have multiple connected users.
        self.active_connections: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, chat_id: int, websocket: WebSocket) -> None:
        """Register an already-accepted WebSocket connection."""
        connections = self.active_connections[chat_id]

        if websocket not in connections:
            connections.append(websocket)

        logger.info(
            "WebSocket registered: chat_id=%s, active_connections=%s",
            chat_id,
            len(connections),
        )

    async def disconnect(self, chat_id: int, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from its chat."""
        connections = self.active_connections.get(chat_id)

        if not connections:
            return

        if websocket in connections:
            connections.remove(websocket)

        if not connections:
            self.active_connections.pop(chat_id, None)

        logger.info("WebSocket unregistered: chat_id=%s", chat_id)

    async def send_to_chat(
        self,
        chat_id: int,
        message: dict,
    ) -> None:
        """Broadcast a JSON event to all connected users in a chat."""
        connections = list(self.active_connections.get(chat_id, []))
        disconnected = []

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                logger.exception(
                    "WebSocket send failed: chat_id=%s",
                    chat_id,
                )
                disconnected.append(connection)

        for connection in disconnected:
            await self.disconnect(chat_id, connection)


# IMPORTANT: Instantiate the class; do not remove the parentheses.
manager = ConnectionManager()
