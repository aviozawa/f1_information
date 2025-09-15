# src/data_fetcher.py (完全版)

import os
import pandas as pd
import fastf1 as ff1
import re

# ----------------------------------------------------------------
# 関数1: ラップデータを取得し、CSVに保存する
# ----------------------------------------------------------------
def fetch_and_save_laps(year: int, gp_name: str, session_identifier: str = 'R'):
    """
    指定されたレースセッションのラップデータを取得し、整形してCSVに保存する。
    """
    print(f"--- ラップデータ取得開始: {year} {gp_name} Grand Prix ({session_identifier}) ---")
    cache_dir = './cache'
    if not os.path.exists(cache_dir): os.makedirs(cache_dir)
    ff1.Cache.enable_cache(cache_dir)

    try:
        session = ff1.get_session(year, gp_name, session_identifier)
        session.load()
        laps_df = session.laps
        laps_df['LapTimeSeconds'] = laps_df['LapTime'].dt.total_seconds()
        
        columns_to_keep = ['Driver', 'LapNumber', 'LapTime', 'LapTimeSeconds', 'Compound', 'TyreLife', 'Stint', 'Position', 'IsAccurate']
        final_columns = [col for col in columns_to_keep if col in laps_df.columns]
        output_df = laps_df[final_columns]

        output_dir = './data'
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        
        safe_gp_name = gp_name.lower().replace(" ", "_")
        file_path = os.path.join(output_dir, f'{year}_{safe_gp_name}_{session_identifier.lower()}_laps.csv')
        output_df.to_csv(file_path, index=False)
        print(f"--- ラップデータ取得完了: {file_path} ---")

    except Exception as e:
        print(f"ラップデータ取得中にエラー: {e}")
        raise

# ----------------------------------------------------------------
# 関数2: レースの最終結果を取得する
# ----------------------------------------------------------------
def get_race_results(year: int, gp_name: str, session_identifier: str = 'R'):
    """
    指定されたレースセッションの最終結果を取得する。
    """
    try:
        print("--- レース結果の取得を開始 ---")
        session = ff1.get_session(year, gp_name, session_identifier)
        session.load(laps=True, telemetry=False, weather=False, messages=False)
        results = session.results
        
        if results is None or results.empty:
            print("警告: session.results から有効なデータが取得できませんでした。")
            return None

        columns_to_keep = ['Position', 'FullName', 'TeamName', 'GridPosition', 'Status', 'Points']
        if 'FullName' not in results.columns:
            columns_to_keep[1] = 'BroadcastName'
        final_columns = [col for col in columns_to_keep if col in results.columns]
        results_df = results[final_columns].copy()
        
        results_df['Position'] = pd.to_numeric(results_df['Position'], errors='coerce').fillna(0).astype(int)
        print("--- レース結果の取得成功 ---")
        return results_df.sort_values(by='Position')

    except Exception as e:
        print(f"レース結果の取得中にエラー: {e}")
        return None

# ----------------------------------------------------------------
# 関数3: レースコントロールメッセージ（SC等）を取得する
# ----------------------------------------------------------------
def get_race_control_messages(year: int, gp_name: str, session_identifier: str = 'R'):
    """
    レースコントロールメッセージ（SC, VSC, 赤旗など）を取得し、要約する。
    """
    try:
        print("--- レースコントロールメッセージの取得を開始 ---")
        session = ff1.get_session(year, gp_name, session_identifier)
        session.load(messages=True, laps=False, telemetry=False, weather=False)
        
        rc_messages = session.race_control_messages
        keywords = ['SAFETY CAR', 'VIRTUAL SAFETY CAR', 'RED FLAG']
        
        important_messages = []
        for index, row in rc_messages.iterrows():
            lap_number = row.get('Lap', 'N/A')
            if any(keyword in row['Message'] for keyword in keywords):
                important_messages.append({'Lap': lap_number, 'Message': row['Message']})

        if not important_messages:
            print("重要なレースコントロールメッセージは見つかりませんでした。")
            return pd.DataFrame(columns=['Lap', 'Message']) # 空のDataFrameを返す
        
        print("--- 重要なレースコントロールメッセージの取得成功 ---")
        return pd.DataFrame(important_messages)

    except Exception as e:
        print(f"レースコントロールメッセージの取得中にエラー: {e}")
        return None