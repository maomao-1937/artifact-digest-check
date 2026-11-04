# artifact-digest-check

[![tests](https://github.com/maomao-1937/artifact-digest-check/actions/workflows/tests.yml/badge.svg)](https://github.com/maomao-1937/artifact-digest-check/actions/workflows/tests.yml)

Check whether a downloaded artifact file matches a known SHA-256 digest. The JSON report contains only the comparison status and the number of bytes read, so a local script can fail on a mismatch without logging filenames or digests.

[简体中文](README.zh-CN.md) · [Research](RESEARCH.md) · [Testing](TESTING.md)

## Run it

Use Python 3.11 or later from this directory. No packages are required.

```sh
python artifact_digest_check.py fixtures/hello.txt sha256:5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03
```

```json
{"status":"match","bytes_read":6}
```

The interface is `python artifact_digest_check.py FILE EXPECTED`. Pass 64 ASCII hex digits, optionally with the exact lowercase `sha256:` prefix. The hex digits may be uppercase or lowercase. Whitespace is rejected. Quote paths that contain spaces and use `--` before a path beginning with a hyphen.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `match` | All bytes read matched the digest. |
| 1 | `mismatch` | All bytes read produced a different digest. |
| 2 | `invalid` | Invalid arguments, unsupported path or file, size limit, or I/O failure. |

`--help` prints usage and exits 0. If stdout closes, the command exits 2 silently, including for help. The byte count is the number actually read, including a single probe byte if the file grows beyond the limit.

## Boundaries

Use the digest for the exact bytes on disk. If the digest describes an archive, point the command at that archive. It treats every file as opaque bytes and does no extraction, ZIP validation, downloading, authentication, or provenance verification. Obtain the expected digest through a trusted channel.

The command opens regular files read-only and accepts empty files and sizes through 1 GiB inclusive. It reads in chunks of at most 1 MiB and rejects URI, UNC and device-style arguments before filesystem access. Absolute Windows drive paths are supported. Symlinks, junctions and mounts are resolved by the OS, so a local-looking path may resolve to remote storage. Check a stable file in a trusted directory if concurrent modification or path replacement is possible.
