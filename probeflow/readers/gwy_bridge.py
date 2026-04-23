"""Last-resort reader: shell out to the system Gwyddion binary to convert
unknown vendor formats into a temporary ``.gwy`` file, which we can then read
with the in-process Gwyddion reader.

Gwyddion knows ~40 SPM file formats out of the box (Bruker, Park, NTEGRA,
Nanoscope, JPK, Park Pro, …). Using its ``--convert-to-gwy`` mode means
ProbeFlow inherits all of them with no extra Python dependency, provided the
user has Gwyddion installed.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def gwyddion_available() -> bool:
    """True iff a callable ``gwyddion`` binary is on PATH."""
    return shutil.which("gwyddion") is not None


def gwyddion_convert_to_gwy(in_path) -> Optional[Path]:
    """Convert ``in_path`` to a temporary ``.gwy`` file via Gwyddion.

    Returns the path to the generated ``.gwy`` (caller is responsible for
    deleting it if desired — placed under :func:`tempfile.gettempdir`), or
    ``None`` if Gwyddion is not installed or refuses the file.
    """
    in_path = Path(in_path)
    if not gwyddion_available():
        return None
    if not in_path.is_file():
        return None

    out = Path(tempfile.gettempdir()) / f"probeflow_bridge_{in_path.stem}.gwy"
    try:
        proc = subprocess.run(
            ["gwyddion", "--convert-to-gwy=" + str(out), str(in_path)],
            capture_output=True, text=True, timeout=60,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
        return None
    return out


def gwyddion_identify(in_path) -> Optional[str]:
    """Return Gwyddion's one-line description of ``in_path``'s SPM type.

    Useful for the ``info`` subcommand when the file's suffix doesn't match
    any built-in reader. Returns ``None`` if Gwyddion is unavailable or the
    file is unidentified.
    """
    in_path = Path(in_path)
    if not gwyddion_available() or not in_path.is_file():
        return None
    try:
        proc = subprocess.run(
            ["gwyddion", "--identify", str(in_path)],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    out = (proc.stdout or "").strip()
    return out or None
