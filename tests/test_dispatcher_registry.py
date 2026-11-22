import unittest

from core import JobState, Registry
from tests.helpers import CountingTool, MutatingTool, make_env


class RegistryTests(unittest.TestCase):
    def test_get_by_name_and_duplicate(self):
        reg = Registry()
        tool = CountingTool()
        reg.register(tool)
        self.assertIs(reg.get("counting"), tool)
        with self.assertRaises(ValueError):
            reg.register(CountingTool())


class DispatcherIsToolAgnostic(unittest.TestCase):
    def test_new_tool_works_without_dispatcher_changes(self):
        reg = Registry()
        tool = CountingTool()
        reg.register(tool)  # единственное действие для подключения Tool
        d, _, _ = make_env(reg)
        job = d.execute("counting", {})
        self.assertEqual((job.state, tool.calls), (JobState.SUCCEEDED, 1))

    def test_tool_cannot_mutate_stored_job_params(self):
        reg = Registry()
        reg.register(MutatingTool())
        d, _, _ = make_env(reg)
        job = d.execute("mutating", {})
        self.assertEqual(job.params, {})

    def test_idempotency_key_returns_same_job(self):
        reg = Registry()
        tool = CountingTool()
        reg.register(tool)
        d, _, _ = make_env(reg)
        a = d.execute("counting", {}, idempotency_key="k1")
        b = d.execute("counting", {}, idempotency_key="k1")
        self.assertIs(a, b)
        self.assertEqual(tool.calls, 1)

    def test_idempotency_key_with_other_params_conflicts(self):
        from core.errors import IdempotencyConflict
        d, _, files = make_env()
        f = files.put("a.txt", b"x")
        d.submit("extract_text", {"fileId": f}, idempotency_key="k")
        with self.assertRaises(IdempotencyConflict):
            d.submit("extract_text", {"fileId": "other"}, idempotency_key="k")


if __name__ == "__main__":
    unittest.main()
