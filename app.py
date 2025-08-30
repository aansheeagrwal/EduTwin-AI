import streamlit as st
import json
import os
import random
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, date, timedelta
from calendar import monthrange
from openai import OpenAI
from io import StringIO
import pdfplumber
from docx import Document

# ---------------------------
# OpenAI Client Setup
# ---------------------------
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# ---------------------------
# File path for student profile
# ---------------------------
PROFILE_FILE = "student_profile.json"

# ---------------------------
# Load or Initialize Profile
# ---------------------------
def load_profile():
    if os.path.exists(PROFILE_FILE):
        try:
            profile = json.load(open(PROFILE_FILE, "r", encoding="utf-8"))
        except json.JSONDecodeError:
            profile = {}
    else:
        profile = {}

    default_keys = {
        "name": "",
        "age": "",
        "interests": [],
        "skills": {},
        "progress": {},
        "last_updated": "",
        "tasks": [],
        "mood": {},
        "points": 0,
        "streak": 0,
        "last_active": datetime.now().strftime("%Y-%m-%d")
    }

    for k, v in default_keys.items():
        if k not in profile:
            profile[k] = v

    # Convert old integer skills to dict format
    for skill, val in list(profile.get("skills", {}).items()):
        if isinstance(val, int):
            profile["skills"][skill] = {"level": val, "focus_today": False}

    return profile

