"""
Optimization module
"""

import numpy as np
from decimal import Decimal
import logging
import optuna
from optuna.samplers import TPESampler
from config.config import OPTIMIZATION_CONFIG
from backtesting import Backtesting


class OptunaCallBack:
    """
    Optuna call back class
    """

    def __init__(self) -> None:
        """
        Init optuna callback
        """
        logging.basicConfig(
            filename="result/optimization/optimization.log.csv",
            format="%(message)s",
            filemode="w",
        )
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        self.logger = logger
        self.logger.info("number,window_size,threshold,sharpe_ratio")

    def __call__(self, _: optuna.study.Study, trial: optuna.trial.FrozenTrial) -> None:
        """

        Args:
            study (optuna.study.Study): _description_
            trial (optuna.trial.FrozenTrial): _description_
        """
        window_size = trial.params["window_size"]
        threshold = trial.params["threshold"]
        self.logger.info(
            "%s,%s,%s,%s",
            trial.number,
            window_size,
            threshold,
            trial.value,
        )


if __name__ == "__main__":
    data = Backtesting.process_data()

    def objective(trial):
        """
        Sharpe ratio objective function

        Args:
            trial (_type_): _description_

        Returns:
            _type_: _description_
        """
        
        window_size = trial.suggest_int(
            "window_size",
            OPTIMIZATION_CONFIG["window_size"][0],
            OPTIMIZATION_CONFIG["window_size"][1],
        )

        bt = Backtesting(capital=Decimal("5e5"), window_size=window_size, printable=False)
        threshold = trial.suggest_float(
            "threshold",
            OPTIMIZATION_CONFIG["threshold"][0],
            OPTIMIZATION_CONFIG["threshold"][1],
            step=0.1,
        )

        bt.run(data, Decimal(threshold))

        return bt.metric.sharpe_ratio(risk_free_return=Decimal('0.00023')) * Decimal(
            np.sqrt(250)
        )

    optunaCallBack = OptunaCallBack()
    study = optuna.create_study(
        sampler=TPESampler(seed=OPTIMIZATION_CONFIG["random_seed"]),
        direction="maximize",
    )
    study.optimize(
        objective, n_trials=OPTIMIZATION_CONFIG["no_trials"], callbacks=[optunaCallBack]
    )
