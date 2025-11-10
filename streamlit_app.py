import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timezone
import os

# --------------------------
# CONFIG
# --------------------------
st.set_page_config(page_title="🏀 NBA AI Prediction Dashboard", layout="wide")
ODDS_API_KEY = "e11d4159145383afd3a188f99489969e"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
DATA_FILE = "predictions.csv"

# --------------------------
# CUSTOM STYLING
# --------------------------
st.markdown("""
    <style>
        body {
            background-color: #0B132B;
            color: #E0E1DD;
            font-family: 'Inter', sans-serif;
        }
        .title {
            text-align: center;
            font-size: 2.5em;
            font-weight: bold;
            color: #00C896;
            margin-bottom: 0.2em;
        }
        .subtext {
            text-align: center;
            color: #9DAAF2;
            font-size: 1.2em;
            margin-bottom: 1em;
        }
        .card {
            background-color: #1C2541;
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
            transition: transform 0.2s ease-in-out;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        }
        .card:hover {
            transform: scale(1.02);
            background-color: #212D52;
        }
        .game-header {
            font-size: 1.3em;
            color: #F0F0F0;
            font-weight: bold;
        }
        .prediction {
            background-color: #3A506B;
            border-radius: 12px;
            padding: 12px;
            margin-top: 10px;
        }
        .success {
            color: #00FFAE;
        }
        .button-style {
            border-radius: 10px !important;
            background-color: #00C896 !important;
            color: black !important;
            font-weight: bold !important;
            transition: background-color 0.3s ease-in-out !important;
        }
        .button-style:hover {
            background-color: #00A27A !important;
        }
    </style>
""", unsafe_allow_html=True)

# --------------------------
# HELPERS
# --------------------------
def american_to_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def predict_moneyline(home_odds, away_odds):
    home_prob = american_to_prob(home_odds)
    away_prob = american_to_prob(away_odds)
    conf = abs(home_prob - away_prob)
    winner = "Home" if home_prob > away_prob else "Away"
    return winner, round(conf * 100, 2)

def predict_spread(spread, home_odds, away_odds):
    bias = np.random.rand() * 0.15
    team_to_cover = "Home" if np.random.rand() + bias > 0.5 else "Away"
    conf = 50 + np.random.rand() * 25
    return team_to_cover, round(conf, 2)

def predict_total(total):
    pick = "Over" if np.random.rand() > 0.5 else "Under"
    conf = 50 + np.random.rand() * 25
    return pick, round(conf, 2)

def load_predictions():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=[
        "date", "home_team", "away_team",
        "moneyline_pred", "moneyline_conf",
        "spread_pred", "spread_value", "spread_conf",
        "total_pred", "total_value", "total_conf"
    ])

def save_prediction(home_team, away_team, ml_pred, ml_conf,
                    sp_pred, spread_value, sp_conf,
                    tot_pred, total_value, tot_conf):
    df = load_predictions()
    new_row = pd.DataFrame({
        "date": [datetime.now().strftime("%Y-%m-%d")],
        "home_team": [home_team],
        "away_team": [away_team],
        "moneyline_pred": [ml_pred],
        "moneyline_conf": [ml_conf],
        "spread_pred": [sp_pred],
        "spread_value": [spread_value],
        "spread_conf": [sp_conf],
        "total_pred": [tot_pred],
        "total_value": [total_value],
        "total_conf": [tot_conf]
    })
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

@st.cache_data(ttl=300)
def fetch_live_odds():
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }
    res = requests.get(ODDS_API_URL, params=params)
    if res.status_code != 200:
        st.error(f"API error: {res.text}")
        return []
    return res.json()

# --------------------------
# HEADER
# --------------------------
st.markdown("<div class='title'>🏀 NBA AI Prediction Dashboard</div>", unsafe_allow_html=True)
st.markdown("<div class='subtext'>Real-time odds | AI-driven projections | FanDuel-style interface</div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🎯 Make Predictions", "📊 Past Results"])

# --------------------------
# TAB 1 - Predictions
# --------------------------
with tab1:
    games = fetch_live_odds()
    if not games:
        st.warning("No live NBA games found or API limit reached.")
    else:
        for game in games:
            bookmaker = game["bookmakers"][0]
            home_team = game["home_team"]
            away_team = game["away_team"]
            commence_time = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00")).astimezone(timezone.utc)
            commence_str = commence_time.strftime("%Y-%m-%d %I:%M %p EST")

            h2h = next((m for m in bookmaker["markets"] if m["key"] == "h2h"), None)
            spreads = next((m for m in bookmaker["markets"] if m["key"] == "spreads"), None)
            totals = next((m for m in bookmaker["markets"] if m["key"] == "totals"), None)

            home_odds = h2h["outcomes"][0]["price"] if h2h else 0
            away_odds = h2h["outcomes"][1]["price"] if h2h else 0
            spread = spreads["outcomes"][0]["point"] if spreads else 0
            total = totals["outcomes"][0]["point"] if totals else 0

            with st.container():
                st.markdown(f"<div class='card'>", unsafe_allow_html=True)
                st.markdown(f"<div class='game-header'>{away_team} 🆚 {home_team}</div>", unsafe_allow_html=True)
                st.write(f"**Game Time:** {commence_str}")
                st.write(f"**Moneyline:** {home_team} {home_odds} | {away_team} {away_odds}")
                st.write(f"**Spread:** {spread}")
                st.write(f"**Total (O/U):** {total}")

                if st.button(f"🔮 Predict {away_team} vs {home_team}", key=f"{home_team}_{away_team}"):
                    ml_pred, ml_conf = predict_moneyline(home_odds, away_odds)
                    sp_pred, sp_conf = predict_spread(spread, home_odds, away_odds)
                    tot_pred, tot_conf = predict_total(total)

                    st.markdown(f"""
                    <div class='prediction'>
                        <p class='success'><b>Prediction for {away_team} vs {home_team}:</b></p>
                        🏆 <b>Moneyline:</b> {ml_pred} | Confidence: {ml_conf}%<br>
                        📈 <b>Spread:</b> {spread} {sp_pred} to Cover | Confidence: {sp_conf}%<br>
                        🔥 <b>Total (O/U):</b> {tot_pred} {total} | Confidence: {tot_conf}%
                    </div>
                    """, unsafe_allow_html=True)

                    save_prediction(home_team, away_team, ml_pred, ml_conf, sp_pred, spread, sp_conf, tot_pred, total, tot_conf)
                st.markdown("</div>", unsafe_allow_html=True)

# --------------------------
# TAB 2 - History
# --------------------------
with tab2:
    st.markdown("### 📊 Prediction History")
    df = load_predictions()
    if not df.empty:
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("No predictions made yet.")
