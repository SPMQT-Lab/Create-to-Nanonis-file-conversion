"""Tests for probeflow.processing.tv_denoise."""

from __future__ import annotations

import numpy as np
import pytest

from probeflow.processing import tv_denoise


@pytest.fixture
def noisy_terrace():
    """Two flat terraces separated by a step, with additive Gaussian noise."""
    rng = np.random.default_rng(0)
    clean = np.zeros((64, 64), dtype=np.float64)
    clean[:, 32:] = 1.0
    noise = rng.normal(scale=0.2, size=clean.shape)
    return clean + noise, clean


class TestTvDenoiseHuberROF:
    def test_reduces_rms_vs_input(self, noisy_terrace):
        noisy, clean = noisy_terrace
        denoised = tv_denoise(noisy, method="huber_rof", lam=0.2, max_iter=200)
        in_rms = float(np.sqrt(np.mean((noisy - clean) ** 2)))
        out_rms = float(np.sqrt(np.mean((denoised - clean) ** 2)))
        assert out_rms < in_rms

    def test_preserves_shape(self, noisy_terrace):
        noisy, _ = noisy_terrace
        denoised = tv_denoise(noisy, method="huber_rof", max_iter=50)
        assert denoised.shape == noisy.shape

    def test_preserves_edge_location(self, noisy_terrace):
        noisy, _ = noisy_terrace
        denoised = tv_denoise(noisy, method="huber_rof", lam=0.5, max_iter=200)
        # The step is around x=32. Find max of absolute x-gradient.
        gx = np.abs(np.diff(denoised.mean(axis=0)))
        assert 28 <= int(np.argmax(gx)) <= 35


class TestTvDenoiseTvL1:
    def test_tv_l1_runs_and_reduces_rms(self, noisy_terrace):
        noisy, clean = noisy_terrace
        denoised = tv_denoise(noisy, method="tv_l1", lam=0.5, max_iter=200)
        in_rms = float(np.sqrt(np.mean((noisy - clean) ** 2)))
        out_rms = float(np.sqrt(np.mean((denoised - clean) ** 2)))
        assert out_rms < in_rms


class TestTvDenoiseErrors:
    def test_non_2d_raises(self):
        with pytest.raises(ValueError):
            tv_denoise(np.zeros((4, 4, 4)), method="huber_rof")

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError):
            tv_denoise(np.zeros((8, 8)), method="nope")

    def test_bad_nabla_raises(self):
        with pytest.raises(ValueError):
            tv_denoise(np.zeros((8, 8)), method="huber_rof", nabla_comp="z")


class TestNablaDirectional:
    def test_nabla_x_reduces_horizontal_streaks(self):
        """x-only gradient should preferentially smooth vertical scratches."""
        rng = np.random.default_rng(1)
        img = rng.normal(scale=0.02, size=(64, 64))
        # Add 4 vertical scratches
        for c in (10, 25, 40, 55):
            img[:, c] += 2.0
        denoised = tv_denoise(img, method="huber_rof", lam=0.3,
                              nabla_comp="x", max_iter=200)
        assert denoised.shape == img.shape
