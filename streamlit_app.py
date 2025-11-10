import streamlit as st
import numpy as np
import pandas as pd
import random
import os
from datetime import datetime
import pytz

# ==========================
# --- CONFIGURATION ---
# ==========================

st.set_page_config(page_title="NBA AI Prediction Dashboard", layout="wide")
EST = pytz.timezone("US/Eastern")
N_SIM = 1000000
DATA_FILE = "nba_predictions.csv"

# ==========================
# --- STYLES ---
# ==========================

st.markdown("""
    <style>
    body {background-color: #0A0E17; color: #E0E6F8;}
    .title {font-size: 2.5em; font-weight: 800; color: #00FFAE; margin-bottom: 10px;}
    .subtext {color: #9DAAF2; font-size: 1.1em; margin-bottom: 25px;}
    .category-title {font-size: 1.5em; font-weight: 700; color: #00C896; margin-top: 25px;}
    .gold-glow {color:#FFD700;text-shadow:0 0 10px #FFD700;}
    </style>
""", unsafe_allow_html=True)

# ==========================
# --- MOCK FUNCTIONS (Replace these with your actual model logic) ---
# ==========================

def fetch_live_odds():
    """Mocked live odds data for demonstration purposes."""
    return [
        {"home_team": "Detroit Pistons", "away_team": "Utah Jazz",
         "bookmakers": [{"markets": [
             {"key": "h2h", "outcomes": [{"price": -180}, {"price": 160}]},
             {"key": "spreads", "outcomes": [{"point": -6.5}]},
             {"key": "totals", "outcomes": [{"point": 224.5}]}
         ]}]},
        {"home_team": "Miami Heat", "away_team": "Boston Celtics",
         "bookmakers": [{"markets": [
             {"key": "h2h", "outcomes": [{"price": 120}, {"price": -140}]},
             {"key": "spreads", "outcomes": [{"point": +3.5}]},
             {"key": "totals", "outcomes": [{"point": 229.5}]}
         ]}]}
    ]

def logo(team):
    """Return ESPN logo for team (mocked)."""
    key = team.lower().split()[0][:3]
    return f"https://a.espncdn.com/i/teamlogos/nba/500/{key}.png"

