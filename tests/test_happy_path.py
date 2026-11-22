import unittest

from core import JobState
from tests.helpers import make_env

TEXT = "Привет, мир. Как дела? Всё хорошо!\n\nВторой абзац."


class HappyPath(unittest.TestCase):
    def test_job_from_creation_to_success(self):
        d, jobs, files = make_env()
        file_id = files.put("note.txt", TEXT.encode("utf-8"))
        job = d.submit("extract_text", {"fileId": file_id})
        self.assertEqual(job.state, JobState.CREATED)
        d.run(job.id)
        self.assertEqual(job.state, JobState.SUCCEEDED)
        self.assertEqual([t for _, t in job.history],
                         [JobState.CREATED, JobState.RUNNING, JobState.SUCCEEDED])
        self.assertEqual(job.result["data"]["characters"], len(TEXT))
        self.assertIsNone(job.error)
        self.assertEqual(files.get(job.result["output_file_id"]).content, TEXT.encode("utf-8"))

    def test_second_tool_statistics(self):
        d, _, files = make_env()
        file_id = files.put("note.txt", TEXT.encode("utf-8"))
        job = d.execute("calculate_statistics", {"textFileId": file_id})
        self.assertEqual(job.state, JobState.SUCCEEDED)
        data = job.result["data"]
        self.assertEqual((data["words"], data["sentences"], data["paragraphs"]), (8, 4, 2))

    def test_third_tool_convert(self):
        d, _, files = make_env()
        file_id = files.put("a.txt", b"one & two\n\nthree")
        job = d.execute("convert_format", {"fileId": file_id, "targetFormat": "html"})
        self.assertEqual(job.state, JobState.SUCCEEDED)
        out = files.get(job.result["output_file_id"])
        self.assertEqual(out.name, "a.html")
        self.assertIn(b"<p>one &amp; two</p>", out.content)

    def test_pipeline_extract_then_statistics(self):
        d, _, files = make_env()
        file_id = files.put("note.md", TEXT.encode("utf-8"))
        first = d.execute("extract_text", {"fileId": file_id})
        second = d.execute("calculate_statistics",
                           {"textFileId": first.result["output_file_id"]})
        self.assertEqual(second.state, JobState.SUCCEEDED)


if __name__ == "__main__":
    unittest.main()
