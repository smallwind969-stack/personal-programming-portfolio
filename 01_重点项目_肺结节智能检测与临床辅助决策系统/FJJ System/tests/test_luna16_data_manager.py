import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from experiments.luna16_data_manager import build_download_request, file_manifest, partial_download_path, validate_download_size


class Luna16DataManagerTests(unittest.TestCase):
    def test_manifest_marks_small_and_large_files(self):
        record = {
            "files": [
                {"key": "annotations.csv", "size": 1, "links": {"self": "url"}, "checksum": "md5:a"},
                {"key": "subset0.zip", "size": 2, "links": {"self": "url"}, "checksum": "md5:b"},
                {"key": "evaluationScript.zip", "size": 3, "links": {"self": "url"}, "checksum": "md5:c"},
            ]
        }

        rows = {row["key"]: row for row in file_manifest(record)}

        self.assertTrue(rows["annotations.csv"]["default_download"])
        self.assertTrue(rows["subset0.zip"]["large_image_subset"])
        self.assertTrue(rows["evaluationScript.zip"]["optional_medium"])

    def test_partial_download_path_keeps_final_file_name_visible(self):
        path = Path("subset1.zip")

        self.assertEqual(partial_download_path(path), Path("subset1.zip.part"))

    def test_build_download_request_uses_range_when_partial_exists(self):
        with TemporaryDirectory() as tmp:
            partial = Path(tmp) / "subset1.zip.part"
            partial.write_bytes(b"abcde")

            request, start = build_download_request("https://example.test/subset1.zip", partial, overwrite=False)

            self.assertEqual(start, 5)
            self.assertEqual(request.headers["Range"], "bytes=5-")

    def test_build_download_request_restarts_when_overwrite(self):
        with TemporaryDirectory() as tmp:
            partial = Path(tmp) / "subset1.zip.part"
            partial.write_bytes(b"abcde")

            request, start = build_download_request("https://example.test/subset1.zip", partial, overwrite=True)

            self.assertEqual(start, 0)
            self.assertNotIn("Range", request.headers)

    def test_validate_download_size_rejects_short_download(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "subset2.zip"
            path.write_bytes(b"short")

            with self.assertRaises(RuntimeError):
                validate_download_size(path, 10)


if __name__ == "__main__":
    unittest.main()
