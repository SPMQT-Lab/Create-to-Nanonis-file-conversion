"""
Vendor-specific readers that produce :class:`probeflow.scan.Scan` objects.

Each submodule exposes a single ``read_<format>(path) -> Scan`` entry point.
The unified dispatcher is :func:`probeflow.scan.load_scan`.

Supported scan readers: ``.sxm`` (Nanonis), ``.dat`` (Createc topography).
Spectroscopy readers (Nanonis ``.dat``, Createc ``.VERT``) live in
:mod:`probeflow.spec_io`.
"""

from probeflow.readers.sxm import read_sxm
from probeflow.readers.dat import read_dat

__all__ = ["read_sxm", "read_dat"]
