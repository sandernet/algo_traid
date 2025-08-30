from src.logical.loading_data import get_kline_data_timeframe
from src.strategy.fe_v1 import make_features

import joblib



def education(df):

    X, y_reg, y_cls = make_features(df, horizon=5)

    # обучаем классификатор
    from lightgbm import LGBMClassifier
    clf = LGBMClassifier()
    clf.fit(X, y_cls)

    # обучаем регрессию
    from lightgbm import LGBMRegressor
    reg = LGBMRegressor()
    reg.fit(X, y_reg)
    
    # сохраняем
    joblib.dump(clf, "clf_model.pkl")
    joblib.dump(reg, "reg_model.pkl")

    return clf, reg
    