"""Regression tests for per-request CORE phase routing."""
import threading
import unittest

from core_phase_context import CorePhaseContext


class TestCorePhaseContext(unittest.TestCase):
    def test_concurrent_requests_keep_their_own_execution_ids(self):
        context = CorePhaseContext()
        barrier = threading.Barrier(2)
        observed = {}
        observed_lock = threading.Lock()

        def request(execution_id):
            with context.bind(execution_id):
                barrier.wait(timeout=2)
                first = context.current_execution_id()
                # Let the other request overlap before reading again.
                second = context.current_execution_id()
                with observed_lock:
                    observed[execution_id] = (first, second)
            self.assertIsNone(context.current_execution_id())

        threads = [
            threading.Thread(target=request, args=(1001,)),
            threading.Thread(target=request, args=(1002,)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=3)
            self.assertFalse(thread.is_alive(), "request thread did not finish")

        self.assertEqual({1001: (1001, 1001), 1002: (1002, 1002)}, observed)

    def test_context_is_cleared_after_early_return_or_exception(self):
        context = CorePhaseContext()
        with self.assertRaisesRegex(RuntimeError, "expected"):
            with context.bind(42):
                self.assertEqual(42, context.current_execution_id())
                raise RuntimeError("expected")
        self.assertIsNone(context.current_execution_id())

    def test_nested_context_restores_previous_execution(self):
        context = CorePhaseContext()
        with context.bind(7):
            with context.bind(8):
                self.assertEqual(8, context.current_execution_id())
            self.assertEqual(7, context.current_execution_id())
        self.assertIsNone(context.current_execution_id())


if __name__ == "__main__":
    unittest.main()
