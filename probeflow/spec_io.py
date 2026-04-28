"""Reader for Createc vertical-spectroscopy (.VERT) files."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union

import numpy as np

from .common import _f, find_hdr
from .readers.createc_vert import (
    CreatecVertDecodeReport,
    detect_createc_vert_time_trace,
    parse_createc_vert_header,
    read_createc_vert_report,
)

log = logging.getLogger(__name__)

# Voltage range below this threshold (mV) → file is a time trace, not a bias sweep.
# Configurable via read_spec_file(time_trace_threshold_mv=...) for unusual sweeps.
_TIME_TRACE_THRESHOLD_MV = 1.0


@dataclass
class SpecData:
    """All data and metadata from one Createc .VERT spectroscopy file.

    Parameters
    ----------
    header : dict[str, str]
        Raw header key-value pairs from the file.
    channels : dict[str, np.ndarray]
        Named data channels. Known channels are converted to SI units:
        'I' (A), 'Z' (m), 'V' (V). Unknown decoded channels are preserved
        in raw numeric units with conservative unit labels.
        For bias sweeps, channels['V'] equals x_array and is redundant;
        for time traces it holds the (near-constant) measurement bias.
    x_array : np.ndarray
        Independent variable in SI units (time in s or bias in V).
    x_label : str
        Human-readable axis label, e.g. 'Bias (V)' or 'Time (s)'.
    x_unit : str
        Unit string, e.g. 'V', 's'.
    y_units : dict[str, str]
        Unit string for each channel, e.g. {'I': 'A', 'Z': 'm'}.
    position : tuple[float, float]
        (x_m, y_m) tip position in physical coordinates (metres).
    metadata : dict[str, Any]
        Scan parameters: sweep_type, bias, frequency, title, etc.
    """

    header: dict[str, str]
    channels: dict[str, np.ndarray]
    x_array: np.ndarray
    x_label: str
    x_unit: str
    y_units: dict[str, str]
    position: tuple[float, float]
    metadata: dict[str, Any]
    # Ordered list of all channel names as they should appear in the UI.
    # Defaults to empty for backwards compatibility with old constructors.
    channel_order: list[str] = field(default_factory=list)
    # Subset of ``channel_order`` to preselect when a viewer first opens.
    default_channels: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        n = self.metadata.get("n_points", "?")
        sw = self.metadata.get("sweep_type", "unknown")
        fname = self.metadata.get("filename", "")
        return f"SpecData({fname!r}, {sw}, {n} pts)"


@dataclass(frozen=True)
class SpecMetadata:
    """Lightweight spectroscopy summary for folder indexing.

    Unlike :class:`SpecData`, this object never contains full numeric channel
    arrays. Readers may stream file rows to count points, but should not build
    array payloads just to populate folder-browser metadata.
    """

    path: Path
    source_format: str
    channels: tuple[str, ...]
    units: tuple[str, ...]
    position: tuple[float, float]
    metadata: dict[str, Any]
    bias: float | None = None
    comment: str | None = None
    acquisition_datetime: str | None = None
    raw_header: dict[str, str] = field(default_factory=dict)


def parse_spec_header(path: Union[str, Path]) -> dict[str, str]:
    """Read only the header of a .VERT file and return it as a dictionary.

    Reads in 64 KB chunks and stops as soon as the DATA marker is found,
    so large spectroscopy files are not loaded entirely into memory.

    Parameters
    ----------
    path : str or Path
        Path to a Createc .VERT file.

    Returns
    -------
    dict[str, str]
        Key-value pairs from the file header.
    """
    return parse_createc_vert_header(path)


def read_spec_file(
    path: Union[str, Path],
    *,
    time_trace_threshold_mv: float = _TIME_TRACE_THRESHOLD_MV,
) -> SpecData:
    """Read a spectroscopy file (Createc .VERT or Nanonis .dat) into SpecData.

    The file type is identified from its content signature, so callers can
    pass either vendor format without worrying about extensions.
    """
    from probeflow.loaders import identify_spectrum_file

    sig = identify_spectrum_file(path)
    if sig.source_format == "nanonis_dat_spectrum":
        from probeflow.readers.nanonis_spec import read_nanonis_spec
        return read_nanonis_spec(sig.path)
    return _read_createc_vert(sig.path, time_trace_threshold_mv=time_trace_threshold_mv)


def read_spec_metadata(
    path: Union[str, Path],
    *,
    time_trace_threshold_mv: float = _TIME_TRACE_THRESHOLD_MV,
) -> SpecMetadata:
    """Read spectroscopy metadata without loading full numeric arrays."""
    from probeflow.loaders import identify_spectrum_file

    sig = identify_spectrum_file(path)
    if sig.source_format == "nanonis_dat_spectrum":
        from probeflow.readers.nanonis_spec import read_nanonis_spec_metadata
        return read_nanonis_spec_metadata(sig.path)
    return _read_createc_vert_metadata(
        sig.path,
        time_trace_threshold_mv=time_trace_threshold_mv,
    )


def _read_createc_vert_metadata(
    path: Path,
    *,
    time_trace_threshold_mv: float = _TIME_TRACE_THRESHOLD_MV,
) -> SpecMetadata:
    """Read Createc .VERT metadata without materialising channel arrays."""
    report = read_createc_vert_report(path, include_arrays=False)
    metadata, bias, comment, position, order, units = _metadata_from_vert_report(
        report,
        time_trace_threshold_mv=time_trace_threshold_mv,
    )
    return SpecMetadata(
        path=path,
        source_format="createc_vert",
        channels=tuple(order),
        units=tuple(units[ch] for ch in order),
        position=position,
        metadata=metadata,
        bias=bias,
        comment=comment,
        acquisition_datetime=None,
        raw_header=report.header,
    )


def _metadata_from_vert_report(
    report: CreatecVertDecodeReport,
    *,
    time_trace_threshold_mv: float,
) -> tuple[
    dict[str, Any],
    float | None,
    str | None,
    tuple[float, float],
    list[str],
    dict[str, str],
]:
    """Return public metadata fields derived from a Createc VERT report."""

    hdr = report.header
    if report.raw_columns and "V" in report.raw_columns:
        bias_for_type = np.asarray(report.raw_columns["V"], dtype=np.float64)
    elif report.bias_min_mv is not None and report.bias_max_mv is not None:
        bias_for_type = np.array(
            [report.bias_min_mv, report.bias_max_mv],
            dtype=np.float64,
        )
    else:
        bias_for_type = np.array([], dtype=np.float64)

    is_time_trace = detect_createc_vert_time_trace(
        hdr,
        bias_for_type,
        time_trace_threshold_mv,
    )

    bias_raw = find_hdr(hdr, "BiasVolt.[mV]", None) or find_hdr(
        hdr,
        "Biasvolt[mV]",
        None,
    )
    bias_mv = _f(bias_raw)
    comment = hdr.get("Titel", "").strip() or None
    order = _public_channel_order(report)
    units = {
        info.canonical_name: info.unit
        for info in report.channel_info
        if info.canonical_name in order
    }

    metadata: dict[str, Any] = {
        "filename": report.path.name,
        "bias_mv": float(bias_mv) if bias_mv is not None else None,
        "spec_freq_hz": _f(find_hdr(hdr, "SpecFreq", "1000"), 1000.0),
        "gain_pre_exp": float(_f(find_hdr(hdr, "GainPre 10^", "9"), 9.0)),
        "fb_log": hdr.get("FBLog", "0").strip() == "1",
        "sweep_type": "time_trace" if is_time_trace else "bias_sweep",
        "n_points": report.raw_table_shape[0],
        "title": comment or "",
        "source": dict(report.source),
        "createc_vert": {
            "file_version": report.file_version,
            "params_line": report.params_line,
            "spec_total_points": report.spec_total_points,
            "spec_position_dac": [report.spec_pos_x, report.spec_pos_y],
            "channel_code": report.channel_code,
            "output_channel_count_marker": report.output_channel_count_marker,
            "column_names": list(report.column_names),
            "warnings": list(report.warnings),
        },
    }

    return (
        metadata,
        (bias_mv / 1000.0) if bias_mv is not None else None,
        comment,
        _position_from_createc_header(hdr),
        order,
        units,
    )


def _scaled_channels_from_vert_report(
    report: CreatecVertDecodeReport,
) -> tuple[dict[str, np.ndarray], dict[str, str]]:
    if report.raw_columns is None:
        raise ValueError("VERT report does not include raw numeric arrays")

    channels: dict[str, np.ndarray] = {}
    y_units: dict[str, str] = {}
    for info in report.channel_info:
        raw = report.raw_columns.get(info.raw_name)
        if raw is None:
            continue
        channels[info.canonical_name] = np.asarray(
            raw * info.scale_factor,
            dtype=np.float64,
        )
        y_units[info.canonical_name] = info.unit
    return channels, y_units


def _public_channel_order(report: CreatecVertDecodeReport) -> list[str]:
    decoded = [info.canonical_name for info in report.channel_info]
    preferred = [name for name in ("I", "Z", "V") if name in decoded]
    rest = [name for name in decoded if name not in preferred]
    return preferred + rest


def _default_spec_channels(channel_order: list[str]) -> list[str]:
    if "I" in channel_order:
        return ["I"]
    current_like = [ch for ch in channel_order if "current" in ch.lower()]
    if current_like:
        return [current_like[0]]
    return channel_order[:1]


def _position_from_createc_header(hdr: dict[str, str]) -> tuple[float, float]:
    dac_to_a_xy = _f(find_hdr(hdr, "Dacto[A]xy", "1"), 1.0)
    ox_dac = _f(find_hdr(hdr, "OffsetX", "0"), 0.0)
    oy_dac = _f(find_hdr(hdr, "OffsetY", "0"), 0.0)
    return (ox_dac * dac_to_a_xy * 1e-10, oy_dac * dac_to_a_xy * 1e-10)


def _read_createc_vert(
    path: Path,
    *,
    time_trace_threshold_mv: float = _TIME_TRACE_THRESHOLD_MV,
) -> SpecData:
    """Read a Createc .VERT spectroscopy file and return a SpecData object.

    The data is converted to SI units on read. The sweep type (bias sweep vs
    time trace) is detected from the Vpoint header entries first, falling back
    to checking the voltage range in the data column.
    """
    report = read_createc_vert_report(path, include_arrays=True)
    if report.raw_columns is None:
        raise ValueError(f"{path.name}: internal VERT report has no numeric arrays")

    channels, y_units = _scaled_channels_from_vert_report(report)
    metadata, _bias, _comment, position, channel_order, _units = (
        _metadata_from_vert_report(
            report,
            time_trace_threshold_mv=time_trace_threshold_mv,
        )
    )

    idx = report.raw_columns.get("idx")
    if idx is None:
        raise ValueError(f"{path.name}: missing idx column in VERT data")
    spec_freq = metadata["spec_freq_hz"]
    if metadata["sweep_type"] == "time_trace":
        x_array = idx / spec_freq  # sample index / Hz → seconds
        x_label = "Time (s)"
        x_unit = "s"
    else:
        x_array = channels["V"]
        x_label = "Bias (V)"
        x_unit = "V"

    log.info(
        "%s: %s, %d pts, pos=(%.3g, %.3g) m",
        path.name,
        metadata["sweep_type"],
        metadata["n_points"],
        position[0],
        position[1],
    )

    return SpecData(
        header=report.header,
        channels=channels,
        x_array=x_array,
        x_label=x_label,
        x_unit=x_unit,
        y_units=y_units,
        position=position,
        metadata=metadata,
        channel_order=channel_order,
        default_channels=_default_spec_channels(channel_order),
    )
