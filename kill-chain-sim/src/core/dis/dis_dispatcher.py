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
    Supports multiple handlers per PDU type (broadcast pattern).

    Thread-safe: register/unregister operations are protected by a lock.
    """

    def __init__(self) -> None:
        self._handlers: Dict[int, list] = {}  # pdu_type -> list of handlers
        self._lock = threading.Lock()

    @property
    def handlers(self) -> Dict[int, list]:
        """Return a copy of the registered handlers dict."""
        with self._lock:
            return {k: list(v) for k, v in self._handlers.items()}

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
            if pdu_type not in self._handlers:
                self._handlers[pdu_type] = []
            self._handlers[pdu_type].append(handler)

    def unregister(self, pdu_type: int) -> None:
        """Remove the handler for a PDU type.

        Args:
            pdu_type: PDU type integer (1-255).
        """
        with self._lock:
            self._handlers.pop(pdu_type, None)

    def dispatch(self, pdu: Dict) -> Optional[any]:
        """Dispatch a PDU to all registered handlers for its type.

        Calls all handlers registered for pdu['pdu_type'] with the
        full PDU dict. If no handlers are registered, silently returns.

        Args:
            pdu: Parsed PDU data dict. Must contain a 'pdu_type' key
                 with an integer value (1-255).

        Returns:
            The return value of the last handler called, or None if no handlers found.
        """
        pdu_type = pdu.get("pdu_type")
        with self._lock:
            handlers = list(self._handlers.get(pdu_type, []))

        results = []
        for handler in handlers:
            try:
                result = handler(pdu)
                results.append(result)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Handler error: {e}")
        return results[-1] if results else None
        return None