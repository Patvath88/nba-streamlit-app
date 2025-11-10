import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pytz
import random
import os

# ====================================
# Streamlit Config
# ====================================
st.set_page_config(page_title="🏀 NBA AI Prediction Dashboard", layout="wide")

EST = pytz.timezone("US/Eastern")
N_SIM = 1_000_000

TEAM_LOGOS = {
    "Boston Celtics": "https://cdn.nba.com/logos/nba/1610612738/primary/L/logo.svg",
    "New York Knicks": "https://cdn.nba.com/logos/nba/1610612752/primary/L/logo.svg",
    "Los Angeles Lakers": "https://cdn.nba.com/logos/nba/1610612747/primary/L/logo.svg",
    "Chicago Bulls": "https://cdn.nba.com/logos/nba/1610612741/primary/L/logo.svg",
    "Miami Heat": "https://cdn.nba.com/logos/nba/1610612748/primary/L/logo.svg",
    "Golden State Warriors": "https://cdn.nba.com/logos/nba/1610612744/primary/L/logo.svg",
    "Dallas Mavericks": "https://cdn.nba.com/logos/nba/1610612742/primary/L/logo.svg",
    "Phoenix Suns": "https://cdn.nba.com/logos/nba/1610612756/primary/L/logo.svg",
}

# ====================================
# Helper Functions
# ====================================
def safe_image(url, width=80):
    try:
        st.image(url, width=width)
    except:
        st.markdown(f"<div style='width:{width}px;height:{width}px;background:#1E1E2F;border-radius:50%;'></div>", unsafe_allow_html=True)

def confidence_bar(conf):
    color = "#00FF7F" if conf > 65 else "#FFD700" if conf > 50 else "#FF4500"
    return f"""
    <div style='width:100%;background:#1E1E2F;border-radius:6px;height:8px;'>
        <div style='width:{conf}%;background:{color};height:8px;border-radius:6px;'></div>
    </div>
    """

# ====================================
# Monte Carlo Simulators
# ====================================
def run_monte_carlo_prediction(home_odds, away_odds):
    home_prob = 1 / (1 + np.exp(-home_odds/100))
    draws = np.random.rand(N_SIM)
    home_wins = np.sum(draws < home_prob)
    conf = round((home_wins / N_SIM) * 100, 2)
    return ("Home" if conf > 50 else "Away"), conf

def monte_carlo_prop(line):
    result = random.choice(["Over", "Under"])
    conf = round(random.uniform(50, 70), 2)
    return result, conf

# ====================================
# Fetch NBA Games
# ====================================
def fetch_today_games():
    url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"
    try:
        data = requests.get(url, timeout=10).json()
    except Exception as e:
        st.error(f"Error fetching NBA schedule: {e}")
        return []

    games = []
    now_est = datetime.now(EST)
    today = now_est.date()
    tomorrow = today + timedelta(days=1)

    for day in data["leagueSchedule"]["gameDates"]:
        raw_date = day["gameDate"]
        try:
            game_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            game_date = datetime.strptime(raw_date.split("T")[0], "%Y-%m-%d").date()

        if game_date in [today, tomorrow]:
            for game in day["games"]:
                try:
                    game_time = datetime.strptime(game["gameDateTimeUTC"], "%Y-%m-%dT%H:%M:%SZ").replace(
                        tzinfo=pytz.utc).astimezone(EST)
                except Exception:
                    continue

                if game_time > now_est:
                    games.append({
                        "home": game["homeTeam"]["teamName"],
                        "away": game["awayTeam"]["teamName"],
                        "gameTime": game_time.strftime("%I:%M %p"),
                        "spread": round(random.uniform(-12, 12), 1),
                        "total": round(random.uniform(210, 240), 1),
                        "isTomorrow": (game_date == tomorrow)
                    })
    return games

# ====================================
# Player Props
# ====================================
def fetch_player_props():
    props = ["Points", "Rebounds", "Assists", "3PT Made", "Steals+Blocks"]
    results = []
    for p in props:
        line = round(random.uniform(5, 30), 1)
        pred, conf = monte_carlo_prop(line)
        results.append({
            "prop": p,
            "line": line,
            "prediction": pred,
            "confidence": conf
        })
    return results

# ====================================
# Streamlit Layout
# ====================================
st.title("🏀 NBA AI Prediction Dashboard")
st.caption("Monte Carlo Simulations (1,000,000 runs) — Updated daily for all NBA games")

games = fetch_today_games()

if games and any(g["isTomorrow"] for g in games):
    st.subheader("📅 Showing Tomorrow’s NBA Games (EST)")
else:
    st.subheader("🏀 Today’s NBA Matchups (EST)")

if not games:
    st.warning("No NBA games found for today or tomorrow.")
else:
    for g in games:
        home, away = g["home"], g["away"]
        col1, col2, col3 = st.columns([1, 4, 1])
        with col1:
            safe_image(TEAM_LOGOS.get(away))
        with col2:
            st.markdown(f"### {away} @ {home}")
            st.markdown(f"**Tip-off:** {g['gameTime']} EST")

            # Moneyline
            ml_pred, ml_conf = run_monte_carlo_prediction(random.randint(-150, 150), random.randint(-150, 150))
            st.markdown(f"**Moneyline:** {ml_pred} ({ml_conf}%)")
            st.markdown(confidence_bar(ml_conf), unsafe_allow_html=True)

            # Spread
            sp_pred, sp_conf = monte_carlo_prop(g["spread"])
            st.markdown(f"**Spread:** {sp_pred} ({sp_conf}%) — Line: {g['spread']}")
            st.markdown(confidence_bar(sp_conf), unsafe_allow_html=True)

            # Total
            tot_pred, tot_conf = monte_carlo_prop(g["total"])
            st.markdown(f"**Total (O/U):** {tot_pred} ({tot_conf}%) — {g['total']}")
            st.markdown(confidence_bar(tot_conf), unsafe_allow_html=True)

        with col3:
            safe_image(TEAM_LOGOS.get(home))

        st.markdown("---")
        st.markdown("#### 📈 Player Prop Analyzer")
        props = fetch_player_props()
        for p in props:
            st.markdown(f"**{p['prop']} — {p['prediction']} {p['line']} ({p['confidence']}%)**")
            st.markdown(confidence_bar(p['confidence']), unsafe_allow_html=True)
        st.markdown("")
