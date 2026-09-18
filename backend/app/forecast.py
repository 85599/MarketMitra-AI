"""AI price forecasting: numpy MLP ensemble with backtest-based confidence intervals.

Trains directly on the server in well under a second using recent daily data.
A single multi-output ensemble predicts 1-, 5- and 10-day-ahead returns; the
ensemble spread plus historical backtest residuals give an honest prediction
range instead of a single "guaranteed" number.
"""
import numpy as np
import pandas as pd

LOOKBACK = 16          # features from the past N days
HORIZONS = [1, 5, 10]  # trading days ahead
HMAX = max(HORIZONS)
HIDDEN = 32
ENSEMBLE = 5
EPOCHS = 220
LR = 0.01


def _build_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Feature rows for i in [LOOKBACK, len-1]; the last row anchors prediction."""
    close = df["Close"].values
    rsi_v = df["RSI14"].values
    macd_h = df["MACD_HIST"].values
    atr_v = df["ATR14"].values
    vol = df["Volume"].values.astype(float)
    vol_sma = df["VOL_SMA20"].values

    rets = np.diff(close) / close[:-1]
    rets = np.concatenate([[0.0], rets])
    vol_ratio = np.divide(vol, np.where(vol_sma > 0, vol_sma, np.nan))
    vol_ratio = np.nan_to_num(vol_ratio, nan=1.0)
    atr_pct = np.nan_to_num(atr_v / close)

    rows, idxs = [], []
    for i in range(LOOKBACK, len(close)):
        window_ret = rets[i - LOOKBACK + 1: i + 1]
        feat = np.concatenate([
            window_ret,
            [(close[i] / close[i - LOOKBACK] - 1.0)],
            [(close[i] / np.mean(close[i - 5:i]) - 1.0)],
            [(close[i] / np.mean(close[i - 10:i]) - 1.0) if i >= 10 else 0.0],
            [(close[i] / np.mean(close[i - 20:i]) - 1.0) if i >= 20 else 0.0],
            [(rsi_v[i] - 50.0) / 50.0],
            [macd_h[i] / close[i]],
            [atr_pct[i]],
            [vol_ratio[i] - 1.0],
            [np.std(window_ret) * np.sqrt(252)],
        ])
        rows.append(feat)
        idxs.append(i)

    return np.array(rows), np.array(idxs)


class _MLP:
    """Single-hidden-layer tanh net with `n_out` regression targets."""

    def __init__(self, n_in: int, n_hidden: int, n_out: int, seed: int):
        rng = np.random.default_rng(seed)
        self.W1 = rng.normal(0, np.sqrt(2 / n_in), (n_in, n_hidden))
        self.b1 = np.zeros(n_hidden)
        self.W2 = rng.normal(0, np.sqrt(1 / n_hidden), (n_hidden, n_out))
        self.b2 = np.zeros(n_out)
        self._rng = rng

    def forward(self, X):
        a = np.tanh(X @ self.W1 + self.b1)
        return a, a @ self.W2 + self.b2

    def predict(self, X):
        return self.forward(X)[1]

    def fit(self, X, y):
        m = len(y)
        params = [self.W1, self.b1, self.W2, self.b2]
        mom = [np.zeros_like(p) for p in params]
        vel = [np.zeros_like(p) for p in params]
        beta1, beta2, eps = 0.9, 0.999, 1e-8
        t = 0
        for _ in range(EPOCHS):
            idx = self._rng.permutation(m)
            Xs, ys = X[idx], y[idx]
            bs = max(16, m // 10)
            for s in range(0, m, bs):
                xb, yb = Xs[s:s + bs], ys[s:s + bs]
                a, out = self.forward(xb)
                err = (out - yb) * 2 / len(yb)
                gW2 = a.T @ err
                gb2 = err.sum(axis=0)
                da = err @ self.W2.T
                dz = da * (1 - a * a)
                gW1 = xb.T @ dz
                gb1 = dz.sum(axis=0)
                t += 1
                for g, p, mm, vv in zip([gW1, gb1, gW2, gb2], params, mom, vel, strict=True):
                    mm *= beta1
                    mm += (1 - beta1) * g
                    vv *= beta2
                    vv += (1 - beta2) * (g ** 2)
                    p -= LR * (mm / (1 - beta1 ** t)) / (np.sqrt(vv / (1 - beta2 ** t)) + eps)


def _standardize(X: np.ndarray):
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    return (X - mu) / sd, mu, sd


def forecast(df: pd.DataFrame) -> dict:
    """Multi-horizon forecast. Top-level fields describe the 1-day (next close)."""
    X, idxs = _build_features(df)
    close = df["Close"].values
    dates = df.index
    n = len(close)
    if len(X) < 80 + HMAX:
        return {"error": "not enough history for a forecast"}

    Xs, mu, sd = _standardize(X)
    anchor = Xs[-1:]                       # features at the latest bar
    last_close = float(close[-1])

    # Training rows: those where every horizon target exists (i + HMAX <= n-1).
    train_mask = (idxs + HMAX) <= (n - 1)
    Xtr_all = Xs[train_mask]
    ti = idxs[train_mask]
    Y = np.column_stack([close[ti + H] / close[ti] - 1.0 for H in HORIZONS])

    n_val = min(60, len(Xtr_all) // 4)
    Xtr, Ytr = Xtr_all[:-n_val], Y[:-n_val]
    Xva, Yva = Xtr_all[-n_val:], Y[-n_val:]

    models, val_preds = [], []
    for k in range(ENSEMBLE):
        net = _MLP(X.shape[1], HIDDEN, len(HORIZONS), seed=42 + k)
        net.fit(Xtr, Ytr)
        models.append(net)
        val_preds.append(net.predict(Xva))
    val_mean = np.mean(val_preds, axis=0)              # (n_val, n_horizons)
    next_rets = np.mean([m.predict(anchor) for m in models], axis=0).ravel()

    residuals = Yva - val_mean
    sigmas, horizons = [], []
    for j, H in enumerate(HORIZONS):
        resid_std = float(np.std(residuals[:, j])) if n_val else 0.0
        spread = float(np.std([m.predict(anchor)[0][j] for m in models]))
        sigma = max(resid_std, spread, 0.002)
        sigmas.append(sigma)
        pred_ret = float(next_rets[j])
        predicted_price = last_close * (1 + pred_ret)
        dir_acc = round(float(np.mean(np.sign(val_mean[:, j]) == np.sign(Yva[:, j]))), 3) if n_val else 0.0
        horizons.append({
            "h": H,
            "predictedReturn": round(pred_ret, 5),
            "predictedPrice": round(predicted_price, 2),
            "direction": "up" if pred_ret >= 0 else "down",
            "range80": [round(last_close * (1 + pred_ret - 1.28 * sigma), 2),
                        round(last_close * (1 + pred_ret + 1.28 * sigma), 2)],
            "range95": [round(last_close * (1 + pred_ret - 1.96 * sigma), 2),
                        round(last_close * (1 + pred_ret + 1.96 * sigma), 2)],
            "directionAccuracy": dir_acc,
            "mape": round(float(np.mean(np.abs(residuals[:, j]))) * 100, 3),
        })

    h1 = horizons[0]
    sigma1 = sigmas[0]
    pred_ret1 = float(next_rets[0])

    # Backtest history for the 1-day horizon, over the validation window.
    history = []
    val_idx = ti[-n_val:]
    for r in range(n_val):
        i = val_idx[r]
        history.append({
            "date": pd.Timestamp(dates[i + 1]).strftime("%Y-%m-%d"),
            "predictedReturn": round(float(val_mean[r, 0]), 5),
            "actualReturn": round(float(Yva[r, 0]), 5),
            "predictedPrice": round(float(close[i] * (1 + val_mean[r, 0])), 2),
            "actualPrice": round(float(close[i + 1]), 2),
        })

    return {
        "lastClose": round(last_close, 2),
        "predictedPrice": h1["predictedPrice"],
        "predictedReturn": round(pred_ret1, 5),
        "direction": h1["direction"],
        "range80": h1["range80"],
        "range95": h1["range95"],
        "confidence": round(max(0.0, min(1.0, 1 - sigma1 / max(abs(pred_ret1), 1e-6) * 0.5)), 2),
        "horizons": horizons,
        "modelStats": {
            "validationDays": int(n_val),
            "directionAccuracy": h1["directionAccuracy"],
            "mape": h1["mape"],
            "ensembleSize": ENSEMBLE,
            "architecture": f"MLP {X.shape[1]}-{HIDDEN}-{len(HORIZONS)} x{ENSEMBLE} (tanh, Adam)",
            "residualStd": round(sigma1, 5),
            "horizons": HORIZONS,
        },
        "history": history,
    }
