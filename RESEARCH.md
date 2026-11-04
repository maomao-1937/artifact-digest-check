# Research

- The upload action documents `artifact-digest` as an output and shows a bare hexadecimal SHA-256 digest. The artifact REST endpoint shows a `digest` field with a `sha256:` prefix. These examples motivate accepting both input forms. [Upload action outputs](https://github.com/actions/upload-artifact#outputs) · [Artifact REST endpoint](https://docs.github.com/en/rest/actions/artifacts#get-an-artifact)
- GitHub documents automatic artifact validation in its download action and a warning on mismatch. A separate local comparison gives an explicit mismatch exit code for a file and expected digest already in hand. [GitHub artifact validation](https://docs.github.com/en/enterprise-cloud@latest/actions/tutorials/store-and-share-data#validating-artifacts)
- An act user reported artifact upload and download failures involving request compatibility. That report concerns transfer, while this project starts with a local file. The upstream issue was read and was not reproduced. [act issue #6114](https://github.com/nektos/act/issues/6114)

## Alternatives

| Tool | Use |
| --- | --- |
| Python `hashlib` | Calculate a digest inside existing Python code. This CLI uses `hashlib.sha256` and adds a path policy, size bound, comparison, and fixed report. |
| GNU `sha256sum` | Compute digests or check checksum manifests when GNU coreutils is available. This CLI takes one digest argument in either documented GitHub form and emits a small JSON report. |
| GitHub's download action | Validate artifacts during the normal Actions download step. This CLI compares already-downloaded bytes in a local script without an Actions runner. |

The examples use a six-byte fixture with a fixed digest. They exercise local byte comparison, without an upload or download.
