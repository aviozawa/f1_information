# app.py (V2.5 - google-genai 対応 完全版)
import streamlit as st
import sys
import os
import pandas as pd
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import seaborn as sns
from urllib.parse import quote

# 新 SDK
from google import genai
from google.genai.types import Tool, GoogleSearch, HarmCategory, HarmBlockThreshold, GenerateContentConfig

# ----------------------------------------------------------------
# 準備：モジュールとAPIキー
# ----------------------------------------------------------------
app_dir = os.path.dirname(os.path.abspath(__file__))
project_root = app_dir
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.append(src_path)

from data_fetcher import fetch_and_save_laps, get_race_results, get_race_control_messages
from analysis import calculate_degradation_per_stint, calculate_theoretical_best_lap

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("APIキーが.envファイルに設定されていません。")

# ----------------------------------------------------------------
# Streamlit UI
# ----------------------------------------------------------------
st.set_page_config(page_title="F1 Pit Optimizer", page_icon="🏎️", layout="wide")
st.title("F1 Pit Optimizer 🏎️ V2.5")
st.write("FastF1データとGemini 2.5 Flash (with Google Search) を統合した、対話型F1レースエンジニアAI")

with st.sidebar:
    st.header("ステップ1: データ取得")
    year_input = st.number_input("レース開催年", min_value=2018, max_value=2024, value=2021)
    gp_name_input = st.text_input("グランプリ名 (英語)", value="Abu Dhabi")
    fetch_button = st.button("レースデータ取得", type="primary")

# --- セッションステートの初期化 ---
for key in ['laps_df', 'results_df', 'race_summary_df', 'race_events_df', 'chat_history']:
    if key not in st.session_state:
        st.session_state[key] = None

# --- データ取得処理 ---
if fetch_button:
    for key in ['laps_df', 'results_df', 'race_summary_df', 'race_events_df', 'chat_history']:
        st.session_state[key] = None

    with st.spinner(f"{year_input}年 {gp_name_input}GPのデータを取得中..."):
        try:
            fetch_and_save_laps(year=year_input, gp_name=gp_name_input)
            st.session_state.race_summary_df = get_race_results(year=year_input, gp_name=gp_name_input)
            st.session_state.race_events_df = get_race_control_messages(year=year_input, gp_name=gp_name_input)

            safe_gp_name = gp_name_input.lower().replace(" ", "_")
            file_path = os.path.join(project_root, 'data', f'{year_input}_{safe_gp_name}_r_laps.csv')
            if os.path.exists(file_path):
                st.session_state.laps_df = pd.read_csv(file_path)
                st.success("全てのレースデータの取得と読み込みに成功しました！")
            else:
                st.error("ラップデータのCSV読み込みに失敗しました。")
        except Exception as e:
            st.error(f"データ取得中にエラーが発生しました: {e}")

# --- 1. レースサマリーとイベント表示 ---
if st.session_state.laps_df is not None:
    st.header(f"🏁 {year_input} {gp_name_input} GP - レース概要")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("最終結果")
        if st.session_state.race_summary_df is not None:
            query = f"Race Highlights | {year_input} {gp_name_input} Grand Prix"
            encoded_query = quote(query)
            youtube_url = f"https://www.youtube.com/results?search_query={encoded_query}"
            st.markdown(f"[🎥 **このレースの公式ハイライトをYouTubeで見る**]({youtube_url})")
            st.dataframe(st.session_state.race_summary_df)
        else:
            st.warning("最終結果データを取得できませんでした。")

    with col2:
        st.subheader("主なレースイベント (SC/VSC/赤旗)")
        if st.session_state.race_events_df is not None and not st.session_state.race_events_df.empty:
            st.dataframe(st.session_state.race_events_df)
        else:
            st.info("このレースでは、主要なイベント（SC等）は記録されていませんでした。")

    st.divider()

    # --- 2. ドライバーパフォーマンス分析 ---
    st.header("ステップ2: ドライバーパフォーマンス分析")
    drivers = sorted(st.session_state.laps_df['Driver'].unique())
    selected_drivers = st.multiselect("分析したいドライバーを選択", options=drivers, default=drivers[:2])
    analysis_button = st.button("分析を実行", type="primary")

    if analysis_button and selected_drivers:
        with st.spinner("分析を実行中..."):
            results = []
            for driver in selected_drivers:
                stints = sorted(st.session_state.laps_df[st.session_state.laps_df['Driver'] == driver]['Stint'].unique())
                for stint_num in stints:
                    stint_laps = st.session_state.laps_df[
                        (st.session_state.laps_df['Driver'] == driver) &
                        (st.session_state.laps_df['Stint'] == stint_num)
                    ]
                    degradation = calculate_degradation_per_stint(st.session_state.laps_df, driver, stint_num)
                    theoretical_best = calculate_theoretical_best_lap(stint_laps)
                    if pd.notna(degradation) and pd.notna(theoretical_best):
                        results.append({
                            "Driver": driver,
                            "Stint": int(stint_num),
                            "Compound": stint_laps['Compound'].iloc[0],
                            "Degradation (s/lap)": degradation,
                            "Theoretical Best (s)": theoretical_best,
                            "Laps": len(stint_laps[stint_laps['IsAccurate'] == True])
                        })
            if results:
                st.session_state.results_df = pd.DataFrame(results)
                st.success("分析が完了しました！")
            else:
                st.warning("分析可能なデータが見つかりませんでした。")

