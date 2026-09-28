import json
import unittest

import handler


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[Key] = Body


class ReportsTest(unittest.TestCase):
    def setUp(self):
        handler._s3 = FakeS3()

    def test_writes_report_for_date(self):
        out = handler.lambda_handler({"date": "2026-01-02"}, None)
        self.assertEqual(out["key"], "reports/2026-01-02.json")
        report = json.loads(handler._s3.objects["reports/2026-01-02.json"])
        self.assertEqual(report["revenue"], 3723.75)
        self.assertEqual(report["stores"], 3)

    def test_scheduled_event_uses_today(self):
        out = handler.lambda_handler({"source": "aws.events"}, None)
        self.assertTrue(out["key"].startswith("reports/20"))

    def test_simulated_failure(self):
        with self.assertRaises(RuntimeError):
            handler.lambda_handler({"simulate_failure": True}, None)


if __name__ == "__main__":
    unittest.main()