def save_profile(profile):
    profile["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=4)

# ---------------------------
# AI Response Function
# ---------------------------
def chat_with_ai(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful AI digital twin mentor for students."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Error contacting OpenAI API: {e}"

# ---------------------------
# Streamlit App UI
# ---------------------------
st.set_page_config(page_title="🎓 EduTwin AI", layout="wide")

# ---------------------------
# Front Landing Page
# ---------------------------
if "entered" not in st.session_state:
    st.session_state.entered = False

if not st.session_state.entered:
    st.markdown("<h1 style='text-align:center;'>🎓 Welcome to EduTwin AI</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align:center;'>Your Digital Study Twin for Skills, Learning & Motivation</h4>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>🌟 Track skills, get AI mentoring, mock interviews & gamified progress!</p>", unsafe_allow_html=True)
    if st.button("🚀 Enter Dashboard"):
        st.session_state.entered = True
    st.stop()

# ---------------------------
# Load Profile
# ---------------------------
profile = load_profile()

# ---------------------------
# Sidebar: Profile Setup & JSON Upload
# ---------------------------
st.sidebar.header("📝 Student Profile")
profile["name"] = st.sidebar.text_input("Name", profile.get("name", ""), key="sidebar_name")
profile["age"] = st.sidebar.text_input("Age", profile.get("age", ""), key="sidebar_age")
interests = st.sidebar.text_area("Interests (comma separated)", ",".join(profile.get("interests", [])), key="sidebar_interests")
profile["interests"] = [i.strip() for i in interests.split(",") if i.strip()]

# Upload JSON
st.sidebar.subheader("📂 Upload Profile JSON")
uploaded_file = st.sidebar.file_uploader("Choose JSON file", type=["json"])
if uploaded_file is not None:
    try:
        uploaded_data = json.load(uploaded_file)
        profile.update({k: uploaded_data.get(k, profile[k]) for k in profile})
        save_profile(profile)
        st.sidebar.success("✅ Profile loaded and merged successfully!")
    except Exception as e:
        st.sidebar.error(f"⚠️ Failed to load JSON: {e}")

if st.sidebar.button("Save Profile"):
    save_profile(profile)
    st.sidebar.success("✅ Profile Saved!")

# ---------------------------
# Tabs
# ---------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Profile & Skills", "Progress & Calendar", "AI Mentor", "Mock Interview", "To-Do & Mental Health"])

# ---------------------------
# Tab 1: Profile & Skills
# ---------------------------
with tab1:
    st.subheader("📊 Track Your Skills")
    skill = st.text_input("Add a Skill (e.g., Python, DBMS, Communication)", key="skill_input")
    level = st.slider("Skill Level (0 = Beginner, 10 = Expert)", 0, 10, 5, key="skill_slider")
    focus_today = st.checkbox("Focus this skill today?", key="focus_today")
    if st.button("Add/Update Skill", key="skill_add"):
        if skill.strip():
            profile["skills"][skill] = {"level": level, "focus_today": focus_today}
            save_profile(profile)
            st.success(f"✅ Skill '{skill}' updated!")

    if profile["skills"]:
        st.write("### Your Skills")
        for s, info in profile["skills"].items():
            # Ensure info is dict
            if isinstance(info, dict):
                level_val = info.get("level", 0)
                focus_today = info.get("focus_today", False)
            else:
                # Convert old integer format
                level_val = int(info)
                focus_today = False
                profile["skills"][s] = {"level": level_val, "focus_today": False}
                save_profile(profile)
            color = "green" if level_val > 7 else "orange" if level_val > 4 else "red"
            st.markdown(f"- **{s}** - Level {level_val} {'🔥' if focus_today else ''}")
            st.progress(level_val / 10)

# ---------------------------
# Tab 2: Progress & Calendar
# ---------------------------
with tab2:
    st.subheader("📈 Learning Progress")
    subject = st.text_input("Subject/Topic", key="progress_subject")
    progress = st.slider("Progress (%)", 0, 100, 50, key="progress_slider")
    if st.button("Update Progress", key="progress_btn"):
        if subject.strip():
            profile["progress"][subject] = progress
            save_profile(profile)
            st.success(f"✅ Progress for {subject} updated!")

    if profile["progress"]:
        st.write("### Current Progress")
        st.bar_chart(profile["progress"])

    # Monthly Calendar
    st.subheader("📆 Monthly Learning Calendar")
    today = date.today()
    year, month = today.year, today.month
    num_days = monthrange(year, month)[1]
    calendar_html = "<table style='border-collapse: collapse;'>"
    calendar_html += "<tr>" + "".join([f"<th style='padding:5px;border:1px solid black'>{d}</th>" for d in range(1,num_days+1)]) + "</tr><tr>"
    last_update_date = datetime.strptime(profile.get("last_updated","1900-01-01"), "%Y-%m-%d").date()
    for d in range(1, num_days+1):
        day_date = date(year, month, d)
        color = "#DDDDDD"
        if day_date < today: color = "#90EE90" if last_update_date >= day_date else "#FF7F7F"
        elif day_date == today: color = "#ADD8E6"
        calendar_html += f"<td style='padding:5px;border:1px solid black;text-align:center;background-color:{color}'>{d}</td>"
    calendar_html += "</tr></table>"
    st.markdown(calendar_html, unsafe_allow_html=True)

# ---------------------------
# Tab 3: AI Mentor + File Upload
# ---------------------------
with tab3:
    st.subheader("🤖 AI Mentor")

    # Text Q&A
    user_query = st.text_area("Ask anything (study tips, career guidance, motivation)", key="ai_query")
    tone = st.selectbox("Choose AI Tone", ["Friendly", "Professional", "Motivational"], key="ai_tone")
    if st.button("Ask AI Twin", key="ai_query_btn"):
        if user_query.strip():
            prompt = f"Tone: {tone}\nStudent asks: {user_query}\nProfile: {json.dumps(profile)}"
            ai_reply = chat_with_ai(prompt)
            st.markdown("### 🧑‍💻 AI Twin Response:")
            st.write(ai_reply)
        else:
            st.warning("⚠️ Please enter a question.")

    # File Upload + Q&A
    st.subheader("📂 Upload File for AI Assistance")
    uploaded_file = st.file_uploader("Upload PDF, DOCX, TXT, CSV, JSON", type=["pdf","docx","txt","csv","json"])
    if uploaded_file is not None:
        content_text = ""
        try:
            if uploaded_file.name.endswith(".pdf"):
                with pdfplumber.open(uploaded_file) as pdf:
                    for page in pdf.pages:
                        content_text += page.extract_text() + "\n"
            elif uploaded_file.name.endswith(".docx"):
                doc = Document(uploaded_file)
                for para in doc.paragraphs:
                    content_text += para.text + "\n"
            else:  # txt, csv, json
                content_text = uploaded_file.getvalue().decode("utf-8")
            st.success(f"✅ {uploaded_file.name} loaded. You can now ask questions about its content.")
            user_file_question = st.text_input("Ask question related to file", key="file_question")
            if st.button("Get File Answer", key="file_question_btn") and user_file_question.strip():
                file_prompt = f"File content: {content_text}\n\nStudent question: {user_file_question}"
                file_answer = chat_with_ai(file_prompt)
                st.markdown("### 📝 AI Answer:")
                st.write(file_answer)
        except Exception as e:
            st.error(f"⚠️ Could not read file: {e}")

# ---------------------------
# Tab 4: Mock Interview
# ---------------------------
with tab4:
    st.subheader("🎤 Daily Mock Interview (Interactive)")
    if profile["skills"]:
        skill_for_mock = random.choice(list(profile["skills"].keys()))
        skill_level = profile["skills"][skill_for_mock]["level"]

        if "mock_questions" not in st.session_state or not st.session_state.mock_questions:
            prompt = f"Generate 3 detailed mock interview questions for a student with skill in '{skill_for_mock}' at level {skill_level} (0=Beginner, 10=Expert). Return plain text, one per line."
            ai_response = chat_with_ai(prompt)
            questions_list = [q.strip() for q in ai_response.split("\n") if q.strip()]
            st.session_state.mock_questions = questions_list
            st.session_state.mock_answers = [""] * len(questions_list)
            st.session_state.mock_feedback = [""] * len(questions_list)
            st.session_state.current_question_index = 0

        current_index = st.session_state.current_question_index
        if current_index < len(st.session_state.mock_questions):
            st.markdown(f"**Question {current_index+1}:** {st.session_state.mock_questions[current_index]}")
            st.session_state.mock_answers[current_index] = st.text_area(
                "Your Answer", st.session_state.mock_answers[current_index], key=f"answer_{current_index}"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Next Question", key=f"next_{current_index}"):
                    st.session_state.current_question_index += 1
            with col2:
                if st.button("Get AI Feedback", key=f"feedback_{current_index}"):
                    answer = st.session_state.mock_answers[current_index]
                    if answer.strip():
                        feedback_prompt = f"Student answer: {answer}\nQuestion: {st.session_state.mock_questions[current_index]}\nProvide constructive feedback and improvement tips."
                        feedback = chat_with_ai(feedback_prompt)
                        st.session_state.mock_feedback[current_index] = feedback
            if st.session_state.mock_feedback[current_index]:
                st.markdown("**AI Feedback:**")
                st.write(st.session_state.mock_feedback[current_index])
        else:
            st.success("✅ Completed all mock interview questions for today!")
            st.session_state.mock_questions = []
            st.session_state.mock_answers = []
            st.session_state.mock_feedback = []
            st.session_state.current_question_index = 0
    else:
        st.info("Add skills to generate interactive mock interview questions.")

# ---------------------------
# Tab 5: To-Do & Mental Health
# ---------------------------
with tab5:
    st.subheader("📝 To-Do & Mood Tracker")

    # Add a new task
    new_task = st.text_input("Add a new task", key="new_task")
    task_points = st.slider("Assign points for this task", 1, 10, 5, key="task_points")
    if st.button("Add Task", key="add_task_btn"):
        if new_task.strip():
            profile["tasks"].append({"task": new_task.strip(), "done": False, "points": task_points})
            save_profile(profile)
            st.success(f"✅ Task added: {new_task} ({task_points} pts)")

    # Display tasks
    if profile["tasks"]:
        st.write("### Your Tasks")
        remove_indices = []
        for i, t in enumerate(profile["tasks"]):
            col1, col2 = st.columns([6,1])
            with col1:
                profile["tasks"][i]["done"] = st.checkbox(f"{t['task']} ({t['points']} pts)", value=t.get("done", False), key=f"task_{i}")
            with col2:
                if st.button("❌", key=f"del_{i}"):
                    remove_indices.append(i)
        for idx in sorted(remove_indices, reverse=True):
            profile["tasks"].pop(idx)
            save_profile(profile)
            st.experimental_rerun()

    # Mood Tracker
    st.subheader("💖 Mood & Mental Health")
    mood_today = st.radio("How do you feel right now?", ["😊 Good", "😐 Okay", "😔 Bad"], key="mood_radio")
    if st.button("Record Mood", key="record_mood"):
        today_str = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%H:%M")
        if "mood" not in profile:
            profile["mood"] = {}
        if today_str not in profile["mood"]:
            profile["mood"][today_str] = []
        profile["mood"][today_str].append({"time": time_str, "mood": mood_today})
        save_profile(profile)
        st.success(f"Mood recorded: {mood_today} at {time_str}")

    # Gamification: Points & Streak
    today = datetime.now().date()
    last_active_date = datetime.strptime(profile.get("last_active", today.strftime("%Y-%m-%d")), "%Y-%m-%d").date()
    completed_points = sum(t["points"] for t in profile["tasks"] if t.get("done", False))
    profile["points"] += completed_points
    today_moods = profile.get("mood", {}).get(today.strftime("%Y-%m-%d"), [])
    profile["points"] += sum(1 for m in today_moods if m["mood"]=="😊 Good")
    profile["last_active"] = today.strftime("%Y-%m-%d")
    save_profile(profile)

    # Dashboard
    st.subheader("🏆 Gamification Dashboard")
    st.metric("Total Points", profile["points"])
    st.metric("Current Streak (days)", profile["streak"])
    st.metric("Level", profile["points"] // 50)

    # Weekly Points Graph
    dates = sorted(profile.get("mood", {}).keys())[-7:]
    weekly_points = []
    for d in dates:
        task_points_day = sum(t["points"] for t in profile["tasks"] if t.get("done", False))
        mood_points_day = sum(1 for m in profile["mood"].get(d, []) if m["mood"]=="😊 Good")
        weekly_points.append(task_points_day + mood_points_day)
    if weekly_points:
        df_week = pd.DataFrame({"Date": dates, "Points": weekly_points})
        st.bar_chart(df_week.set_index("Date"))

    # Option to view mood history
    if st.checkbox("Show Mood History", key="show_mood_hist"):
        st.write("### Mood History")
        for d in sorted(profile.get("mood", {}).keys(), reverse=True):
            st.write(f"**{d}**")
            for entry in profile["mood"][d]:
                st.write(f"{entry['time']}: {entry['mood']}")
