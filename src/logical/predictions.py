from src.strategy.fe_v1 import make_features

def make_prediction(new_df, clf, reg, horizon=5):
    X, y_reg, y_cls = make_features(new_df, horizon=horizon)

    # берём последнюю строку (текущий момент)
    X_latest = X.iloc[[-1]]

    proba = clf.predict_proba(X_latest)[0, 1]  # вероятность роста
    y_pred_reg = reg.predict(X_latest)[0]      # ожидаемая доходность

    return proba, y_pred_reg
