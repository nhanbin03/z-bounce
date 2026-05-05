# Z-Bounce

## Trading Through Statistical Price Oscillations

> A regime-adaptive trading strategy using z-score and ADX to follow or oppose extreme price movement

## Abstract

This project develops a trading strategy for VN30 futures using rolling z-scores and the Average Directional Index (ADX).

The strategy detects when price moves far away from its recent average and decides whether to trade with or against that movement depending on market conditions. When the market shows weak trend strength, extreme price movement is treated as temporary and the strategy trades against it. When the market shows strong trend strength, extreme price movement is treated as a continuing move and the strategy trades with it.

Instead of closing positions when price returns to the average, the strategy waits until an opposite extreme signal appears. This is because returning to the average does not always mean the price movement is finished. Using an opposite signal gives clearer evidence that the previous movement has changed.

To control risk, the strategy also makes it harder to add more positions as current exposure increases, preventing excessive accumulation.

Transaction fees, contract rolling, and forced liquidation are included in the backtesting process for more realistic evaluation.

## Introduction

Price does not always move in the same way. Sometimes it moves back and forth within a range, and sometimes it moves strongly in one direction.

A trading strategy that always assumes one type of market behavior may perform poorly when the market changes.

This project builds a strategy that adjusts its behavior based on current market conditions. The strategy uses z-score to measure how far the current price is from its recent average. A large positive or negative z-score means price is at an unusual level compared to recent history. The strategy also uses ADX to measure trend strength. By combining these two indicators, the strategy can decide whether an extreme price move should be treated as a reversal opportunity or a continuation opportunity.

A key design choice is that the strategy does not close positions when price returns to the average. The average only shows balance in the middle of the price range, but it does not clearly tell whether the movement is over. Instead, the strategy waits for an opposite extreme signal, which gives stronger evidence that market direction has changed.

To reduce risk, the strategy increases the required z-score level before adding more positions when inventory becomes larger.

## Hypothesis

Large price deviations from the recent average often lead to meaningful future price movement.

However, the direction of that movement depends on market conditions.

When trend strength is weak, extreme price movement is more likely to reverse.

When trend strength is strong, extreme price movement is more likely to continue.

The strategy assumes that once a position is opened, returning to the average is not enough evidence to close it. Price may continue moving after crossing the average.

An opposite extreme signal gives stronger evidence that the previous movement has ended or changed direction.

By adapting to market conditions and using opposite signals for exits, the strategy aims to capture larger price movement more consistently.

## Trading Logic

The strategy combines z-score and ADX.

The z-score is calculated as:
$$z\text{-}score = \frac{price - MA(price)}{STD(price)}$$

where MA is the moving average and STD is the standard deviation over a rolling window.

ADX is used to determine market condition:

- ADX < 30 → weak trend
- ADX > 40 → strong trend
- 30 ≤ ADX ≤ 40 → no trade

### Weak Trend Logic

When the market trend is weak, extreme price movement is treated as temporary.

Entry rules:

- z-score < -threshold → buy
- z-score > threshold → sell

The expectation is that price will reverse.

### Strong Trend Logic

When the market trend is strong, extreme price movement is treated as continuing.

Entry rules:

- z-score > threshold → buy
- z-score < -threshold → sell

The expectation is that price will continue moving in the same direction.

### Exit Logic

Positions are closed only when an opposite extreme signal appears.

## Data

- Data source: Algotrade database
- Data asset: VN30 Futures (VN30F1M - 1-month contract)
- Data period: from 2022-01-01 to 2025-04-29
- Data frequency: 1-minute OHLC (Open, High, Low, Close) data
- Transaction fee: 0.4 / 2 per side

### Data collection

- The 1-minute price data is collected from Algotrade database
- Data is collected using the script `data_loader.py`
- Data is stored in the `data/is/` folder (in-sample) and `data/os/` folder (out-of-sample)

## Implementation

### Environment Setup

1. Set up python virtual environment

