#!/usr/bin/env python3
"""Fix all test API keys to use valid base64 format."""

from pathlib import Path

# Valid test keys (base64 encoded, 32 chars)
VALID_TEST_KEY = "vj_test_c0U6nxxUVPWjjw+c0yIqEsCwFuJ6H2wB"  # pragma: allowlist secret
VALID_LIVE_KEY = "vj_live_ggqT0GSEN6qrtVYph6hi5r0oPzxKvrI0"  # pragma: allowlist secret

# Invalid patterns to replace
INVALID_PATTERNS = [
    r"vj_test_abc123def456ghi789jkl012mno34pqr",  # pragma: allowlist secret
    r"vj_test_ABC123DEF456GHI789JKL012MNO34PQR",  # pragma: allowlist secret
    r"vj_test_abcdefghijklmnopqrstuvwxyz1234",  # pragma: allowlist secret
    r"vj_test_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234AB",  # pragma: allowlist secret
    r"vj_live_abc123def456ghi789jkl012mno34pqr",  # pragma: allowlist secret
    r"vj_live_ABC123DEF456GHI789JKL012MNO34PQR",  # pragma: allowlist secret
    r"vj_live_abcdefghijklmnopqrstuvwxyz1234ab",  # pragma: allowlist secret
    r"vj_live_abcdefghijklmnopqrstuvwxyz123456",  # pragma: allowlist secret
]


def fix_file(filepath: Path) -> int:
    """Fix API keys in a single file. Returns number of replacements."""
    content = filepath.read_text()
    original = content
    replacements = 0

    for pattern in INVALID_PATTERNS:
        replacement = VALID_TEST_KEY if pattern.startswith("vj_test") else VALID_LIVE_KEY
        new_content = content.replace(pattern, replacement)
        if new_content != content:
            count = content.count(pattern)
            replacements += count
            print(f"  {filepath.name}: Replaced {count} occurrences of {pattern}")
            content = new_content

    if content != original:
        filepath.write_text(content)

    return replacements


def main():
    """Fix all test files."""
    test_dir = Path("tests")
    total_replacements = 0
    files_modified = 0

    for test_file in test_dir.rglob("*.py"):
        replacements = fix_file(test_file)
        if replacements > 0:
            total_replacements += replacements
            files_modified += 1

    print(f"\nTotal: {total_replacements} replacements in {files_modified} files")
    print(f"Valid test key: {VALID_TEST_KEY}")
    print(f"Valid live key: {VALID_LIVE_KEY}")


if __name__ == "__main__":
    main()
