# src/analysis.py

import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np  
def calculate_degradation_per_stint(laps_df: pd.DataFrame, target_driver: str, target_stint: int) -> float: 
    """
    特定のドライバーの特定のスティントにおけるタイヤのデグラデーション（1周あたりのタイム劣化）を計算する。

    Args:
        laps_df (pd.DataFrame): レース全体のラップデータ。
        target_driver (str): 分析対象のドライバーの略称 (例: 'VER')。
        target_stint (int): 分析対象のスティント番号。

    Returns:
        float: 1周あたりの平均タイム劣化（秒）。ポジティブな値は劣化を示します。
               計算不可能な場合はNaNを返します。
    """
    # 対象ドライバーとスティントのデータを抽出
    stint_laps = laps_df[
        (laps_df['Driver'] == target_driver) &
        (laps_df['Stint'] == target_stint) &
        (laps_df['IsAccurate'] == True) # 信頼できるラップのみを対象
    ].copy()

    # 分析に十分なデータ（最低3ラップ）があるか確認
    if len(stint_laps) < 3:
        return np.nan # データが少ない場合は計算不能

    # 線形回帰モデルの準備
    # X: タイヤの年齢 (TyreLife)
    # y: ラップタイム (LapTimeSeconds)
    X = stint_laps[['TyreLife']].values
    y = stint_laps['LapTimeSeconds'].values

    # モデルを学習させる
    model = LinearRegression()
    model.fit(X, y)

    # 傾き（coef_）が1周あたりのデグラデーション率に相当する
    degradation_rate = model.coef_[0]

    return degradation_rate # 修正点3: return文を追加

# (既存の calculate_degradation_per_stint 関数の下に配置)

def calculate_theoretical_best_lap(stint_laps: pd.DataFrame) -> float:
    """
    特定のスティントのラップデータから、理論上の最速ラップタイムを推定する。
    線形回帰モデルを使い、TyreLife=0の時のラップタイムを計算する。

    Args:
        stint_laps (pd.DataFrame): 1つのスティントに絞り込んだラップデータ。

    Returns:
        float: 推定された理論上の最速ラップタイム（秒）。
               計算不可能な場合はNaNを返します。
    """
    # 信頼できるラップのみを対象にする
    accurate_laps = stint_laps[stint_laps['IsAccurate'] == True].copy()
    
    # 分析に十分なデータ（最低3ラップ）があるか確認
    if len(accurate_laps) < 3:
        return np.nan

    # 線形回帰モデルの準備
    X = accurate_laps[['TyreLife']].values
    y = accurate_laps['LapTimeSeconds'].values

    # モデルを学習させる
    model = LinearRegression()
    model.fit(X, y)

    # 切片（intercept_）がTyreLife=0の時の推定タイム、つまり理論上の最速ラップ
    theoretical_best = model.intercept_
    
    return theoretical_best

def predict_stint_time(theoretical_best: float, degradation_rate: float, start_tyre_life: int, num_laps: int) -> float:
    """
    理論上のベストタイムと劣化率を基に、将来の複数ラップの合計タイムを予測する。

    Args:
        theoretical_best (float): 理論上の最速ラップタイム。
        degradation_rate (float): 1周あたりの劣化タイム。
        start_tyre_life (int): 予測を開始する時点のタイヤ年齢。
        num_laps (int): 何周分のタイムを予測するか。

    Returns:
        float: 予測される合計ラップタイム（秒）。
    """
    total_time = 0.0
    for i in range(num_laps):
        # 現在のタイヤ年齢での劣化によるタイムロスを計算
        degradation_loss = degradation_rate * (start_tyre_life + i)
        
        # 予測ラップタイムを計算
        predicted_lap_time = theoretical_best + degradation_loss
        
        # 合計タイムに加算
        total_time += predicted_lap_time
        
    return total_time