```bash
python -m venv venv
source venv/bin/activate # for Linux/MacOS
.\venv\Scripts\activate.bat # for Windows command line
.\venv\Scripts\Activate.ps1 # for Windows PowerShell
```

2. Install the required packages. This requires the paperbroker client package, which can be installed from [here](https://papertrade.algotrade.vn/static/docs/downloads/paperbroker_client-0.2.4-py3-none-any.64a14680f78f.whl).

```bash
pip install -r requirements.txt
pip install paperbroker_client-0.2.4-py3-none-any.whl
```

3. Create `.env` file in the root directory of the project and fill in the required information. The `.env` file is used to store environment variables that are used in the project. The following is an example of a `.env` file:

```env
HOST=<database_host>
PORT=<database_port>
DATABASE=<database_name>
USER_DB=<database_user>
PASSWORD=<database_password>

MARKET_REDIS_HOST=<redis_host>
MARKET_REDIS_PORT=<redis_port>
MARKET_REDIS_PASSWORD=<redis_password>

PAPERBROKER_KAFKA_BOOTSTRAP_SERVERS=<kafka_bootstrap_servers>
PAPERBROKER_KAFKA_USERNAME=<kafka_username>
PAPERBROKER_KAFKA_PASSWORD=<kafka_password>
PAPERBROKER_ENV_ID=<paperbroker_env_id>

DEFAULT_SUB_ACCOUNT=<default_sub_account>
PAPERBROKER_USERNAME=<paperbroker_username>
PAPERBROKER_PASSWORD=<paperbroker_password>
PAPERBROKER_REST_BASE_URL=<paperbroker_rest_base_url>
PAPERBROKER_SOCKET_HOST=<paperbroker_socket_host>
PAPERBROKER_SOCKET_PORT=<paperbroker_socket_port>
PAPERBROKER_SENDER_COMP_ID=<paperbroker_sender_comp_id>
PAPERBROKER_TARGET_COMP_ID=<paperbroker_target_comp_id>
```

### Data Collection

#### Option 1. Download from Google Drive

Data can be download directly from [Google Drive](https://drive.google.com/drive/folders/1R84iCUwO-t_aQxzGqmNYGrtEezPttzSK?usp=sharing). The data files are stored in the `data` folder with the following folder structure:

```
data
├── is
│   └── VN30F1M_data.csv
└── os
    └── VN30F1M_data.csv
```

You should place this folder to the current `PYTHONPATH` for the following steps.

#### Option 2. Run codes to collect data

To collect data from database, run this command below in the root directory:

```bash
python data_loader.py
```

The result will be stored in the `data/is/` and `data/os/`

### In-sample Backtesting

Specify period and parameters in `parameter/backtesting_parameter.json` file.

```bash
python backtesting.py
```

The results are stored in the `result/backtest/` folder.

### Optimization

To run the optimization, execute the command in the root folder:

```bash
python optimization.py
```

The optimization parameter are store in `parameter/optimization_parameter.json`. After optimizing, the optimized parameters are stored in `parameter/optimized_parameter.json`.

### Out-of-sample Backtesting

To run the out-of-sample backtesting results, execute this command

```bash
python evaluation.py
```

The script will get value from `parameter/optimized_parameter.json` to execute. The results are stored in the `result/optimization` folder.

### Paper Trading

Configure the paper trading parameters at the top of `paper_trading.py` file. Then, run the command below to start paper trading:

```bash
python paper_trading.py
```

## In-sample Backtesting

Running the in-sample backtesting by execute the command:

```bash
python backtesting.py
```

### Evaluation Metrics

- Backtesting results are stored in the `result/backtest/` folder.
- Used metrics:
  - Sharpe ratio (SR)
  - Sortino ratio (SoR)
  - Maximum drawdown (MDD)
- We use a risk-free rate of 6% per annum, equivalent to approximately 0.023% per day, as a benchmark for evaluating the Sharpe Ratio (SR) and Sortino Ratio (SoR).

### Parameters

### In-sample Backtesting Result

- The backtesting results are constructuted from 2022-01-01 to 2023-01-01.

```
| Metric                 | Value                              |
|------------------------|------------------------------------|
| Sharpe Ratio           | 0.3215                             |
| Sortino Ratio          | 0.4817                             |
| Maximum Drawdown (MDD) | -0.0557                            |
| HPR (%)                | 9.08                               |
| Monthly return (%)     | 0.73                               |
| Annual return (%)      | 8.19                               |
```

- The HPR chart. The chart is located at: `result/backtest/hpr.svg`
  ![HPR chart with VNINDEX benchmark](result/backtest/hpr.svg)
- Drawdown chart. The chart is located at `result/backtest/drawdown.svg`
  ![Drawdown chart](result/backtest/drawdown.svg)
- Daily inventory. The chart is located at `result/backtest/inventory.svg`
  ![Inventory chart](result/backtest/inventory.svg)

## Optimization

The strategy parameters are optimized using the in-sample data to maximize risk-adjusted returns. The configuration for optimization is stored in `parameter/optimization_parameter.json`. A random seed is used for reproducibility. The optimized parameters are stored in `parameter/optimized_parameter.json`.

The optimization process can be reproduced by executing:

```bash
python optimization.py
```

The currently found optimized parameters with seed `2025` are:

```json
{
  "window_size": 12,
  "threshold": 2.5,
  "position_scaling_factor": 0.02
}
```

## Out-of-sample Backtesting

- Specify the out-sample period and parameters in `parameter/backtesting_parameter.json` file.
- The out-sample data is loaded on the previous step. Refer to section [Data](#data) for more information.
- To evaluate the out-sample data run the command below

```bash
python evaluation.py
```

### Out-of-sample Backtesting Result

- The out-sample backtesting results are constructuted from 2024-01-02 to 2025-04-29.

```
| Metric                 | Value                              |
|------------------------|------------------------------------|
| Sharpe Ratio           | 0.4919                             |
| Sortino Ratio          | 0.8488                             |
| Maximum Drawdown (MDD) | -0.0606                            |
| HPR (%)                | 13.07                              |
| Monthly return (%)     | 0.71                               |
| Annual return (%)      | 8.11                               |
```

- The HPR chart. The chart is located at `result/optimization/hpr.svg`.
  ![HPR chart with VNINDEX benchmark](result/optimization/hpr.svg)

- Drawdown chart. The chart is located at `result/optimization/drawdown.svg`.
  ![Drawdown chart](result/optimization/drawdown.svg)
- Daily inventory. The chart is located at `result/optimization/inventory.svg`
  ![Inventory chart](result/optimization/inventory.svg)

## Paper Trading

- Configure the paper trading parameters at the top of `paper_trading.py` file. This includes the symbol, window size, z-score threshold, and position scaling factor.
- To start paper trading, run the command below:

```bash
python paper_trading.py
```

### Evaluation Metrics

Paper trading performance is evaluated using the same metrics as backtesting:

- Sharpe Ratio (SR)
- Sortino Ratio (SoR)
- Maximum Drawdown (MDD)

### Paper Trading Result

- The paper trading results are constructed from 2026-04-16 to 2026-04-29.

```
| Metric                 | Value                              |
|------------------------|------------------------------------|
| Sharpe Ratio           | 3.21                               |
| Sortino Ratio          | 0.35                               |
| Maximum Drawdown (MDD) | -0.0040                            |
| HPR (%)                | 11.40                              |
```

## Reference

[1] ALGOTRADE, Algorithmic Trading Theory and Practice - A Practical Guide with Applications on the Vietnamese Stock Market, 1st ed. DIMI BOOK, 2023, pp. 52–53. Accessed: March 3, 2026. [Online]. Available: [Link](https://hub.algotrade.vn/knowledge-hub/mean-reversion-strategy/)
