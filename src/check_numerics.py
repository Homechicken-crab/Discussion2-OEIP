"""Small invariant checks only; no course experiment or recovery benchmark."""
import json
import sys

import numpy as np

from deblur import motion_psf, psf_to_otf, restore, srgb_to_linear, linear_to_srgb


def main():
    checks = []
    rng = np.random.default_rng(20261101)
    image = rng.random((31, 37))
    for length, angle in [(0, 0), (9, 0), (15, 35), (12, 90)]:
        psf = motion_psf(length, angle)
        assert np.all(psf >= 0) and np.isclose(psf.sum(), 1)
        assert np.allclose(psf, psf[::-1, ::-1], atol=1e-12)
        transfer = psf_to_otf(psf, image.shape)
        direct = np.zeros_like(image)
        cy, cx = (d // 2 for d in psf.shape)
        for y, x in np.ndindex(psf.shape):
            direct += psf[y, x] * np.roll(image, (y-cy, x-cx), axis=(0, 1))
        via_fft = np.fft.ifft2(np.fft.fft2(image) * transfer).real
        assert np.allclose(direct, via_fft, atol=1e-12)
    checks.append("PSF nonnegativity, unit sum, centered symmetry and spatial-vs-FFT convolution agree")
    delta = np.array([[1.0]])
    assert np.allclose(psf_to_otf(delta, image.shape), 1)
    assert np.allclose(restore(image, delta, k=0.01, pad=0), image/1.01)
    assert np.allclose(restore(image, delta, method="inverse", pad=8), image)
    rgb = np.stack([image, image*0.5, image*0.25], axis=-1)
    assert np.allclose(restore(rgb, delta, k=0.01, pad=8), rgb/1.01)
    checks.append("delta PSF, Wiener closed form, inverse identity, RGB axes and reflect-crop dimensions")
    assert np.allclose(linear_to_srgb(srgb_to_linear(image)), image, atol=1e-12)
    checks.append("sRGB/linear conversion round trip")
    try:
        restore(image, delta, k=0)
    except ValueError:
        checks.append("invalid K rejected")
    else:
        raise AssertionError("K=0 accepted")
    print(json.dumps({"status": "passed", "scope": "preparation_numerical_checks_only_not_experimental_results", "checks": checks, "python": sys.version.split()[0], "numpy": np.__version__}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