# --- 分析結果表示 ---
if st.session_state.results_df is not None:
    st.subheader("分析結果（数値）")
    st.dataframe(st.session_state.results_df.style.format({'Degradation (s/lap)': '{:.4f}', 'Theoretical Best (s)': '{:.3f}'}))

    st.subheader("分析結果（グラフ）")
    with st.spinner("グラフを描画中..."):
        plot_df = st.session_state.laps_df[
            (st.session_state.laps_df['Driver'].isin(selected_drivers)) &
            (st.session_state.laps_df['IsAccurate'] == True)
        ]
        fig, ax = plt.subplots(figsize=(15, 8))
        sns.lineplot(data=plot_df, x='LapNumber', y='LapTimeSeconds', hue='Driver', ax=ax)
        ax.set_title(f"{year_input} {gp_name_input} GP - Lap Time Comparison")
        ax.set_xlabel("Lap Number")
        ax.set_ylabel("Lap Time (seconds)")
        st.pyplot(fig)

    st.divider()

# --- 3. Gemini 2.5 Flash との対話型分析 ---
st.header("ステップ3: Gemini 2.5 Flash との対話型分析")

if "chat_history" not in st.session_state or st.session_state.chat_history is None or analysis_button:
    st.session_state.chat_history = []

    summary_text = "N/A"
    if st.session_state.race_summary_df is not None:
        summary_text = st.session_state.race_summary_df.to_markdown(index=False)
    events_text = "N/A"
    if st.session_state.race_events_df is not None and not st.session_state.race_events_df.empty:
        events_text = st.session_state.race_events_df.to_markdown(index=False)
    results_text = "N/A"
    if st.session_state.results_df is not None:
        results_text = st.session_state.results_df.to_markdown(index=False)

    system_prompt = f"""
あなたは、F1チームの非常に優秀で経験豊富なチーフ・レースストラテジストです。
これから私たちの会話では、以下のレースデータに基づいて分析と議論を行います。このデータをあなたの知識の基盤としてください。
[レース最終結果]
{summary_text}
[主なレースイベント (SC/VSCなど)]
{events_text}
[選択されたドライバーのスティント毎パフォーマンス分析]
{results_text}
"""
    st.session_state.chat_history.append({"role": "system", "content": system_prompt})
    st.session_state.chat_history.append({"role": "assistant", "content": "了解した。全データをインプットした。いつでも質問を始めてくれ。"})

# チャットUI
if prompt := st.chat_input("データとレース展開について質問してください"):
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.spinner("AIが回答を生成中..."):
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="\n".join([msg["content"] for msg in st.session_state.chat_history]),
            config=GenerateContentConfig(
                tools=[Tool(google_search=GoogleSearch())],
                safety_settings=[
                    {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
                    {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_NONE},
                    {"category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": HarmBlockThreshold.BLOCK_NONE},
                    {"category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
                ]
            )
        )

        answer = response.text
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)
