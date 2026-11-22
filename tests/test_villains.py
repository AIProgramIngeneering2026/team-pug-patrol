"""Злодейства З1–З6 с пары «Взлом Job». Каждое — отдельный тест(ы); ядро должно отклонять."""
import itertools
import threading
import unittest

from core import ALLOWED_TRANSITIONS, JobState, Registry
from core.errors import InvalidStateTransition, OperationNotSupported
from tests.helpers import CountingTool, job_in_state, make_env


class Z1_DoubleWork(unittest.TestCase):
    """З1: в одном Job одновременно работают два Tool."""

    def test_second_start_of_running_job_is_rejected(self):
        job = job_in_state(JobState.RUNNING)
        with self.assertRaises(InvalidStateTransition):
            job.start()
        self.assertEqual(job.state, JobState.RUNNING)

    def test_parallel_runs_execute_tool_once(self):
        reg = Registry()
        tool = CountingTool(delay=0.05)
        reg.register(tool)
        d, _, _ = make_env(reg)
        job = d.submit("counting", {})
        outcomes = []

        def attempt():
            try:
                d.run(job.id)
                outcomes.append("ran")
            except InvalidStateTransition:
                outcomes.append("rejected")

        threads = [threading.Thread(target=attempt) for _ in range(8)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(tool.calls, 1)
        self.assertEqual(outcomes.count("ran"), 1)
        self.assertEqual(outcomes.count("rejected"), 7)

    def test_parallel_submits_with_same_key_create_one_job(self):
        reg = Registry()
        reg.register(CountingTool())
        d, jobs, _ = make_env(reg)
        threads = [threading.Thread(target=lambda: d.submit("counting", {}, "same-key"))
                   for _ in range(8)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(len(jobs.list_all()), 1)


class Z2_EternalWork(unittest.TestCase):
    """З2: сервер перезапустился, Job остался в running."""

    def test_recovery_moves_interrupted_job_to_failed(self):
        d, jobs, _ = make_env()
        stuck = d.submit("extract_text", {"fileId": "x"})
        stuck.start()  # «упали» посреди выполнения
        fresh = d.submit("extract_text", {"fileId": "y"})  # created — не трогаем
        done = job_in_state(JobState.SUCCEEDED)
        jobs.get_or_create(None, lambda: done)
        recovered = d.recover_interrupted()
        self.assertEqual([j.id for j in recovered], [stuck.id])
        self.assertEqual((stuck.state, stuck.error["code"]),
                         (JobState.FAILED, "SERVICE_RESTARTED"))
        self.assertEqual(fresh.state, JobState.CREATED)
        self.assertEqual(done.state, JobState.SUCCEEDED)

    def test_recovery_is_idempotent(self):
        d, _, _ = make_env()
        d.submit("extract_text", {"fileId": "x"}).start()
        self.assertEqual(len(d.recover_interrupted()), 1)
        self.assertEqual(d.recover_interrupted(), [])


class Z3_Cancel(unittest.TestCase):
    """З3: отменили, а потом стал готовым. Отмены нет — отменённого состояния нет."""

    def test_cancel_not_supported_and_state_unchanged(self):
        d, _, _ = make_env()
        for state in (JobState.CREATED, JobState.RUNNING):
            with self.subTest(state=state):
                job = job_in_state(state)
                with self.assertRaises(OperationNotSupported) as cm:
                    job.cancel()
                self.assertEqual(cm.exception.code, "OPERATION_NOT_SUPPORTED")
                self.assertEqual(job.state, state)

    def test_dispatcher_cancel_not_supported(self):
        d, _, _ = make_env()
        job = d.submit("extract_text", {"fileId": "x"})
        with self.assertRaises(OperationNotSupported):
            d.cancel(job.id)
        self.assertEqual(job.state, JobState.CREATED)

    def test_no_cancelled_state_exists(self):
        self.assertEqual({s.value for s in JobState},
                         {"created", "running", "succeeded", "failed", "rejected"})


class Z4_TwoOutcomes(unittest.TestCase):
    """З4: был в ошибке, потом стал готовым."""

    def test_failed_cannot_become_succeeded(self):
        job = job_in_state(JobState.FAILED)
        with self.assertRaises(InvalidStateTransition):
            job.succeed({"data": {}})
        self.assertEqual((job.state, job.result), (JobState.FAILED, None))

    def test_succeeded_cannot_become_failed(self):
        job = job_in_state(JobState.SUCCEEDED)
        with self.assertRaises(InvalidStateTransition):
            job.fail({"code": "X", "message": "m"})
        self.assertEqual((job.state, job.error), (JobState.SUCCEEDED, None))

    def test_failed_job_is_not_retried_by_dispatcher(self):
        d, _, _ = make_env()
        job = d.execute("extract_text", {"fileId": "missing"})
        self.assertEqual(job.state, JobState.FAILED)
        with self.assertRaises(InvalidStateTransition):
            d.run(job.id)
        self.assertEqual(job.state, JobState.FAILED)


class Z5_SuccessWithoutWork(unittest.TestCase):
    """З5: стал succeeded, не побывав в running."""

    def test_created_cannot_succeed_directly(self):
        job = job_in_state(JobState.CREATED)
        with self.assertRaises(InvalidStateTransition):
            job.succeed({"data": {}})
        self.assertEqual((job.state, job.result), (JobState.CREATED, None))

    def test_every_success_passes_through_running(self):
        d, _, files = make_env()
        job = d.execute("extract_text", {"fileId": files.put("a.txt", b"hi")})
        states = [t for _, t in job.history]
        self.assertLess(states.index(JobState.RUNNING), states.index(JobState.SUCCEEDED))


class Z6_RepeatOfSuccess(unittest.TestCase):
    """З6: готовый Job снова пошёл в работу (SMS ушло второй раз)."""

    def test_succeeded_cannot_start_again(self):
        job = job_in_state(JobState.SUCCEEDED)
        with self.assertRaises(InvalidStateTransition) as cm:
            job.start()
        self.assertEqual(cm.exception.http_status, 409)
        self.assertEqual(job.state, JobState.SUCCEEDED)

    def test_rerun_and_resubmit_do_not_execute_tool_again(self):
        reg = Registry()
        tool = CountingTool()
        reg.register(tool)
        d, _, _ = make_env(reg)
        job = d.execute("counting", {}, idempotency_key="sms-1")
        with self.assertRaises(InvalidStateTransition):
            d.run(job.id)
        d.execute("counting", {}, idempotency_key="sms-1")
        self.assertEqual(tool.calls, 1)


class ForbiddenTransitionsExhaustive(unittest.TestCase):
    """Все пары состояний: запрещённая пара -> явная ошибка, состояние не меняется."""

    def test_all_forbidden_pairs(self):
        for src, dst in itertools.product(JobState, JobState):
            if dst in ALLOWED_TRANSITIONS[src]:
                continue
            with self.subTest(src=src.value, dst=dst.value):
                job = job_in_state(src)
                before = job.history
                with self.assertRaises(InvalidStateTransition):
                    job.transition_to(dst, result={}, error={})
                self.assertEqual((job.state, job.history), (src, before))

    def test_allowed_pairs_exactly_as_diagram(self):
        allowed = {(s.value, t.value) for s, ts in ALLOWED_TRANSITIONS.items() for t in ts}
        self.assertEqual(allowed, {("created", "running"), ("created", "rejected"),
                                   ("running", "succeeded"), ("running", "failed")})

    def test_state_cannot_be_assigned_from_outside(self):
        job = job_in_state(JobState.CREATED)
        with self.assertRaises(AttributeError):
            job.state = JobState.SUCCEEDED


if __name__ == "__main__":
    unittest.main()
