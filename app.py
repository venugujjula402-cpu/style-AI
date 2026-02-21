import streamlit as st
import google.generativeai as genai
import os
import json
import sqlite3
from datetime import datetime
from PIL import Image
from dotenv import load_dotenv

# ==============================
# CONFIGURATION
# ==============================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    st.error("Please add GEMINI_API_KEY in .env file")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

st.set_page_config(
    page_title="StyleSense",
    page_icon="👗",
    layout="wide"
)

# ==============================
# DATABASE SETUP
# ==============================

conn = sqlite3.connect("stylesense.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    gender TEXT,
    age INTEGER,
    body_type TEXT,
    preferences TEXT,
    colors TEXT,
    budget TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS favorites(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    outfit TEXT,
    created_at TEXT
)
""")

conn.commit()

# ==============================
# UTILITY FUNCTIONS
# ==============================

def register_user(username, password):
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?,?)",
                       (username, password))
        conn.commit()
        return True
    except:
        return False


def login_user(username, password):
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?",
                   (username, password))
    return cursor.fetchone()


def save_favorite(username, outfit):
    cursor.execute("INSERT INTO favorites (username, outfit, created_at) VALUES (?,?,?)",
                   (username, outfit, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()


def get_favorites(username):
    cursor.execute("SELECT outfit, created_at FROM favorites WHERE username=?",
                   (username,))
    return cursor.fetchall()


# ==============================
# GEMINI PROMPTS
# ==============================

def generate_recommendation(profile, occasion, weather):
    prompt = f"""
You are a professional AI Fashion Stylist.

User Profile:
Gender: {profile['gender']}
Age: {profile['age']}
Body Type: {profile['body_type']}
Style Preference: {profile['preferences']}
Favorite Colors: {profile['colors']}
Budget: {profile['budget']}

Occasion: {occasion}
Weather: {weather}

Provide:
1. 3 Outfit Suggestions
2. Color combinations
3. Accessories recommendation
4. Styling tips
5. Explain WHY these outfits suit the user
Make it modern, trendy and practical.
"""

    response = model.generate_content(prompt)
    return response.text


def generate_trends():
    prompt = """
Generate latest global fashion trends for 2026.
Include:
- Trending colors
- Popular fabrics
- Streetwear trends
- Formal trends
Keep it short and modern.
"""
    return model.generate_content(prompt).text


def fashion_chatbot(user_message, profile):
    prompt = f"""
You are StyleSense AI fashion assistant.

User Profile:
Gender: {profile.get('gender')}
Age: {profile.get('age')}
Body Type: {profile.get('body_type')}
Preferences: {profile.get('preferences')}

User Question:
{user_message}

Provide helpful, trendy, personalized styling advice.
"""

    return model.generate_content(prompt).text


# ==============================
# SESSION STATE
# ==============================

if "user" not in st.session_state:
    st.session_state.user = None

if "profile" not in st.session_state:
    st.session_state.profile = {}

# ==============================
# LANDING PAGE
# ==============================

if not st.session_state.user:
    st.title("👗 StyleSense")
    st.subheader("Generative AI–Powered Fashion Recommendation System")

    menu = st.sidebar.selectbox("Menu", ["Login", "Register"])

    if menu == "Register":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Register"):
            if register_user(username, password):
                st.success("Account Created! Please login.")
            else:
                st.error("Username already exists.")

    if menu == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            user = login_user(username, password)
            if user:
                st.session_state.user = username
                st.success("Login Successful")
                st.rerun()
            else:
                st.error("Invalid Credentials")

# ==============================
# DASHBOARD
# ==============================

else:
    st.sidebar.title(f"Welcome {st.session_state.user}")

    page = st.sidebar.selectbox(
        "Navigation",
        ["Dashboard", "Upload & Recommendation", "Saved Outfits", "Trend Insights", "AI Chat Assistant", "Logout"]
    )

    if page == "Logout":
        st.session_state.user = None
        st.rerun()

    if page == "Dashboard":
        st.title("👤 User Profile")

        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        age = st.number_input("Age", 10, 100)
        body_type = st.selectbox("Body Type", ["Slim", "Athletic", "Curvy", "Plus Size"])
        preferences = st.multiselect("Fashion Preferences",
                                      ["Casual", "Formal", "Streetwear", "Ethnic", "Minimalist"])
        colors = st.text_input("Favorite Colors")
        budget = st.selectbox("Budget", ["Low", "Medium", "High"])

        if st.button("Save Profile"):
            st.session_state.profile = {
                "gender": gender,
                "age": age,
                "body_type": body_type,
                "preferences": preferences,
                "colors": colors,
                "budget": budget
            }
            st.success("Profile Saved Successfully!")

    # ==========================
    # RECOMMENDATION PAGE
    # ==========================

    if page == "Upload & Recommendation":
        st.title("🧠 AI Fashion Recommendations")

        occasion = st.selectbox("Occasion",
                                ["Party", "Office", "Wedding", "Travel", "Casual Day Out"])
        weather = st.selectbox("Weather",
                               ["Sunny", "Rainy", "Cold", "Hot", "Cloudy"])

        uploaded_file = st.file_uploader("Upload Outfit Image (Optional)", type=["jpg", "png", "jpeg"])

        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image", use_column_width=True)

        if st.button("Generate Recommendations"):
            if not st.session_state.profile:
                st.error("Please fill your profile first.")
            else:
                with st.spinner("Generating AI Recommendations..."):
                    result = generate_recommendation(
                        st.session_state.profile,
                        occasion,
                        weather
                    )
                st.markdown(result)

                if st.button("Save This Recommendation"):
                    save_favorite(st.session_state.user, result)
                    st.success("Saved to Favorites!")

    # ==========================
    # SAVED OUTFITS
    # ==========================

    if page == "Saved Outfits":
        st.title("💖 Saved Outfits")

        favorites = get_favorites(st.session_state.user)
        for outfit, date in favorites:
            st.markdown(f"### 🗓 {date}")
            st.markdown(outfit)
            st.divider()

    # ==========================
    # TREND INSIGHTS
    # ==========================

    if page == "Trend Insights":
        st.title("📈 AI Trend Insights")

        if st.button("Generate Trends"):
            with st.spinner("Analyzing Global Fashion Trends..."):
                trends = generate_trends()
            st.markdown(trends)

    # ==========================
    # CHAT ASSISTANT
    # ==========================

    if page == "AI Chat Assistant":
        st.title("💬 StyleSense AI Assistant")

        user_message = st.text_input("Ask your styling question")

        if st.button("Ask"):
            if not st.session_state.profile:
                st.error("Please complete profile first.")
            else:
                with st.spinner("Thinking..."):
                    reply = fashion_chatbot(
                        user_message,
                        st.session_state.profile
                    )
                st.markdown(reply)