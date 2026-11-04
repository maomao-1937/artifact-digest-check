"""Compare the bytes in a local file with an expected SHA-256 digest."""

import argparse
import hashlib
import hmac
import json
import os
import re
import stat
import sys


MAX_BYTES = 1024**3
CHUNK_BYTES = 1024**2
EXPECTED = re.compile(r"(?:sha256:)?([a-fA-F0-9]{64})")
RESERVED_DEVICE = re.compile(r"CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|(?:COM|LPT)[1-9¹²³]")


def local_path(path):
    if not path or "\x00" in path:
        return False
    # Check both separator styles regardless of the current platform.
    windows_form = path.replace("/", "\\")
    if windows_form.startswith("\\\\"):
        return False
    if re.match(r"[A-Za-z]:\\", windows_form):
        windows_form = windows_form[3:]
    if ":" in windows_form:
        return False
    for part in windows_form.split("\\"):
        stem = part.partition(".")[0].rstrip(" ").upper()
        if RESERVED_DEVICE.fullmatch(stem):
            return False
    return True


def regular_within_limit(info):
    return stat.S_ISREG(info.st_mode) and 0 <= info.st_size <= MAX_BYTES


def check(path, expected):
    match = EXPECTED.fullmatch(expected)
    if match is None or not local_path(path):
        return 2, "invalid", 0

    count = 0
    hasher = hashlib.sha256()
    try:
        if not regular_within_limit(os.stat(path)):
            return 2, "invalid", 0
        # Nonblocking open on POSIX avoids hanging if a FIFO replaces the file.
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        try:
            if not regular_within_limit(os.fstat(fd)):
                return 2, "invalid", 0
            while chunk := os.read(fd, min(CHUNK_BYTES, MAX_BYTES - count or 1)):
                count += len(chunk)
                if count > MAX_BYTES:
                    return 2, "invalid", count
                hasher.update(chunk)
        finally:
            os.close(fd)
    except (OSError, UnicodeError, ValueError):
        return 2, "invalid", count

    if hmac.compare_digest(hasher.hexdigest(), match.group(1).lower()):
        return 0, "match", count
    return 1, "mismatch", count


class UsageError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError


def main():
    parser = Parser(
        prog="artifact-digest-check",
        description="Compare a local file with an expected SHA-256 digest.",
        allow_abbrev=False,
    )
    parser.add_argument("file", metavar="FILE", help="local regular file up to 1 GiB")
    parser.add_argument("expected", metavar="EXPECTED", help="64 hex digits with optional sha256: prefix")
    try:
        args = parser.parse_args()
        code, status, count = check(args.file, args.expected)
    except UsageError:
        code, status, count = 2, "invalid", 0
    print(json.dumps({"status": status, "bytes_read": count}, separators=(",", ":")), flush=True)
    return code


def run():
    try:
        return main()
    except SystemExit as exit_signal:
        # argparse help writes to stdout before requesting a clean exit.
        sys.stdout.flush()
        return exit_signal.code


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except OSError:
        # Windows may report EINVAL for a closed pipe. Skip the final stdout flush.
        os._exit(2)
