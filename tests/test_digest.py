import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


CLI = Path(__file__).resolve().parents[1] / "artifact_digest_check.py"
FIXTURE = CLI.parent / "fixtures" / "hello.txt"
HELLO = "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03"
EMPTY = hashlib.sha256(b"").hexdigest()


class DigestTests(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            capture_output=True, text=True, timeout=10,
        )

    def assert_report(self, result, code, status, count):
        self.assertEqual(result.returncode, code, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), {"status": status, "bytes_read": count})

    def test_known_file_and_uppercase_prefixed_digest(self):
        self.assert_report(self.cli(FIXTURE, "sha256:" + HELLO.upper()), 0, "match", 6)

    def test_path_guard_without_removed_pathlib_method(self):
        import artifact_digest_check as digest

        with patch.object(PureWindowsPath, "is_reserved", create=True,
                          side_effect=AttributeError("is_reserved was removed")):
            self.assertEqual(digest.check(str(FIXTURE), HELLO), (0, "match", 6))
            self.assertFalse(digest.local_path("folder/COM¹ .txt"))
            self.assertFalse(digest.local_path("NUL.txt"))

    def test_mismatch_reports_only_status_and_count(self):
        self.assert_report(self.cli(FIXTURE, EMPTY), 1, "mismatch", 6)

    def test_empty_file_matches(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "empty"
            path.touch()
            self.assert_report(self.cli(path, EMPTY), 0, "match", 0)

    def test_missing_file_and_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            for path in (Path(folder) / "private-value", folder):
                self.assert_report(self.cli(path, EMPTY), 2, "invalid", 0)

    def test_bad_digest_precedes_filesystem_access(self):
        import artifact_digest_check as digest

        invalid = (" " + HELLO, HELLO + "\n", "SHA256:" + HELLO, "Ａ" * 64, "f" * 63)
        with patch.object(digest.os, "stat", side_effect=AssertionError("unexpected stat")):
            with patch.object(digest.os, "open", side_effect=AssertionError("unexpected open")):
                for expected in invalid:
                    self.assertEqual(digest.check("private-value", expected), (2, "invalid", 0))

    def test_nonlocal_or_device_paths_precede_filesystem_access(self):
        import artifact_digest_check as digest

        unsafe = (
            "https://example.test/a", "file:///a", r"\\server\share\a",
            "//server/share/a", r"/\server\share\a", r"\\?\C:\a", r"\\.\NUL",
            "C:relative", "name:stream", "NUL.txt", "sub/COM1", "CONIN$",
            "x\x00y", "",
        )
        with patch.object(digest.os, "stat", side_effect=AssertionError("unexpected stat")):
            with patch.object(digest.os, "open", side_effect=AssertionError("unexpected open")):
                for path in unsafe:
                    with self.subTest(path=path):
                        self.assertEqual(digest.check(path, EMPTY), (2, "invalid", 0))
        self.assertTrue(digest.local_path(r"C:\path\file.zip"))

    def test_inclusive_cap_and_chunk_boundary(self):
        import artifact_digest_check as digest

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "local"
            data = b"abcdefghij"
            path.write_bytes(data)
            with patch.object(digest, "MAX_BYTES", len(data)), patch.object(digest, "CHUNK_BYTES", 3):
                with patch.object(digest.os, "read", wraps=os.read) as read:
                    self.assertEqual(digest.check(str(path), hashlib.sha256(data).hexdigest()), (0, "match", 10))
                    self.assertTrue(all(0 < call.args[1] <= 3 for call in read.call_args_list))
                path.write_bytes(data + b"x")
                with patch.object(digest.os, "open", side_effect=AssertionError("oversize opened")):
                    self.assertEqual(digest.check(str(path), EMPTY), (2, "invalid", 0))

    def test_descriptor_checked_after_open(self):
        import artifact_digest_check as digest

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "local"
            path.touch()
            other = Path(folder) / "larger"
            other.write_bytes(b"12345")
            open_file = os.open
            with patch.object(digest, "MAX_BYTES", 4):
                with patch.object(digest.os, "open", side_effect=lambda _, flags: open_file(other, flags)):
                    self.assertEqual(digest.check(str(path), EMPTY), (2, "invalid", 0))

    def test_file_growth_cannot_exceed_cap_by_more_than_one_probe_byte(self):
        import artifact_digest_check as digest

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "local"
            path.write_bytes(b"1234")
            read_file = os.read

            def grow_then_read(fd, size):
                with path.open("ab") as stream:
                    stream.write(b"5678")
                return read_file(fd, size)

            with patch.object(digest, "MAX_BYTES", 4):
                with patch.object(digest.os, "read", side_effect=grow_then_read) as read:
                    self.assertEqual(digest.check(str(path), EMPTY), (2, "invalid", 5))
                    self.assertEqual([call.args[1] for call in read.call_args_list], [4, 1])

    def test_usage_errors_do_not_echo_input(self):
        self.assert_report(self.cli("--private-option"), 2, "invalid", 0)

    def test_closed_stdout_for_report_and_help(self):
        for args in (("--help",), (str(FIXTURE), HELLO)):
            with self.subTest(args=args):
                reader, writer = os.pipe()
                os.close(reader)
                try:
                    result = subprocess.run(
                        [sys.executable, str(CLI), *args], stdout=writer,
                        stderr=subprocess.PIPE, text=True, timeout=10,
                    )
                finally:
                    os.close(writer)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
