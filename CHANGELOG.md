# Changelog

## [Unreleased] - Critical Bug Fixes (branch: issue-fixes-of-critical)

### Fixed

- **Temporary File Leak** (`app.py`): Wrapped temporary file handling in a `try/finally` block to ensure temp files are always cleaned up, even when exceptions occur.
- **Remote Code Execution (RCE) Risk** (`src/llm_extractor.py`): Replaced unsafe `eval()` / `exec()` usage with safe JSON parsing (`json.loads`) to prevent arbitrary code execution from untrusted LLM output.
- **Race Condition** (`mitigation_module/dynamic_network.py`): Added thread-safe locking (`threading.Lock`) around shared state access to prevent data corruption under concurrent requests.

---

## Previous Releases

See git log for earlier history.
