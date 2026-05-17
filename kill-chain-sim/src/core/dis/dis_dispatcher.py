"""DIS PDU Dispatcher.

Routes received PDUs to registered handlers based on PDU type.
"""

from __future__ import annotations

import threading
from typing import Callable, Dict, Optional


class DisDispatcher:
    """Dispatcher that routes DIS PDUs to registered handlers.

    Handlers are registered by PDU type (integer 1-255) and called
    with the parsed PDU data dict when a matching PDU is dispatched.

    Thread-safe: register/unregister operations are protected by a lock.
    """

    def __init__(self) -> None:
        self._handlers: Dict[int, Callable[[Dict], any]] = {}
        self._lock = threading.Lock()

    @property
    def handlers(self) -> Dict[int, Callable[[Dict], any]]:
        """Return a copy of the registered handlers dict.

        Returns:
            Dict mapping pdu_type (int) to handler (callable).
        """
        with self._lock:
            return dict(self._handlers)

    def register(self, pdu_type: int, handler: Callable[[Dict], any]) -> None:
        """Register a handler for a PDU type.

        Args:
            pdu_type: PDU type integer (1-255).
            handler: Callable that accepts a parsed PDU data dict.

        Raises:
            TypeError: If handler is not callable.
            ValueError: If pdu_type is outside the valid range 1-255.
        """
        if not callable(handler):
            raise TypeError(f"handler must be callable, got {type(handler).__name__}")
        if not isinstance(pdu_type, int) or pdu_type < 1 or pdu_type > 255:
            raise ValueError(f"pdu_type must be an integer in range 1-255, got {pdu_type}")

        with self._lock:
            self._handlers[pdu_type] = handler

    def unregister(self, pdu_type: int) -> None:
        """Remove the handler for a PDU type.

        Args:
            pdu_type: PDU type integer (1-255).
        """
        with self._lock:
            self._handlers.pop(pdu_type, None)

    def dispatch(self, pdu: Dict) -> Optional[any]:
        """Dispatch a PDU to its registered handler.

        Looks up the handler by pdu['pdu_type'] and calls it with the
        full PDU dict. If no handler is registered for the type, the
        call is silently ignored.

        Args:
            pdu: Parsed PDU data dict. Must contain a 'pdu_type' key
                 with an integer value (1-255).

        Returns:
            The return value of the handler, or None if no handler found.
        """
        pdu_type = pdu.get("pdu_type")
        with self._lock:
            handler = self._handlers.get(pdu_type)

        if handler is not None:
            return handler(pdu)
        return None