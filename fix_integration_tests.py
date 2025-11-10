#!/usr/bin/env python3
"""Add test_settings parameter to integration test functions that use AuthService."""

import re
import sys
from pathlib import Path


def fix_file(filepath):
    """Fix a single Python test file."""
    with open(filepath, "r") as f:
        content = f.read()

    original = content

    # Find functions that use AuthService but don't have test_settings
    pattern = r"(async def test_\w+\([^)]*db_session: AsyncSession[^)]*)\)"

    def add_settings_if_needed(match):
        func_sig = match.group(1)
        # Check if test_settings is already present
        if "test_settings" in func_sig:
            return match.group(0)  # Already has it
        # Check if AuthService is used in this function
        # We'll add it to be safe for all db_session functions
        return func_sig + ", test_settings)"

    # First pass: add test_settings to functions with db_session
    content = re.sub(pattern, add_settings_if_needed, content)

    if content != original:
        with open(filepath, "w") as f:
            f.write(content)
        print(f"Fixed: {filepath}")
        return True
    return False


def main():
    integration_dir = Path("tests/integration")
    if not integration_dir.exists():
        print("tests/integration directory not found")
        sys.exit(1)

    fixed_count = 0
    for py_file in integration_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        if fix_file(py_file):
            fixed_count += 1

    print(f"\nFixed {fixed_count} files")


if __name__ == "__main__":
    main()
