"""
AFSIM Environment Integration Tests

Verifies that AFSIM 2.9.0 binaries and documentation are properly installed.
"""

from pathlib import Path

import pytest


# AFSIM installation root
AFSIM_ROOT = Path("D:/afsim-2.9.0-win64")


class TestAFSIMEnvironment:
    """Verify AFSIM 2.9.0 installation."""

    def test_afsim_binaries_exist(self):
        """Check that engage.exe and mission.exe exist in the AFSIM bin directory."""
        bin_dir = AFSIM_ROOT / "bin"
        engage = bin_dir / "engage.exe"
        mission = bin_dir / "mission.exe"

        assert engage.exists(), f"engage.exe not found at {engage}"
        assert mission.exists(), f"mission.exe not found at {mission}"

    def test_afsim_documentation_exists(self):
        """Check that the AFSIM HTML documentation directory exists."""
        docs_dir = AFSIM_ROOT / "documentation" / "html"

        assert docs_dir.exists(), f"AFSIM documentation not found at {docs_dir}"
        assert docs_dir.is_dir(), f"documentation/html is not a directory"