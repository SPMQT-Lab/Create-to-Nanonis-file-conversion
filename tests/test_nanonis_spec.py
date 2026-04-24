"""Tests for the Nanonis .dat point-spectroscopy reader."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from probeflow.readers.nanonis_spec import read_nanonis_spec
from probeflow.spec_io import read_spec_file


TESTDATA = Path(__file__).resolve().parents[1] / "anonymised_testdata"

KELVIN = TESTDATA / "nanonis_kelvin_parabola_500mv.dat"
KONDO  = TESTDATA / "nanonis_sts_kondo_15mv.dat"


@pytest.fixture(scope="module")
def kelvin_spec():
    return read_nanonis_spec(KELVIN)


@pytest.fixture(scope="module")
def kondo_spec():
    return read_nanonis_spec(KONDO)


class TestParseBasics:
    def test_kelvin_parses(self, kelvin_spec):
        assert kelvin_spec.metadata["n_points"] > 0

    def test_kondo_parses(self, kondo_spec):
        assert kondo_spec.metadata["n_points"] > 0

    def test_kelvin_sweep_type(self, kelvin_spec):
        assert kelvin_spec.metadata["sweep_type"] == "bias_sweep"

    def test_kondo_sweep_type(self, kondo_spec):
        assert kondo_spec.metadata["sweep_type"] == "bias_sweep"


class TestChannels:
    def test_kelvin_has_bias_and_current(self, kelvin_spec):
        assert "Bias calc" in kelvin_spec.channels
        assert "Current" in kelvin_spec.channels
        # Any secondary channel — Kelvin file has OC M1 Freq. Shift and Input 6.
        secondary = {"OC M1 Freq. Shift", "Input 6"}
        assert secondary & set(kelvin_spec.channels)

    def test_kondo_has_bias_and_current_avg(self, kondo_spec):
        assert "Bias calc" in kondo_spec.channels
        assert "Current [AVG]" in kondo_spec.channels
        assert "LockIn [AVG]" in kondo_spec.channels


class TestXAxis:
    def test_kelvin_x_is_bias_v(self, kelvin_spec):
        assert kelvin_spec.x_unit == "V"
        assert "Bias" in kelvin_spec.x_label

    def test_kondo_x_is_bias_v(self, kondo_spec):
        assert kondo_spec.x_unit == "V"
        assert "Bias" in kondo_spec.x_label

    def test_x_array_matches_column(self, kelvin_spec):
        assert np.allclose(kelvin_spec.x_array, kelvin_spec.channels["Bias calc"])


class TestDefaults:
    def test_kelvin_default_channels_include_current_and_secondary(self, kelvin_spec):
        defaults = kelvin_spec.default_channels
        assert any(name.startswith("Current") for name in defaults)
        # At least one non-current secondary
        assert any(not name.startswith("Current") for name in defaults)

    def test_kondo_default_channels_include_current_avg(self, kondo_spec):
        defaults = kondo_spec.default_channels
        assert any(name.startswith("Current") for name in defaults)

    def test_defaults_reference_real_channels(self, kelvin_spec, kondo_spec):
        for spec in (kelvin_spec, kondo_spec):
            for name in spec.default_channels:
                assert name in spec.channels


class TestPosition:
    def test_kelvin_position_floats(self, kelvin_spec):
        px, py = kelvin_spec.position
        assert isinstance(px, float)
        assert isinstance(py, float)
        assert px != 0.0
        assert py != 0.0

    def test_kondo_position_floats(self, kondo_spec):
        px, py = kondo_spec.position
        assert isinstance(px, float)
        assert isinstance(py, float)
        assert px != 0.0
        assert py != 0.0


class TestDispatcher:
    def test_read_spec_file_routes_nanonis(self):
        spec = read_spec_file(KONDO)
        assert spec.metadata["sweep_type"] == "bias_sweep"
        assert "Current [AVG]" in spec.channels

    def test_read_spec_file_routes_createc_vert(self):
        # Existing Createc files should still go through the VERT reader.
        vert = TESTDATA / "createc_ivt_telegraph_300mv_a.VERT"
        if not vert.exists():
            pytest.skip("missing .VERT fixture")
        spec = read_spec_file(vert)
        assert "I" in spec.channels
        assert "Z" in spec.channels
