import streamlit as st
import pandas as pd
import numpy as np
import requests
import xgboost as xgb
from datetime import datetime, timezone

# --------------------------
# CONFIG
# --------------------------
st.set_page_config(page_title="🏀 NBA AI Prediction Dashboard", layout="wide")

ODDS_API_KEY = "e11d4159145383afd3a188f99489969e"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"

# --------------------------
# FETCH LIVE NBA ODDS
# --------------------------
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

games = fetch_live_odds()

# --------------------------
# LOAD OR SIMULATE MODEL
# --------------------------
def load_model():
    try:
        model = xgb.XGBClassifier()
        model.load_model("nba_xgboost.json")
        return model
    except Exception:
        # Placeholder simple model
        m = xgb.XGBClassifier()
        m.fit(np.random.rand(10, 3), np.random.randint(0, 2, 10))
        return m

model = load_model()

# --------------------------
# PREDICTION FUNCTION
# --------------------------
def predict_outcome(home_odds, away_odds, spread, total):
    # Convert odds to implied probabilities
    def american_to_prob(odds):
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    home_prob = american_to_prob(home_odds)
    away_prob = american_to_prob(away_odds)

    # Example feature vector
    X = np.array([[home_prob, away_prob, spread]])
    dmatrix = xgb.DMatrix(X)
    pred = np.random.rand()  # Simulated prediction
    return pred

# --------------------------
# FRONTEND
# --------------------------
st.title("🏀 NBA AI Prediction Dashboard")
st.markdown("Live odds, AI predictions, and confidence levels")

if not games:
    st.warning("No live NBA games or API limit reached.")
else:
    for game in games:
        home_team = game["home_team"]
        away_team = game["away_team"]
        commence_time = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00")).astimezone(timezone.utc)
        commence_str = commence_time.strftime("%Y-%m-%d %I:%M %p EST")

        h2h = next((m for m in game["bookmakers"][0]["markets"] if m["key"] == "h2h"), None)
        spreads = next((m for m in game["bookmakers"][0]["markets"] if m["key"] == "spreads"), None)
        totals = next((m for m in game["bookmakers"][0]["markets"] if m["key"] == "totals"), None)

        home_odds = h2h["outcomes"][0]["price"] if h2h else 0
        away_odds = h2h["outcomes"][1]["price"] if h2h else 0
        spread = spreads["outcomes"][0]["point"] if spreads else 0
        total = totals["outcomes"][0]["point"] if totals else 0

        st.divider()
        st.subheader(f"{away_team} 🆚 {home_team}")
        st.write(f"**Game Time:** {commence_str}")
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])

        with col1:
            st.metric(label="🏠 Home ML", value=home_odds)
        with col2:
            st.metric(label="🚀 Away ML", value=away_odds)
        with col3:
            st.metric(label="📊 Spread", value=spread)
        with col4:
            st.metric(label="🔥 Total (O/U)", value=total)

        with col5:
            if st.button(f"🔮 Predict {home_team} vs {away_team}", key=home_team):
                ai_pred = predict_outcome(home_odds, away_odds, spread, total)
                conf = round(ai_pred * 100, 2)
                winner = home_team if ai_pred > 0.5 else away_team
                st.success(f"🏆 Predicted Winner: {winner}")
                st.metric(label="AI Confidence", value=f"{conf}%")
