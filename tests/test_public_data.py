# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from public_data import load_notices_file, validate_notices, to_db_records


class PublicNoticesTest(unittest.TestCase):
    def test_notices_json_valid_and_deduped(self):
        data = load_notices_file()
        errors = validate_notices(data)
        self.assertEqual(errors, [], msg="\n".join(errors))
        self.assertTrue(data.get("updated_at"))
        self.assertGreaterEqual(len(data["notices"]), 8)

    def test_records_have_source_urls(self):
        records = to_db_records()
        urls = [r["source_url"] for r in records]
        self.assertEqual(len(urls), len(set(urls)))
        for r in records:
            self.assertTrue(r["source_url"].startswith("http"))
            self.assertTrue(r["title"])
            self.assertRegex(r["publish_date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_no_placeholder_fake_titles(self):
        records = to_db_records()
        for r in records:
            self.assertNotIn("{region}", r["title"])
            self.assertFalse(r["source_url"].endswith(".jhtml") and "gzggzy.cn" in r["source_url"] and "9999999" in r["source_url"])


if __name__ == "__main__":
    unittest.main()
