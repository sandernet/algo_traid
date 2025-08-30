from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, List, Dict, Optional
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score, log_loss, precision_recall_fscore_support
from lightgbm import LGBMClassifier
import warnings

# =============== ВСПОМОГАТЕЛЬНЫЕ УТИЛИТЫ ===============

def _safe_div(a, b):
    out = np.divide(a, b, out=np.zeros_like(a, dtype=float), where=(b != 0))
    return out

def _ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "Date" in df.columns and not isinstance(df.index, pd.DatetimeIndex):
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("Нужен DatetimeIndex (или колонка Date).")
    return df.sort_index()

# =============== ФИЧИ (улучшенная версия) ===============

def make_features_v2(df: pd.DataFrame, horizon: int = 5) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Улучшенная версия вашей функции:
    - больше технических индикаторов
    - нормализация некоторых величин к цене
    - корректный shift всех фич (t -> решение на t, результат на t+1..t+h)
    """
    out = _ensure_datetime_index(df)

    # Базовые возвраты и волатильность
    out["ret_1"] = out["Close"].pct_change()
    for l in [2, 3, 5, 10]:
        out[f"ret_{l}"] = out["Close"].pct_change(l)

    # Скользящие средние и спрэды (MACD-подобное)
    out["ema_12"] = out["Close"].ewm(span=12, adjust=False).mean()
    out["ema_26"] = out["Close"].ewm(span=26, adjust=False).mean()
    out["ema_spread"] = (out["ema_12"] - out["ema_26"]) / out["Close"]
    out["macd"] = out["ema_12"] - out["ema_26"]
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()
    out["macd_hist"] = out["macd"] - out["macd_signal"]

    # RSI c экспоненциальным сглаживанием (Wilder)
    delta = out["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = _safe_div(avg_gain, avg_loss)
    out["rsi_14"] = 100 - (100 / (1 + rs))

    # Stochastic Oscillator
    low_min_14 = out["Low"].rolling(14).min()
    high_max_14 = out["High"].rolling(14).max()
    out["stoch_k"] = _safe_div(out["Close"] - low_min_14, (high_max_14 - low_min_14)) * 100
    out["stoch_d"] = out["stoch_k"].rolling(3).mean()

    # Bollinger Bands
    ma20 = out["Close"].rolling(20).mean()
    std20 = out["Close"].rolling(20).std()
    out["bb_pos"] = _safe_div(out["Close"] - ma20, std20)          # положение в полосах
    out["bb_width"] = 2 * std20 / out["Close"]

    # True Range / ATR (Wilder)
    prev_close = out["Close"].shift(1)
    tr = pd.concat([
        (out["High"] - out["Low"]).abs(),
        (out["High"] - prev_close).abs(),
        (out["Low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    atr14 = tr.ewm(alpha=1/14, adjust=False).mean()
    out["atr_14"] = atr14
    out["atr_pct"] = _safe_div(atr14, out["Close"])

    # Диапазоны и форма свечи
    out["hl_range_pct"] = _safe_div(out["High"] - out["Low"], out["Close"])
    out["oc_range_pct"] = _safe_div(out["Close"] - out.get("Open", out["Close"]), out["Close"])
    out["upper_wick"] = _safe_div(out["High"] - out[["Close", "Open"]].max(axis=1), out["Close"])
    out["lower_wick"] = _safe_div(out[["Close", "Open"]].min(axis=1) - out["Low"], out["Close"])

    # Волатильности
    for w in [5, 10, 20, 30]:
        out[f"ret_vol_{w}"] = out["ret_1"].rolling(w).std()
        out[f"ret_ewmvol_{w}"] = out["ret_1"].ewm(span=w, adjust=False).std()

    # Объём (если есть)
    if "Volume" in out.columns:
        out["vol_chg_1"] = out["Volume"].pct_change()
        out["vol_ma_20"] = out["Volume"].rolling(20).mean()
        out["vol_z_20"] = _safe_div(out["Volume"] - out["vol_ma_20"], out["Volume"].rolling(20).std())


    # Таргеты: форвардная доходность на горизонте и бинарная метка
    # Используем log-доходность (устойчивее при больших шагов)
    future_close = out["Close"].shift(-horizon)
    y_reg = np.log(_safe_div(future_close, out["Close"]))      # лог-ретёрн за horizon
    # Классификация: можно добавить "мёртвую зону" для шумовых движений
    threshold = 0.0  # при желании сделайте 0.001 (0.1%) и используйте 2-класса +/- (а нули отфильтровать)
    y_cls = (y_reg > threshold).astype(int)

    # Сдвиг фич на 1 бар, чтобы решение принималось на t, а результат на t+1..t+h
    features = [
        c for c in out.columns
        if c not in {"Close", "Open", "High", "Low"}  # базовые цены в сыром виде не используем, чтобы не схватить утечку со shift?
    ]
    X = out[features].shift(1)

    # Синхронная очистка
    # df_all = pd.concat([X, y_reg.rename("y_reg"), y_cls.rename("y_cls")], axis=1).dropna()
    df_all = pd.concat([
    X,
    pd.Series(y_reg, index=X.index, name="y_reg"),
    pd.Series(y_cls, index=X.index, name="y_cls")
    ], axis=1).dropna()

    X = df_all.drop(columns=["y_reg", "y_cls"])
    y_reg = df_all["y_reg"]
    y_cls = df_all["y_cls"].astype(int)

    # Явно отметить категориальные признаки
    for cat_col in ["dow", "month", "is_month_end"]:
        if cat_col in X.columns:
            X[cat_col] = X[cat_col].astype("category")

    return X, y_reg, y_cls

# fold_probas: pd.Series
#     fold_index: pd.Index
#     models: List[LGBMClassifier]
#     feature_importance_: pd.DataFrame
#     best_threshold: float
#     metrics: Dict[str, float]
#     strategy_report: Dict[str, float]
#     equity_curve: pd.Series
#     signals: pd.Series

# def _annualize_factor(freq: str | None, index: pd.DatetimeIndex) -> float:
#     # Автоматический множитель для годовой Sharpe
#     if freq is None and isinstance(index, pd.DatetimeIndex):
#         # оценим частоту по медиане шага
#         delta = np.median(np.diff(index.values).astype("timedelta64[D]").astype(int))
#         if delta <= 1:
#             return np.sqrt(252)
#         elif delta <= 7:
#             return np.sqrt(52)
#         elif delta <= 31:# =============== WALK-FORWARD ВАЛИДАЦИЯ И ОБУЧЕНИЕ ===============

# @dataclass
# class CVResult:
#     fold_preds: pd.Series
#     fold_probas: pd.Series
#     fold_index: pd.Index
#     models: List[LGBMClassifier]
#     feature_importance_: pd.DataFrame
#     best_threshold: float
#     metrics: Dict[str, float]
#     strategy_report: Dict[str, float]
#     equity_curve: pd.Series
#     signals: pd.Series

# def _annualize_factor(freq: str | None, index: pd.DatetimeIndex) -> float:
#     # Автоматический множитель для годовой Sharpe
#     if freq is None and isinstance(index, pd.DatetimeIndex):
#         # оценим частоту по медиане шага
#         delta = np.median(np.diff(index.values).astype("timedelta64[D]").astype(int))
#         if delta <= 1:
#             return np.sqrt(252)
#         elif delta <= 7:
#             return np.sqrt(52)
#         elif delta <= 31:

# # =============== WALK-FORWARD ВАЛИДАЦИЯ И ОБУЧЕНИЕ ===============

# @dataclass
# class CVResult:
#     fold_preds: pd.Series
    

# # =============== WALK-FORWARD ВАЛИДАЦИЯ И ОБУЧЕНИЕ ===============

# @dataclass
# class CVResult:
#     fold_preds: pd.Series
#     fold_probas: pd.Series
#     fold_index: pd.Index
#     models: List[LGBMClassifier]
#     feature_importance_: pd.DataFrame
#     best_threshold: float
#     metrics: Dict[str, float]
#     strategy_report: Dict[str, float]
#     equity_curve: pd.Series
#     signals: pd.Series

# def _annualize_factor(freq: str | None, index: pd.DatetimeIndex) -> float:
#     # Автоматический множитель для годовой Sharpe
#     if freq is None and isinstance(index, pd.DatetimeIndex):
#         # оценим частоту по медиане шага
#         delta = np.median(np.diff(index.values).astype("timedelta64[D]").astype(int))
#         if delta <= 1:
#             return np.sqrt(252)
#         elif delta <= 7:
#             return np.sqrt(52)
#         elif delta <= 31:
#             return np.sqrt(12)
#     return np.sqrt(252)

# def _max_drawdown(series: pd.Series) -> float:
#     cummax = series.cummax()
#     dd = series / cummax - 1.0
#     return dd.min()

# def _sharpe(returns: pd.Series, ann_factor: float) -> float:
#     mu = returns.mean()
#     sd = returns.std()
#     if sd == 0 or np.isnan(sd):
#         return 0.0
#     return (mu / sd) * ann_factor

# def _build_signals(proba: pd.Series, thr: float) -> pd.Series:
#     # long / flat / short: симметричный порог
#     # long если p>thr, short если p<1-thr, иначе 0
#     sig = pd.Series(0, index=proba.index, dtype=int)
#     sig[proba > thr] = 1
#     sig[proba < (1 - thr)] = -1
#     return sig

# def _optimize_threshold(val_proba: pd.Series, y_reg_val: pd.Series,
#                         cost_bps: float = 1.0, horizon: int = 5, index: pd.DatetimeIndex | None = None) -> float:
#     ann = _annualize_factor(None, index if index is not None else val_proba.index)
#     # Грид порогов 0.50..0.70
#     grid = np.linspace(0.50, 0.70, 21)
#     best_thr, best_sharpe = 0.5, -np.inf
#     for thr in grid:
#         sig = _build_signals(val_proba, thr)
#         # позиция берётся в момент t (по вероятности), реализованный ретёрн — y_reg (за horizon)
#         # транзакционные издержки (двусторонние): bps на смену позиции
#         pos = sig.shift(0).fillna(0)  # уже сдвинутость фич учтена ранее
#         # Реализация: лог-ретёрн y_reg соответствует ходу за horizon вперёд
#         # Для единичной позиции доходность = pos * y_reg
#         strat = pos * y_reg_val
#         # комиссии в лог-доходности ~ bps/10000 при смене позиции
#         turns = pos.diff().abs().fillna(0)
#         fee = turns * (cost_bps / 10000.0)
#         strat_net = strat - fee
#         sh = _sharpe(strat_net.dropna(), ann)
#         if sh > best_sharpe:
#             best_sharpe, best_thr = sh, thr
#     return float(best_thr)

# def train_lightgbm_walkforward(
#     X: pd.DataFrame,
#     y_cls: pd.Series,
#     y_reg: pd.Series,
#     n_splits: int = 5,
#     min_train_size: int = 500,
#     horizon: int = 5,
#     cost_bps: float = 1.0,
#     lgbm_params: Optional[Dict] = None,
#     verbose: bool = True
# ) -> CVResult:

#     assert (X.index == y_cls.index).all() and (X.index == y_reg.index).all(), "Индексы X / y должны совпадать и быть времени."

#     # Базовые параметры LGBM (anti-overfit + скорость)
#     if lgbm_params is None:
#         lgbm_params = dict(
#             objective="binary",
#             n_estimators=2000,
#             learning_rate=0.02,
#             num_leaves=64,
#             max_depth=-1,            # ограничение через min_data_in_leaf/num_leaves
#             min_data_in_leaf=100,
#             subsample=0.8,           # bagging_fraction
#             subsample_freq=1,        # bagging_freq
#             colsample_bytree=0.8,    # feature_fraction
#             reg_alpha=1.0,
#             reg_lambda=2.0,
#             random_state=42,
#             n_jobs=-1
#         )

#     tscv = TimeSeriesSplit(n_splits=n_splits)
#     all_models: List[LGBMClassifier] = []
#     all_importances: List[pd.DataFrame] = []
#     oof_proba = pd.Series(index=X.index, dtype=float)
#     oof_pred = pd.Series(index=X.index, dtype=int)

#     # Walk-forward с early stopping на валидации каждого фолда
#     for fold, (tr_idx, val_idx) in enumerate(tscv.split(X), 1):
#         tr_idx = np.array(tr_idx)
#         val_idx = np.array(val_idx)

#         # Гарантия минимальной обучающей выборки (часто критично на часовых/дневных рядах)
#         if len(tr_idx) < min_train_size:
#             if verbose:
#                 warnings.warn(f"Fold {fold}: пропуск (слишком мало train: {len(tr_idx)} < {min_train_size})")
#             continue

#         X_tr, X_val = X.iloc[tr_idx], X.iloc[val_idx]
#         y_tr, y_val = y_cls.iloc[tr_idx], y_cls.iloc[val_idx]
#         y_reg_val = y_reg.iloc[val_idx]

#         model = LGBMClassifier(**lgbm_params)
#         model.fit(
#             X_tr, y_tr,
#             eval_set=[(X_val, y_val)],
#             eval_metric="auc",
#             callbacks=[],  # можно добавить early_stopping из lightgbm.callback, но sklearn-обёртка уже умеет
#         )
#         all_models.append(model)

#         # Прогноз на валидации
#         proba_val = pd.Series(model.predict_proba(X_val)[:, 1], index=X_val.index)
#         oof_proba.loc[X_val.index] = proba_val
#         oof_pred.loc[X_val.index] = (proba_val > 0.5).astype(int)

#         # FI
#         fi = pd.DataFrame({
#             "feature": X.columns,
#             "importance": model.feature_importances_,
#             "fold": fold
#         }).sort_values("importance", ascending=False)
#         all_importances.append(fi)

#         if verbose:
#             auc = roc_auc_score(y_val, proba_val)
#             print(f"Fold {fold}: AUC={auc:.4f}, val_size={len(val_idx)}")

#     # Метрики по OOF
#     valid_mask = oof_proba.notna()
#     auc = roc_auc_score(y_cls[valid_mask], oof_proba[valid_mask])
#     acc = accuracy_score(y_cls[valid_mask], (oof_proba[valid_mask] > 0.5).astype(int))
#     try:
#         ll = log_loss(y_cls[valid_mask], np.vstack([1 - oof_proba[valid_mask], oof_proba[valid_mask]]).T, labels=[0,1])
#     except Exception:
#         ll = np.nan
#     prec, rec, f1, _ = precision_recall_fscore_support(
#         y_cls[valid_mask], (oof_proba[valid_mask] > 0.5).astype(int), average="binary"
#     )

#     # Подбор порога по Sharpe на OOF валидации
#     best_thr = _optimize_threshold(
#         oof_proba[valid_mask], y_reg[valid_mask],
#         cost_bps=cost_bps, horizon=horizon, index=X.index
#     )

#     # Формируем сигналы и стратегию на OOF (out-of-fold)
#     ann = _annualize_factor(None, X.index)
#     signals = _build_signals(oof_proba, best_thr).rename("signal")
#     pos = signals  # позиция на t
#     strat = (pos * y_reg).rename("strategy_logret")  # лог-доход за horizon на каждую сделку
#     turns = pos.diff().abs().fillna(0)
#     fee = turns * (cost_bps / 10000.0)
#     strat_net = strat - fee

#     # Преобразуем лог-ретёрны в эквити (накопительный капитал)
#     equity = np.exp(strat_net.fillna(0).cumsum()).rename("equity")

#     sharpe = _sharpe(strat_net.dropna(), ann)
#     mdd = _max_drawdown(equity)
#     avg_trades_m = turns.resample("M").sum().mean() if isinstance(X.index, pd.DatetimeIndex) else turns.mean()

#     metrics = {
#         "oof_auc": float(auc),
#         "oof_accuracy": float(acc),
#         "oof_logloss": float(ll) if not np.isnan(ll) else None,
#         "oof_precision": float(prec),
#         "oof_recall": float(rec),
#         "oof_f1": float(f1),
#     }
#     strategy_report = {
#         "best_threshold": float(best_thr),
#         "sharpe_ann": float(sharpe),
#         "max_drawdown": float(mdd),
#         "avg_position_changes_per_month": float(avg_trades_m) if avg_trades_m is not None else None,
#         "mean_logret": float(strat_net.mean()),
#         "std_logret": float(strat_net.std()),
#     }

#     fi_all = pd.concat(all_importances, ignore_index=True) if all_importances else pd.DataFrame(columns=["feature","importance","fold"])
#     fi_mean = (fi_all.groupby("feature")["importance"].mean().sort_values(ascending=False)
#                .rename("avg_importance").to_frame())

#     return CVResult(
#         fold_preds=oof_pred,
#         fold_probas=oof_proba,
#         fold_index=X.index,
#         models=all_models,
#         feature_importance_=fi_mean,
#         best_threshold=best_thr,
#         metrics=metrics,
#         strategy_report=strategy_report,
#         equity_curve=equity,
#         signals=signals
#     )

# # =============== ПРИМЕР ИСПОЛЬЗОВАНИЯ ===============
# if __name__ == "__main__":
#     # Пример: df = pd.read_csv("prices.csv")  # с колонками Date, Open, High, Low, Close[, Volume]
#     # Ниже просто эскиз. Загрузите свои данные вместо генерации.
#     # df = your_dataframe

#     # --- 1) Фичи и таргеты
#     # X, y_reg, y_cls = make_features_v2(df, horizon=5)

#     # --- 2) Обучение и бэктест Walk-Forward
#     # cv = train_lightgbm_walkforward(
#     #     X, y_cls, y_reg,
#     #     n_splits=5,
#     #     min_train_size=500,
#     #     horizon=5,
#     #     cost_bps=1.0,
#     # )

#     # --- 3) Отчёты
#     # print("OOF metrics:", cv.metrics)
#     # print("Strategy report:", cv.strategy_report)
#     # print(cv.feature_importance_.head(20))

#     # --- 4) Использование последней модели в проде
#     # last_model = cv.models[-1]
#     # proba_today = last_model.predict_proba(X.iloc[[-1]])[:,1][0]
#     # signal_today = 1 if proba_today > cv.best_threshold else (-1 if proba_today < (1-cv.best_threshold) else 0)
#     # print("proba_today:", proba_today, "signal_today:", signal_today)
#     pass
