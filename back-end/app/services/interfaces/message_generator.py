from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from shared.models.message import Message


@dataclass
class MessageItem:
    message: str
    timeout: int
    should_send: bool
    next_send_time: datetime
    data: Optional[Dict[str, Any]] = None


class IMessageGeneratorService(ABC):
    
    @abstractmethod
    async def generate_message(
        self,
        message: Message,
        force = False,
        include_data = False,
    ) -> MessageItem | None:
        ...