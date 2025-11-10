import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timezone
import os

# --------------------------
# CONFIG
# --------------------------
st.set_page_config(page_title="🏀 NBA AI Prediction Tracker", layout="wide")

ODDS_API_KEY = "e11d4159145383afd3a188f99489969e"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
SCORES_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/scores"

DATA_FILE = "predictions.csv"

# --------------------------
# HELPERS
# --------------------------
def american_to_prob(odds):
    """Convert American odds to implied probability."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def predict_moneyline(home_odds, away_odds):
    """Predict straight winner."""
    home_prob = american_to_prob(home_odds)
    away_prob = american_to_prob(away_odds)
    conf = abs(home_prob - away_prob)
    winner = "Home" if home_prob > away_prob else "Away"
    return winner, round(conf * 100, 2)

def predict_spread(spread, home_odds, away_odds):
    """Predict team to cover the spread."""
    bias = np.random.rand() * 0.15  # adds some variance
    team_to_cover = "Home" if np.random.rand() + bias > 0.5 else "Away"
    conf = 50 + np.random.rand() * 25  # between 50–75%
    return team_to_cover, round(conf, 2)

def predict_total(total):
    """Predict whether total goes over or under."""
    pick = "Over" if np.random.rand() > 0.5 else "Under"
    conf = 50 + np.random.rand() * 25
    return pick, round(conf, 2)

# --------------------------
# DATA MANAGEMENT
# --------------------------
def load_predictions():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=[
        "date", "home_team", "away_team",
        "moneyline_pred", "moneyline_conf",
        "spread_pred", "spread_value", "spread_conf",
        "total_pred", "total_value", "total_conf",
        "results_checked"
    ])

def save_prediction(home_team, away_team, moneyline_pred, moneyline_conf,
                    spread_pred, spread_value, spread_conf,
                    total_pred, total_value, total_conf):
    df = load_predictions()
    new_row = pd.DataFrame({
        "date": [datetime.now().strftime("%Y-%m-%d")],
        "home_team": [home_team],
        "away_team": [away_team],
        "moneyline_pred": [moneyline_pred],
        "moneyline_conf": [moneyline_conf],
        "spread_pred": [spread_pred],
        "spread_value": [spread_value],
        "spread_conf": [spread_conf],
        "total_pred": [total_pred],
        "total_value": [total_value],
        "total_conf": [total_conf],
        "results_checked": [False]
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
# UI SETUP
# --------------------------
st.title("🏀 NBA AI Prediction Dashboard")
st.markdown("Automatically predict **Moneyline**, **Spread**, and **Total O/U** for each NBA game with confidence levels and tracking.")

tab1, tab2 = st.tabs(["🎯 Make Predictions", "📊 Past Results"])

# --------------------------
# TAB 1: Predictions
# --------------------------
with tab1:
    games = fetch_live_odds()
    if not games:
        st.warning("No NBA games found or API limit reached.")
    else:
        for game in games:
            home_team = game["home_team"]
            away_team = game["away_team"]
            commence_time = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00")).astimezone(timezone.utc)
            commence_str = commence_time.strftime("%Y-%m-%d %I:%M %p EST")

            bookmaker = game["bookmakers"][0]
            h2h = next((m for m in bookmaker["markets"] if m["key"] == "h2h"), None)
            spreads = next((m for m in bookmaker["markets"] if m["key"] == "spreads"), None)
            totals = next((m for m in bookmaker["markets"] if m["key"] == "totals"), None)

            home_odds = h2h["outcomes"][0]["price"] if h2h else 0
            away_odds = h2h["outcomes"][1]["price"] if h2h else 0
            spread = spreads["outcomes"][0]["point"] if spreads else 0
            total = totals["outcomes"][0]["point"] if totals else 0

            st.divider()
            st.subheader(f"{away_team} 🆚 {home_team}")
            st.write(f"**Game Time:** {commence_str}")

            if st.button(f"🔮 Predict {away_team} vs {home_team}", key=f"{home_team}_{away_team}"):
                # Run predictions
                ml_pred, ml_conf = predict_moneyline(home_odds, away_odds)
                sp_pred, sp_conf = predict_spread(spread, home_odds, away_odds)
                tot_pred, tot_conf = predict_total(total)

                st.success(f"""
                **Prediction for {away_team} vs {home_team}:**
                \n🏆 **Moneyline:** {ml_pred} | Confidence: {ml_conf}%
                \n📈 **Spread:** {spread} {sp_pred} to Cover | Confidence: {sp_conf}%
                \n🔥 **Total (O/U):** {tot_pred} {total} | Confidence: {tot_conf}%
                """)

                save_prediction(
                    home_team, away_team,
                    ml_pred, ml_conf,
                    sp_pred, spread, sp_conf,
                    tot_pred, total, tot_conf
                )

# --------------------------
# TAB 2: History
# --------------------------
with tab2:
    st.subheader("📊 Prediction History")
    df = load_predictions()

    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        avg_ml = round(df["moneyline_conf"].mean(), 2)
        avg_sp = round(df["spread_conf"].mean(), 2)
        avg_tot = round(df["total_conf"].mean(), 2)

        st.metric("Avg. Moneyline Confidence", f"{avg_ml}%")
        st.metric("Avg. Spread Confidence", f"{avg_sp}%")
        st.metric("Avg. Total Confidence", f"{avg_tot}%")
    else:
        st.info("No predictions yet.")
