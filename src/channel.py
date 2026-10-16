"""Simulateur de canal : bruit blanc (SNR mesuré dans 3 kHz, convention codec2)
et fading HF de type Watterson à deux trajets (presets CCIR). numpy seul."""
import numpy as np

# nom : (retard du 2e trajet en ms, étalement Doppler en Hz)
CCIR = {"none": None, "good": (0.5, 0.1), "moderate": (1.0, 0.5), "poor": (2.0, 1.0)}


def _hilbert(x):
    """Signal analytique (équivalent de scipy.signal.hilbert)."""
    n = len(x)
    X = np.fft.fft(x)
    h = np.zeros(n)
    h[0] = 1
    if n % 2 == 0:
        h[n // 2] = 1
        h[1:n // 2] = 2
    else:
        h[1:(n + 1) // 2] = 2
    return np.fft.ifft(X * h)


def _gauss_smooth(x, sigma):
    """Filtrage gaussien (équivalent de scipy.ndimage.gaussian_filter1d)."""
    r = int(4 * sigma + 0.5)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(x, r, mode="reflect"), k, mode="valid")


def _fading_gain(n, fs, spread_hz, rng):
    """Gain complexe gaussien, spectre Doppler gaussien de largeur 2σ = spread."""
    rate = 100.0
    m = int(n / fs * rate) + 50
    sigma = rate / (np.pi * spread_hz)          # écart-type temporel du filtre, en échantillons
    g = _gauss_smooth(rng.standard_normal(m), sigma) + 1j * _gauss_smooth(rng.standard_normal(m), sigma)
    g /= np.sqrt(np.mean(np.abs(g) ** 2))
    t = np.arange(n) / fs * rate
    return np.interp(t, np.arange(m), g.real) + 1j * np.interp(t, np.arange(m), g.imag)


def apply(samples: np.ndarray, fs: int, snr_db: float, fading="none", seed=0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = samples.astype(np.float64)
    active = np.abs(x) > 1
    ps = np.mean(x[active] ** 2)                 # puissance pendant l'émission
    if CCIR.get(fading):
        delay_ms, spread = CCIR[fading]
        xa = _hilbert(x)
        d = int(round(delay_ms * 1e-3 * fs))
        g1, g2 = _fading_gain(len(x), fs, spread, rng), _fading_gain(len(x), fs, spread, rng)
        y = g1 * xa + g2 * np.concatenate([np.zeros(d), xa[:-d]])
        x = np.real(y) / np.sqrt(2)              # 2 trajets de même puissance
    sigma2 = ps * (fs / 2) / (3000 * 10 ** (snr_db / 10))
    x = x + rng.standard_normal(len(x)) * np.sqrt(sigma2)
    peak = np.max(np.abs(x))
    if peak > 30000:                             # on réduit le niveau plutôt que d'écrêter
        x *= 30000 / peak
    return x.astype(np.int16)