def american_to_prob(odds):
    """Convert American odds to implied probability."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def monte_carlo_spread(spread):
    """Simulate spread results."""
    conf = random.uniform(50, 90)
    return ("Home to Cover" if conf > 55 else "Away to Cover", conf)

def monte_carlo_total(total):
    """Simulate total points results."""
    conf = random.uniform(50, 85)
    return ("Over" if conf > 52 else "Under", conf)

def progress_bar(conf):
    """Render a clean progress bar."""
    fill = int(conf)
    return f"""
    <div style='background:#1C2541;border-radius:8px;height:8px;margin:4px 0;'>
        <div style='background:#00FFAE;height:8px;width:{fill}%;border-radius:8px;'></div>
    </div>
    """

# ==========================
# --- SAFE IMAGE HANDLER ---
# ==========================

def safe_image(url, width, fallback_text="🏀"):
    """Displays safe team logos or fallback icons."""
    if not url or str(url).strip() in ["", "0", "None"]:
        st.markdown(
            f"""
            <div style='width:{width}px;height:{width}px;
            display:flex;align-items:center;justify-content:center;
            background:#1C2541;color:#00FFAE;font-size:{width//2}px;
            border-radius:50%;box-shadow:0 0 10px rgba(0,0,0,0.4);'>
            {fallback_text}
            </div>
            """, unsafe_allow_html=True
        )
        return
    try:
        st.image(url, width=width)
    except Exception:
        st.markdown(
            f"""
            <div style='width:{width}px;height:{width}px;
            display:flex;align-items:center;justify-content:center;
            background:#1C2541;color:#00FFAE;font-size:{width//2}px;
            border-radius:50%;box-shadow:0 0 10px rgba(0,0,0,0.4);'>
            {fallback_text}
            </div>
            """, unsafe_allow_html=True
        )

# ==========================
# --- MAIN TABS ---
# ==========================

tab1, tab2, tab3, tab4 = st.tabs(["🏀 Top Predictions", "📊 Daily NBA Predictions", "🧠 Prediction History", "✅ Recent Wins"])

# ==========================
# --- TOP PREDICTIONS TAB ---
# ==========================

with tab1:
    st.markdown(f"<div class='title'>🏀 Top Predictions for {datetime.now(EST).strftime('%m/%d/%Y')}</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtext'>Best AI Monte Carlo picks with confidence ratings</div>", unsafe_allow_html=True)

    games = fetch_live_odds()
    top_ml, top_sp, top_tot = [], [], []

    for game in games:
        bookmaker = game["bookmakers"][0]
        home, away = game["home_team"], game["away_team"]
        h2h = next((m for m in bookmaker["markets"] if m["key"] == "h2h"), None)
        spreads = next((m for m in bookmaker["markets"] if m["key"] == "spreads"), None)
        totals = next((m for m in bookmaker["markets"] if m["key"] == "totals"), None)
        if not h2h or not spreads or not totals:
            continue

        home_odds, away_odds = h2h["outcomes"][0]["price"], h2h["outcomes"][1]["price"]
        spread, total = spreads["outcomes"][0]["point"], totals["outcomes"][0]["point"]

        home_prob = american_to_prob(home_odds)
        away_prob = american_to_prob(away_odds)
        draws = np.random.rand(N_SIM)
        home_wins = np.sum(draws < home_prob / (home_prob + away_prob))
        ml_conf = round((home_wins / N_SIM) * 100, 2)
        ml_pred = "Home" if ml_conf >= 50 else "Away"

        sp_pred, sp_conf = monte_carlo_spread(spread)
        tot_pred, tot_conf = monte_carlo_total(total)

        top_ml.append((home, away, ml_pred, ml_conf, home_odds, away_odds))
        top_sp.append((home, away, sp_pred, sp_conf, spread))
        top_tot.append((home, away, tot_pred, tot_conf, total))

    def show_top(title, data, metric_label):
        st.markdown(f"<div class='category-title'>{title}</div>", unsafe_allow_html=True)
        for i, (home, away, pred, conf, *extra) in enumerate(sorted(data, key=lambda x: x[3], reverse=True)[:3], start=1):
            team = home if pred == "Home" else away
            col1, col2 = st.columns([1, 4])
            with col1:
                rank_style = "gold-glow" if i == 1 else "color:#00C896;"
                st.markdown(f"<h1 style='{rank_style}'>{i}</h1>", unsafe_allow_html=True)
                safe_image(logo(team), 110, fallback_text="🏀")
            with col2:
                st.markdown(f"""
                    <b style='font-size:1.3em;'>{team}</b><br>
                    <span style='color:#9DAAF2'>{metric_label}: {extra[0]}</span><br>
                    <b style='color:#00FFAE;'>Confidence: {conf}%</b><br>
                """, unsafe_allow_html=True)
                st.markdown(progress_bar(conf), unsafe_allow_html=True)
            st.markdown("<hr style='border:1px solid #1C2541;'>", unsafe_allow_html=True)

    show_top("🏆 Top 3 Moneyline Predictions", top_ml, "Odds")
    show_top("📈 Top 3 Spread Predictions", top_sp, "Spread")
    show_top("🔥 Top 3 Total (O/U) Predictions", top_tot, "Total")

# ==========================
# --- RECENT WINS TAB ---
# ==========================

with tab4:
    st.markdown("<div class='title'>✅ Recent Wins & Accuracy</div>", unsafe_allow_html=True)
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["date", "home_team", "away_team", "moneyline_result", "spread_result", "total_result"])
        df.to_csv(DATA_FILE, index=False)

    df = pd.read_csv(DATA_FILE)

    # Add missing columns to prevent KeyError
    expected_cols = ["moneyline_result", "spread_result", "total_result"]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    correct_ml = np.sum(df["moneyline_result"] == "win")
    correct_sp = np.sum(df["spread_result"] == "win")
    correct_tot = np.sum(df["total_result"] == "win")

    total_preds = len(df)
    ml_acc = round((correct_ml / total_preds) * 100, 2) if total_preds else 0
    sp_acc = round((correct_sp / total_preds) * 100, 2) if total_preds else 0
    tot_acc = round((correct_tot / total_preds) * 100, 2) if total_preds else 0

    st.markdown(f"""
        <div style='font-size:1.3em;color:#00FFAE;'>
        🏆 <b>Moneyline Accuracy:</b> {ml_acc}%<br>
        🧩 <b>Spread Accuracy:</b> {sp_acc}%<br>
        🔥 <b>Total (O/U) Accuracy:</b> {tot_acc}%
        </div>
    """, unsafe_allow_html=True)

    if total_preds:
        st.markdown("### 📜 Historical Prediction Results")
        st.dataframe(df.tail(25), use_container_width=True)
    else:
        st.info("No prediction history available yet. Once games conclude, results will appear here.")
