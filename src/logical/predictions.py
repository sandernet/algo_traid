from src.strategy.fe_v1 import make_features
from src.strategy.fe_v2 import make_features_v2


def make_prediction(new_df, clf, reg, horizon=5):
    X, y_reg, y_cls = make_features_v2(new_df, horizon=horizon)

    # берём последнюю строку (текущий момент)
    X_latest = X.iloc[[-1]]

    proba_down, proba_up = clf.predict_proba(X_latest)[0]
    print("Вероятность падения:", proba_down)
    print("Вероятность роста:", proba_up)

    # proba = clf.predict_proba(X_latest)[0, 1]  # вероятность роста
    y_pred_reg = reg.predict(X_latest)[0]      # ожидаемая доходность

    return proba_down, proba_up, y_pred_reg
