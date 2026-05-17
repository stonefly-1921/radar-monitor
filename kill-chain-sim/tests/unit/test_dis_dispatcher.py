import pytest
from src.core.dis.dis_dispatcher import DisDispatcher


class TestDisDispatcher:
    """Test suite for DisDispatcher."""

    def test_register_and_dispatch(self):
        """Test registering a handler and dispatching a PDU."""
        dispatcher = DisDispatcher()
        calls = []

        def handler(pdu):
            calls.append(pdu)

        dispatcher.register(1, handler)
        dispatcher.dispatch({"pdu_type": 1, "data": "test"})

        assert len(calls) == 1
        assert calls[0]["data"] == "test"

    def test_register_multiple_pdu_types(self):
        """Test registering handlers for multiple PDU types."""
        dispatcher = DisDispatcher()
        calls = []

        def handler1(pdu):
            calls.append(("type1", pdu))

        def handler2(pdu):
            calls.append(("type2", pdu))

        dispatcher.register(10, handler1)
        dispatcher.register(20, handler2)

        dispatcher.dispatch({"pdu_type": 10, "payload": "a"})
        dispatcher.dispatch({"pdu_type": 20, "payload": "b"})

        assert len(calls) == 2
        assert calls[0] == ("type1", {"pdu_type": 10, "payload": "a"})
        assert calls[1] == ("type2", {"pdu_type": 20, "payload": "b"})

    def test_dispatch_no_handler(self):
        """Test dispatching a PDU with no registered handler does not raise."""
        dispatcher = DisDispatcher()
        # Should not raise
        dispatcher.dispatch({"pdu_type": 99, "data": " orphan"})

    def test_unregister(self):
        """Test unregistering a handler removes it."""
        dispatcher = DisDispatcher()
        calls = []

        def handler(pdu):
            calls.append(pdu)

        dispatcher.register(5, handler)
        dispatcher.unregister(5)
        dispatcher.dispatch({"pdu_type": 5, "data": "should not reach handler"})

        assert len(calls) == 0

    def test_unregister_nonexistent(self):
        """Test unregistering a non-existent handler does not raise."""
        dispatcher = DisDispatcher()
        # Should not raise
        dispatcher.unregister(255)

    def test_handlers_property_empty(self):
        """Test handlers property returns empty dict initially."""
        dispatcher = DisDispatcher()
        assert dispatcher.handlers == {}

    def test_handlers_property_returns_registered(self):
        """Test handlers property returns all registered handlers."""
        dispatcher = DisDispatcher()

        def h1(pdu):
            pass

        def h2(pdu):
            pass

        dispatcher.register(1, h1)
        dispatcher.register(2, h2)

        handlers = dispatcher.handlers
        assert len(handlers) == 2
        assert handlers[1] is h1
        assert handlers[2] is h2

    def test_register_non_callable_raises(self):
        """Test registering a non-callable raises TypeError."""
        dispatcher = DisDispatcher()
        with pytest.raises(TypeError):
            dispatcher.register(1, "not a callable")

        with pytest.raises(TypeError):
            dispatcher.register(1, 42)

    def test_register_pdu_type_out_of_range_raises(self):
        """Test registering a pdu_type outside 1-255 raises ValueError."""
        dispatcher = DisDispatcher()

        with pytest.raises(ValueError):
            dispatcher.register(0, lambda p: None)

        with pytest.raises(ValueError):
            dispatcher.register(256, lambda p: None)

        with pytest.raises(ValueError):
            dispatcher.register(-1, lambda p: None)

    def test_dispatch_returns_handler_result(self):
        """Test dispatch returns whatever the handler returns."""
        dispatcher = DisDispatcher()

        def handler(pdu):
            return pdu["value"] * 2

        dispatcher.register(7, handler)
        result = dispatcher.dispatch({"pdu_type": 7, "value": 21})
        assert result == 42

    def test_handler_receives_full_pdu_dict(self):
        """Test handler receives the complete PDU dict."""
        dispatcher = DisDispatcher()
        received = None

        def handler(pdu):
            nonlocal received
            received = pdu

        dispatcher.register(3, handler)
        dispatcher.dispatch({"pdu_type": 3, "foo": "bar", "nested": {"a": 1}})

        assert received == {"pdu_type": 3, "foo": "bar", "nested": {"a": 1}}

    def test_thread_safety_register(self):
        """Test register is thread-safe (no deadlock/exception)."""
        import threading

        dispatcher = DisDispatcher()
        errors = []

        def register_many(tid):
            try:
                for i in range(1, 256):
                    dispatcher.register(i, lambda p, t=tid: None)
            except Exception as e:
                errors.append((tid, e))

        threads = [threading.Thread(target=register_many, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, errors
        # All 255 types registered
        assert len(dispatcher.handlers) == 255

    def test_thread_safety_unregister(self):
        """Test unregister is thread-safe."""
        import threading

        dispatcher = DisDispatcher()
        for i in range(1, 256):
            dispatcher.register(i, lambda p: None)

        errors = []

        def unregister_many(tid):
            try:
                for i in range(1, 256):
                    dispatcher.unregister(i)
            except Exception as e:
                errors.append((tid, e))

        threads = [threading.Thread(target=unregister_many, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])