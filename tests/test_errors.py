import unittest

from core import JobState
from core.errors import UnknownOperation
from tests.helpers import CrashingTool, make_env


class UnknownOperationAndBadParams(unittest.TestCase):
    def test_unknown_operation_is_error_and_no_job_created(self):
        d, jobs, _ = make_env()
        with self.assertRaises(UnknownOperation) as cm:
            d.submit("translate", {})
        self.assertEqual(cm.exception.code, "UNKNOWN_OPERATION")
        self.assertEqual(jobs.list_all(), [])

    def test_missing_required_field_rejected_with_field(self):
        d, _, _ = make_env()
        job = d.execute("extract_text", {})
        self.assertEqual(job.state, JobState.REJECTED)
        self.assertEqual(job.error["code"], "INVALID_INPUT")
        self.assertEqual(job.error["field"], "fileId")

    def test_wrong_type_rejected_with_field(self):
        d, _, _ = make_env()
        job = d.execute("extract_text", {"fileId": 123})
        self.assertEqual((job.state, job.error["field"]), (JobState.REJECTED, "fileId"))

    def test_unknown_field_rejected_with_field(self):
        d, _, _ = make_env()
        job = d.execute("calculate_statistics", {"textFileId": "a", "extra": 1})
        self.assertEqual((job.state, job.error["field"]), (JobState.REJECTED, "extra"))

    def test_rejected_job_never_runs(self):
        d, _, _ = make_env()
        job = d.execute("extract_text", {})
        from core.errors import InvalidStateTransition
        with self.assertRaises(InvalidStateTransition):
            d.run(job.id)
        self.assertEqual(job.state, JobState.REJECTED)

    def test_business_check_in_tool_fails_job_with_field(self):
        d, _, files = make_env()
        file_id = files.put("a.txt", b"hello")
        job = d.execute("extract_text", {"fileId": file_id, "language": "RU!"})
        self.assertEqual(job.state, JobState.FAILED)
        self.assertEqual((job.error["code"], job.error["field"]), ("INVALID_INPUT", "language"))

    def test_tool_typed_errors_fail_job(self):
        d, _, files = make_env()
        cases = [
            ("extract_text", {"fileId": "nope"}, "FILE_NOT_FOUND"),
            ("extract_text", {"fileId": files.put("a.pdf", b"%PDF")}, "UNSUPPORTED_FORMAT"),
            ("calculate_statistics", {"textFileId": files.put("b.txt", b"\xff\xfe")},
             "INVALID_INPUT"),
            ("convert_format", {"fileId": files.put("c.txt", b"x"), "targetFormat": "exe"},
             "INVALID_INPUT"),
            ("convert_format", {"fileId": files.put("c.txt", b"x"), "targetFormat": "pdf"},
             "UNSUPPORTED_FORMAT"),
        ]
        for op, params, code in cases:
            with self.subTest(op=op, code=code):
                job = d.execute(op, params)
                self.assertEqual((job.state, job.error["code"]), (JobState.FAILED, code))

    def test_deadline_gives_tool_timeout(self):
        d, _, files = make_env(timeout_seconds=0)
        file_id = files.put("a.txt", b"hello")
        job = d.execute("extract_text", {"fileId": file_id})
        self.assertEqual((job.state, job.error["code"]), (JobState.FAILED, "TOOL_TIMEOUT"))

    def test_tool_crash_fails_job_and_hides_details(self):
        from core import build_default_registry
        reg = build_default_registry()
        reg.register(CrashingTool())
        d, _, _ = make_env(reg)
        job = d.execute("crashing", {})
        self.assertEqual((job.state, job.error["code"]), (JobState.FAILED, "TOOL_INTERNAL_ERROR"))
        self.assertNotIn("password", str(job.error))


if __name__ == "__main__":
    unittest.main()
