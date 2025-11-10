# -------------------------------------------------
# 🏀 NBA AI Prediction Dashboard
# -------------------------------------------------
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from nba_api.stats.endpoints import scoreboardv2
from nba_api.stats.static import teams
import requests

# -------------------------------------------------
# PAGE CONFIG & STYLE
# -------------------------------------------------
st.set_page_config(page_title="NBA AI Prediction Dashboard", page_icon="🏀", layout="wide")

st.markdown("""
    <style>
    body {background-color:#121212;color:#EAEAEA;font-family:'Roboto',sans-serif;}
    .title {font-size:36px;font-weight:700;color:#FF6F00;text-shadow:0 0 8px #FF8C00;margin-bottom:4px;}
    .subtext {font-size:16px;color:#B0B0B0;margin-bottom:25px;}
    .stAlert {background-color:#1E1E1E !important;border-radius:10px;}
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='title'>🏀 NBA AI Prediction Dashboard</div>", unsafe_allow_html=True)
st.markdown("<div class='subtext'>Monte Carlo Simulations (1,000,000 runs) — Updated daily for all NBA games</div>", unsafe_allow_html=True)

# -------------------------------------------------
# HELPERS
# -------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_today_games():
    """Fetch today's NBA games and return formatted data."""
    try:
        today = datetime.now().date()
        date_str = today.strftime("%m/%d/%Y")

        sb = scoreboardv2.ScoreboardV2(day_offset=0, league_id="00", game_date=date_str)
        games_df = sb.line_score.get_data_frame()

        games = []
        for _, g in games_df.iterrows():
            raw_date = str(g.get("GAME_DATE_EST", today))

            # --- Robust Date Parsing ---
            game_date = None
            date_formats = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S.%fZ"]
            for fmt in date_formats:
                try:
                    game_date = datetime.strptime(raw_date.split("T")[0], fmt).date()
                    break
                except Exception:
                    continue
            if game_date is None:
                try:
                    game_date = datetime.fromisoformat(raw_date.replace("Z", "")).date()
                except Exception:
                    st.warning(f"⚠️ Unrecognized date format: {raw_date}")
                    continue

            games.append({
                "game_id": g.get("GAME_ID"),
                "home_team": g.get("TEAM_ABBREVIATION") if g.get("TEAM_ID_HOME") else None,
                "visitor_team": g.get("TEAM_ABBREVIATION") if g.get("TEAM_ID_VISITOR") else None,
                "game_date": game_date
            })

        if not games:
            st.warning("No games found for today. Try again later.")
        return games

    except Exception as e:
        st.error(f"Error fetching games: {e}")
        return []

# -------------------------------------------------
# FETCH GAMES
# -------------------------------------------------
games = fetch_today_games()

if not games:
    st.info("No NBA games found for today.")
else:
    for g in games:
        st.markdown(f"### 🏆 {g['visitor_team']} @ {g['home_team']} ({g['game_date']})")

        # Placeholder Monte Carlo simulation demo
        st.write("Running AI Monte Carlo simulations... (example output below)")

        # Simulate a simple predictive distribution
        np.random.seed(42)
        pred = np.random.normal(loc=105, scale=10, size=1000000)
        mean_pred = np.mean(pred)
        prob_over_110 = np.mean(pred > 110)

        st.progress(float(prob_over_110))
        st.write(f"**Predicted Points:** {mean_pred:.2f} | **P(Over 110):** {prob_over_110*100:.1f}%")

# -------------------------------------------------
# OPTIONAL: PLAYER PROP ANALYZER
# -------------------------------------------------
st.divider()
st.subheader("📊 Player Prop Analyzer")

player = st.text_input("Search player (e.g. LeBron James)")
if player:
    st.write(f"Analyzing props for **{player}** (sample data)")
    props = pd.DataFrame({
        "Prop": ["Points", "Assists", "Rebounds", "3PT Made", "PRA"],
        "Line": [25.5, 6.5, 7.5, 2.5, 38.5],
        "Predicted": [27.1, 7.2, 8.1, 2.8, 40.5],
        "Edge": [6.3, 10.8, 8.0, 12.0, 5.2]
    })
    st.bar_chart(props.set_index("Prop")["Edge"])
    st.dataframe(props)
