"""Tests for the Gwyddion CLI bridge reader (``probeflow.readers.gwy_bridge``)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from probeflow.readers.gwy_bridge import (
    gwyddion_available, gwyddion_convert_to_gwy, gwyddion_identify,
)


def test_availability_matches_path():
    assert gwyddion_available() == (shutil.which("gwyddion") is not None)


@pytest.mark.skipif(not gwyddion_available(),
                    reason="gwyddion binary not installed on this system")
def test_convert_returns_path_or_none(tmp_path):
    """The bridge should either produce a non-empty .gwy file or return None.

    Some Createc-flavoured ``.sxm`` files trip Gwyddion's stricter Nanonis
    parser; we don't depend on success, only on the bridge's graceful
    failure semantics.
    """
    sample = next(Path("data").rglob("*.sxm"), None)
    if sample is None:
        pytest.skip("no .sxm sample in data/")
    out = gwyddion_convert_to_gwy(sample)
    if out is None:
        return  # Gwyddion couldn't read this Createc-style .sxm — that's fine
    assert out.exists() and out.stat().st_size > 0
    out.unlink(missing_ok=True)


@pytest.mark.skipif(not gwyddion_available(),
                    reason="gwyddion binary not installed on this system")
def test_identify_returns_string(tmp_path):
    sample = next(Path("data").rglob("*.sxm"), None)
    if sample is None:
        pytest.skip("no .sxm sample in data/")
    label = gwyddion_identify(sample)
    # Some Gwyddion versions print 'Nanonis SXM data' or 'sxm', etc.
    assert label is None or isinstance(label, str)


def test_missing_file_returns_none(tmp_path):
    bogus = tmp_path / "does_not_exist.xyz"
    assert gwyddion_convert_to_gwy(bogus) is None
    assert gwyddion_identify(bogus) is None
