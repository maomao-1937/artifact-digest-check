# Testing

Run the suite from the repository root with Python 3.11.

```sh
python -B -m unittest discover -s tests -v
```

The tests run the CLI against the six-byte fixture and temporary local files. They verify exact report fields and exit codes for match, mismatch, invalid usage and file errors. The suite also verifies early digest and path validation, bounded chunk requests, an inclusive size limit, descriptor rechecking, and a growth probe. Size tests temporarily lower the production limit, so they exercise those branches without reading a GiB.

The closed-pipe regression launches a real child process with no reader on stdout. It tests help and a normal report. `checks.json` lists separate runnable examples and their expected exit codes.

The path compatibility regression makes the removed `PureWindowsPath.is_reserved()` API raise `AttributeError` and exercises both a regular file and reserved names. The suite ran under Python 3.11.15. This regression simulates the API removal documented for Python 3.15.
