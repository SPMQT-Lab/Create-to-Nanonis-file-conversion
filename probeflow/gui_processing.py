"""Bridge between GUI processing-state dict and the canonical ProcessingState.

No Qt imports — this module can be tested without a running Qt event loop.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from probeflow.scan import Scan

# Keys in the GUI processing state dict that correspond to numeric data
# transforms (as opposed to display-only settings like grain overlays,
# colourmap, or clip percentiles).
NUMERIC_PROC_KEYS: tuple[str, ...] = (
    "remove_bad_lines",
    "align_rows",
    "bg_order",
    "facet_level",
    "smooth_sigma",
    "edge_method",
    "fft_mode",
)


def processing_state_from_gui(gui_state: dict) -> "ProcessingState":
    """Convert a GUI processing dict into a canonical :class:`ProcessingState`.

    The GUI dict uses keys such as ``"remove_bad_lines"``, ``"bg_order"``, etc.
    Display-only keys (``colormap``, ``clip_low``, ``clip_high``,
    ``grain_threshold``, ``grain_above``) are silently ignored.

    Operation order matches the existing GUI application order.
    """
    from probeflow.processing_state import ProcessingState, ProcessingStep

    steps = []

    if gui_state.get("remove_bad_lines"):
        steps.append(ProcessingStep("remove_bad_lines", {"threshold_mad": 5.0}))

    align = gui_state.get("align_rows")
    if align:
        steps.append(ProcessingStep("align_rows", {"method": str(align)}))

    bg_order = gui_state.get("bg_order")
    if bg_order is not None:
        steps.append(ProcessingStep("plane_bg", {"order": int(bg_order)}))

    if gui_state.get("facet_level"):
        steps.append(ProcessingStep("facet_level", {"threshold_deg": 3.0}))

    smooth_sigma = gui_state.get("smooth_sigma")
    if smooth_sigma:
        steps.append(ProcessingStep("smooth", {"sigma_px": float(smooth_sigma)}))

    edge_method = gui_state.get("edge_method")
    if edge_method:
        steps.append(ProcessingStep("edge_detect", {
            "method": str(edge_method),
            "sigma":  float(gui_state.get("edge_sigma",  1.0)),
            "sigma2": float(gui_state.get("edge_sigma2", 2.0)),
        }))

    fft_mode = gui_state.get("fft_mode")
    if fft_mode is not None:
        steps.append(ProcessingStep("fourier_filter", {
            "mode":   str(fft_mode),
            "cutoff": float(gui_state.get("fft_cutoff", 0.10)),
            "window": str(gui_state.get("fft_window",   "hanning")),
        }))

    return ProcessingState(steps=steps)


def apply_processing_state_to_scan(
    scan: "Scan",
    proc_state: dict,
    *,
    plane_idx: int = 0,
) -> "Scan":
    """Apply GUI processing state to a Scan before export.

    Converts *proc_state* to a canonical :class:`ProcessingState`, applies it
    via :func:`~probeflow.processing_state.apply_processing_state`, and
    records each step in ``scan.processing_history``.

    Updates ``scan.planes[plane_idx]`` in place and returns *scan*.
    Display-only settings (grain overlay, colormap, clip percentiles) are ignored.
    """
    from probeflow.processing_state import apply_processing_state

    if plane_idx < 0 or plane_idx >= len(scan.planes):
        raise ValueError(
            f"plane_idx={plane_idx} out of range for Scan with "
            f"{len(scan.planes)} plane(s)"
        )

    state    = processing_state_from_gui(proc_state)
    now      = datetime.now().isoformat()
    a        = apply_processing_state(scan.planes[plane_idx], state)

    scan.planes[plane_idx] = a

    for step in state.steps:
        scan.processing_history.append({
            "op":        step.op,
            "params":    dict(step.params),
            "timestamp": now,
        })

    return scan
