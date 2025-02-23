import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
import random
import os
import json

# ---------------- Firebase Initialization ----------------
import firebase_admin
from firebase_admin import credentials, db

firebase_key_json = os.getenv("FIREBASE_KEY")
if firebase_key_json:
    firebase_key = json.loads(firebase_key_json)
    cred = credentials.Certificate(firebase_key)
    # Initialize Firebase only if not already initialized
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://kavya-6ed82-default-rtdb.firebaseio.com/"
        })
else:
    st.error("Firebase key is missing. Please set the FIREBASE_KEY environment variable.")

# ---------------- Set Page Config ----------------
st.set_page_config(
    page_title="NEET Exam Prep - Subject-wise Tracker",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- Base Custom CSS ----------------
base_css = """
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"]  {
        font-family: 'Roboto', sans-serif;
    }
    .main-header {
        background: linear-gradient(135deg, #007BFF, #66B2FF);
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        color: white;
        margin-bottom: 20px;
    }
    .sidebar .sidebar-content {
        padding: 20px;
        border-radius: 8px;
    }
    .stButton>button {
        border: none;
        border-radius: 5px;
        padding: 8px 16px;
    }
    .stProgress>div>div {
        border-radius: 5px;
    }
    .dataframe-container {
        background: #ffffff;
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.1);
    }
    .section-divider {
        border: none;
        border-bottom: 1px solid #ddd;
        margin: 10px 0;
    }
    .container-box {
        background: #f9f9f9;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
    }
    /* Current time box styling */
    .current-time {
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 10000;
        background: #ffffff;
        padding: 5px 10px;
        border-radius: 5px;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.2);
        font-size: 14px;
    }
</style>
"""
st.markdown(base_css, unsafe_allow_html=True)

# ---------------- Theme CSS Function ----------------
def apply_theme_css():
    theme = st.session_state.get("app_theme", "Light Mode")
    if theme == "Dark Mode":
        css = """
        <style>
            body, .stApp { background-color: #222; color: #ddd; }
            .sidebar .sidebar-content { background-color: #333; }
            .stButton>button { background-color: #555; color: #fff; }
            .stProgress>div>div { background-color: #888; }
        </style>
        """
    elif theme == "Colorful Mode":
        css = """
        <style>
            body, .stApp { background-color: #e0f7fa; color: #212529; }
            .sidebar .sidebar-content { background-color: #b2ebf2; }
            .stButton>button { background-color: #ff4081; color: #fff; }
            .stProgress>div>div { background-color: #ff4081; }
        </style>
        """
    else:  # Light Mode
        css = """
        <style>
            body, .stApp { background-color: #F8F9FA; color: #212529; }
            .sidebar .sidebar-content { background-color: #f0f2f6; }
            .stButton>button { background-color: #007BFF; color: #fff; }
            .stProgress>div>div { background-color: #66B2FF; }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)

# ---------------- Current Date & Time in Top Right Corner ----------------
current_time = datetime.datetime.now().strftime("%d/%m/%y %I:%M:%S %p")
st.markdown(f"""
    <div class="current-time">
        <strong>{current_time}</strong>
    </div>
    """, unsafe_allow_html=True)

# ---------------- Firebase Persistence Functions ----------------
# These functions replace local file persistence.

def process_subject_data(data):
    for subject, chapters in data.items():
        for chapter in chapters:
            if isinstance(chapter.get("entry_datetime"), str):
                try:
                    chapter["entry_datetime"] = datetime.datetime.fromisoformat(chapter["entry_datetime"])
                except Exception:
                    pass
            for reminder in chapter.get("reminders", []):
                if isinstance(reminder.get("time"), str):
                    try:
                        reminder["time"] = datetime.datetime.fromisoformat(reminder["time"])
                    except Exception:
                        pass
    return data

def prepare_data_for_firebase(data):
    new_data = {}
    for subject, chapters in data.items():
        new_chapters = []
        for chapter in chapters:
            new_chapter = chapter.copy()
            if isinstance(new_chapter.get("entry_datetime"), datetime.datetime):
                new_chapter["entry_datetime"] = new_chapter["entry_datetime"].isoformat()
            new_reminders = []
            for reminder in new_chapter.get("reminders", []):
                new_reminder = reminder.copy()
                if isinstance(new_reminder.get("time"), datetime.datetime):
                    new_reminder["time"] = new_reminder["time"].isoformat()
                new_reminders.append(new_reminder)
            new_chapter["reminders"] = new_reminders
            new_chapters.append(new_chapter)
        new_data[subject] = new_chapters
    return new_data

def load_data_from_firebase():
    ref = db.reference("subject_chapters_data")
    data = ref.get()
    if data is None:
        return {subject: [] for subject in SUBJECT_CHOICES}
    return process_subject_data(data)

def save_data_to_firebase():
    data = st.session_state['subject_chapters_data']
    data_prepared = prepare_data_for_firebase(data)
    ref = db.reference("subject_chapters_data")
    ref.set(data_prepared)

def load_todo_from_firebase():
    ref = db.reference("todo_data")
    data = ref.get()
    if data is None:
        return []
    current_time_dt = datetime.datetime.now()
    filtered_tasks = [
        task for task in data
        if current_time_dt - datetime.datetime.fromisoformat(task["timestamp"]) < datetime.timedelta(days=1)
    ]
    return filtered_tasks

def save_todo_to_firebase(todo_list):
    ref = db.reference("todo_data")
    ref.set(todo_list)

# ---------------- Session State Initialization ----------------
SUBJECT_CHOICES = ["Botany", "Zoology", "Physics", "Chemistry"]
THEME_OPTIONS = ["Light Mode", "Dark Mode", "Colorful Mode"]

if 'subject_chapters_data' not in st.session_state:
    st.session_state['subject_chapters_data'] = load_data_from_firebase()
if 'app_theme' not in st.session_state:
    st.session_state['app_theme'] = "Light Mode"
if 'todo_list' not in st.session_state:
    st.session_state['todo_list'] = load_todo_from_firebase()

# ---------------- Color Palette (for CSV export and charts) ----------------
PRIMARY_COLOR = "#007BFF"
SECONDARY_COLOR = "#66B2FF"
TAB_HIGHLIGHT_COLOR = "#D1E7DD"
COLOR_SUCCESS = "#28A745"
COLOR_WARNING = "#DC3545"

# ---------------- Motivational Quotes & Study Tips ----------------
motivational_quotes = [
    "The expert in anything was once a beginner.",
    "Believe you can and you're halfway there.",
    "Success is not final, failure is not fatal: it is the courage to continue that counts.",
    "The only way to do great work is to love what you do.",
    "Your future is created by what you do today, not tomorrow."
]
study_tips = [
    "Plan your study schedule and stick to it.",
    "Use active recall and spaced repetition techniques.",
    "Practice with past papers regularly.",
    "Take short breaks to avoid burnout.",
    "Stay hydrated and get enough sleep.",
    "Focus on understanding concepts rather than rote memorization.",
    "Join study groups or online forums for discussions.",
    "Use different learning resources like textbooks, videos, and online materials.",
    "Regularly test yourself to track progress.",
    "Stay positive and believe in your preparation."
]

# ---------------- Helper Functions ----------------
def _create_default_reminders(entry_datetime):
    return [
        {"reminder_id": 1, "type": "12 hour Reminder", "time": entry_datetime + datetime.timedelta(hours=12), "status": "Pending"},
        {"reminder_id": 2, "type": "3 days Reminder", "time": entry_datetime + datetime.timedelta(days=3), "status": "Pending"},
        {"reminder_id": 3, "type": "5 days Reminder", "time": entry_datetime + datetime.timedelta(days=5), "status": "Pending"},
    ]

def _prepare_csv_data(data):
    all_data = []
    for subject, chapters in data.items():
        for chapter in chapters:
            for reminder in chapter['reminders']:
                all_data.append({
                    "Subject": subject,
                    "Chapter Name": chapter['chapter_name'],
                    "Entry Date": chapter['entry_datetime'].strftime("%d/%m/%y %I:%M %p") if isinstance(chapter['entry_datetime'], datetime.datetime) else chapter['entry_datetime'],
                    "Reminder Time": reminder['time'].strftime("%d/%m/%y %I:%M %p") if isinstance(reminder['time'], datetime.datetime) else reminder['time'],
                    "Status": reminder['status'],
                    "Exams Appeared": chapter['exams_appeared'],
                    "Exam Status": chapter['exam_status'],
                    "Time Spent (minutes)": chapter['time_spent']
                })
    return pd.DataFrame(all_data).to_csv(index=False).encode('utf-8')

def _aggregate_productivity_data(data, start_date=None):
    aggregated = {}
    for chapters in data.values():
        for chapter in chapters:
            for reminder in chapter["reminders"]:
                r_date = reminder["time"].date() if isinstance(reminder["time"], datetime.datetime) else datetime.datetime.fromisoformat(reminder["time"]).date()
                if start_date and r_date < start_date:
                    continue
                aggregated.setdefault(r_date, {"total": 0, "revised": 0})
                aggregated[r_date]["total"] += 1
                if reminder["status"] == "Revised":
                    aggregated[r_date]["revised"] += 1
    return aggregated

# ---------------- Core Functions ----------------
def add_chapter_and_reminders(subject, chapter_name, entry_datetime, custom_reminders=None):
    reminders = custom_reminders if custom_reminders else _create_default_reminders(entry_datetime)
    st.session_state['subject_chapters_data'][subject].append({
        "chapter_name": chapter_name,
        "entry_datetime": entry_datetime,
        "reminders": reminders,
        "exams_appeared": 0,
        "exam_status": "Not Appeared",
        "time_spent": 0
    })
    save_data_to_firebase()
    st.success(f"Chapter '{chapter_name}' added to {subject} with reminders starting {entry_datetime.strftime('%d/%m/%y %I:%M %p')}.")

def delete_chapter(subject, chapter_index):
    del st.session_state['subject_chapters_data'][subject][chapter_index]
    save_data_to_firebase()
    st.success("Chapter deleted successfully!")
    st.experimental_rerun()

def mark_reminder_revised(subject, chapter_index, reminder_index):
    st.session_state['subject_chapters_data'][subject][chapter_index]['reminders'][reminder_index]['status'] = "Revised"
    save_data_to_firebase()
    st.experimental_rerun()

def mark_reminder_pending(subject, chapter_index, reminder_index):
    st.session_state['subject_chapters_data'][subject][chapter_index]['reminders'][reminder_index]['status'] = "Pending"
    save_data_to_firebase()
    st.experimental_rerun()

def calculate_subject_progress(subject):
    chapters = st.session_state['subject_chapters_data'][subject]
    if not chapters:
        return 0
    total = sum(len(ch["reminders"]) for ch in chapters)
    revised = sum(1 for ch in chapters for rem in ch["reminders"] if rem["status"] == "Revised")
    return (revised / total) * 100 if total else 0

def display_reminders_section(subject, chapter, chapter_index):
    rem_list = []
    for i, reminder in enumerate(chapter["reminders"]):
        key = f"{subject}_{chapter_index}_{i}"
        current = reminder["status"] == "Revised"
        new_status = st.checkbox(reminder["type"], value=current, key=key)
        if new_status != current:
            if new_status:
                mark_reminder_revised(subject, chapter_index, i)
            else:
                mark_reminder_pending(subject, chapter_index, i)
        rem_list.append({
            "Reminder Type": reminder["type"],
            "Reminder Time": reminder["time"].strftime("%d/%m/%y %I:%M %p") if isinstance(reminder["time"], datetime.datetime) else reminder["time"],
            "Status": "Revised" if reminder["status"] == "Revised" else "Pending"
        })
    with st.container():
        st.markdown("<div class='dataframe-container'>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(rem_list), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

def display_time_spent_section(subject, chapter):
    key = f"time_spent_{subject}_{chapter['chapter_name']}"
    time_spent = st.number_input("Time Spent Studying (minutes):", value=chapter.get("time_spent", 0), min_value=0, step=5, key=key)
    if time_spent != chapter.get("time_spent", 0):
        chapter["time_spent"] = time_spent
        save_data_to_firebase()
        st.success("Time updated!")

def display_exam_tracking_section(subject, chapter, chapter_index):
    st.subheader(f"{subject} Exam Tracking - {chapter['chapter_name']}")
    exam_count_key = f"exam_count_{subject}_{chapter_index}"
    exam_status_key = f"exam_status_{subject}_{chapter_index}"
    exam_appeared = st.number_input("Exams Appeared:", min_value=0, value=chapter.get("exams_appeared", 0), key=exam_count_key)
    exam_status_text = st.text_input("Exam Status:", value=chapter.get("exam_status", "Not Appeared"), key=exam_status_key, placeholder="e.g., Score, Performance")
    if st.button("Update Exam Info", key=f"update_exam_{subject}_{chapter_index}"):
        chapter["exams_appeared"] = exam_appeared
        chapter["exam_status"] = exam_status_text
        save_data_to_firebase()
        st.success("Exam info updated!")

def _get_chapter_item(subject_data, chapter_name):
    for idx, chapter in enumerate(subject_data):
        if chapter["chapter_name"] == chapter_name:
            return chapter, idx
    return None, -1

def display_subject_tab_content(subject):
    st.subheader(f"{subject} Revision Progress")
    progress = calculate_subject_progress(subject)
    st.progress(int(min(progress, 100)))
    st.write(f"Overall Revision: {progress:.2f}%")
    
    chapters = st.session_state['subject_chapters_data'][subject]
    chapter_names = [ch["chapter_name"] for ch in chapters]
    if not chapter_names:
        st.info(f"No chapters in {subject}. Please add one from the sidebar.")
        return
    
    selected = st.selectbox(f"Select {subject} Chapter:", ["Select Chapter"] + chapter_names, index=0)
    if selected != "Select Chapter":
        chapter, idx = _get_chapter_item(chapters, selected)
        if chapter:
            display_reminders_section(subject, chapter, idx)
            display_time_spent_section(subject, chapter)
            display_exam_tracking_section(subject, chapter, idx)
            st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
            st.markdown("### Delete Chapter", unsafe_allow_html=True)
            confirm_delete = st.checkbox("Confirm deletion of this chapter", key=f"confirm_delete_{selected}")
            if confirm_delete:
                if st.button("Delete Chapter", key=f"delete_{selected}"):
                    delete_chapter(subject, idx)

def download_csv_data():
    return _prepare_csv_data(st.session_state['subject_chapters_data'])

# ---------------- Productivity Tracking ----------------
def display_productivity_tracking():
    st.header("Productivity Tracking")
    period = st.selectbox("Tracking Period:", ["Last 1 Week", "Last 1 Month", "All Time"])
    today = datetime.date.today()
    start_date = None
    if period == "Last 1 Week":
        start_date = today - datetime.timedelta(days=7)
    elif period == "Last 1 Month":
        start_date = today - datetime.timedelta(days=30)
    agg = _aggregate_productivity_data(st.session_state['subject_chapters_data'], start_date)
    df = pd.DataFrame([
        {"Date": d, "Total Reminders": stats["total"], "Revised": stats["revised"],
         "Productivity (%)": (stats["revised"] / stats["total"] * 100) if stats["total"] else 0}
        for d, stats in agg.items()
    ])
    if not df.empty:
        df.sort_values("Date", inplace=True)
        df["Date"] = df["Date"].apply(lambda d: d.strftime("%d/%m/%y"))
        fig = px.line(df, x="Date", y="Productivity (%)", markers=True, title="Daily Productivity")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No productivity data available.")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.title("📚 NEET Prep App")
    with st.expander("App Theme", expanded=False):
        st.session_state['app_theme'] = st.selectbox("Choose Theme:", THEME_OPTIONS, index=THEME_OPTIONS.index(st.session_state['app_theme']))
    with st.expander("Add New Chapter", expanded=True):
        subject = st.selectbox("Subject:", SUBJECT_CHOICES)
        chapter_name = st.text_input("Chapter Name:", placeholder="e.g., Structure of Atom")
        entry_date = st.date_input("Entry Date:", value=datetime.date.today())
        entry_time = st.time_input("Entry Time:", value=datetime.time(datetime.datetime.now().hour, datetime.datetime.now().minute))
        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        st.subheader("Customize Revision Schedule (Optional)")
        custom_12hr = st.checkbox("Use 12 hour Reminder?", value=True)
        custom_3day = st.checkbox("Use 3 days Reminder?", value=True)
        custom_5day = st.checkbox("Use 5 days Reminder?", value=True)
        if st.button("Add Chapter"):
            if chapter_name and subject:
                entry_datetime = datetime.datetime.combine(entry_date, entry_time)
                custom_reminders_list = []
                if custom_12hr:
                    custom_reminders_list.append({
                        "reminder_id": 1,
                        "type": "12 hour Reminder",
                        "time": entry_datetime + datetime.timedelta(hours=12),
                        "status": "Pending"
                    })
                if custom_3day:
                    custom_reminders_list.append({
                        "reminder_id": 2,
                        "type": "3 days Reminder",
                        "time": entry_datetime + datetime.timedelta(days=3),
                        "status": "Pending"
                    })
                if custom_5day:
                    custom_reminders_list.append({
                        "reminder_id": 3,
                        "type": "5 days Reminder",
                        "time": entry_datetime + datetime.timedelta(days=5),
                        "status": "Pending"
                    })
                add_chapter_and_reminders(subject, chapter_name, entry_datetime, custom_reminders_list)
            else:
                st.warning("Please enter a chapter name and select a subject.")
    with st.expander("Data Options", expanded=False):
        st.header("Download Data")
        csv_data = download_csv_data()
        st.download_button(label="Download CSV", data=csv_data, file_name="neet_prep_data.csv", mime='text/csv')
    st.header("Motivation")
    st.markdown(f"> *{random.choice(motivational_quotes)}*")
    st.header("Study Tips")
    with st.expander("See Study Tips"):
        for tip in study_tips:
            st.markdown(f"- {tip}")

# ---------------- Apply Theme CSS ----------------
apply_theme_css()

# ---------------- Main Panel & Tabs ----------------
st.markdown("<div class='main-header'><h1>NEET Prep Tracker Dashboard (Sathvik)</h1></div>", unsafe_allow_html=True)
tabs = st.tabs(SUBJECT_CHOICES + ["Today's Revisions", "Productivity Tracking", "To Do List"])

# ----- Subject Tabs -----
for idx, subject in enumerate(SUBJECT_CHOICES):
    with tabs[idx]:
        st.header(subject)
        st.markdown(f"<div class='dataframe-container' style='background-color:{TAB_HIGHLIGHT_COLOR}; padding: 10px; border-radius: 5px;'>", unsafe_allow_html=True)
        display_subject_tab_content(subject)
        st.markdown("</div>", unsafe_allow_html=True)

# ----- Today's Revisions Tab -----
with tabs[len(SUBJECT_CHOICES)]:
    st.header("Today's Revisions")
    mode = st.radio("View Mode", ["Today", "Select Date"], index=0, horizontal=True)
    if mode == "Today":
        sel_date = datetime.date.today()
        st.info(f"Revisions for today: {sel_date.strftime('%d/%m/%y')}")
    else:
        sel_date = st.date_input("Select Date:", value=datetime.date.today())
        st.info(f"Revisions on: {sel_date.strftime('%d/%m/%y')}")
    
    revision_entries = []
    for subj, chapters in st.session_state['subject_chapters_data'].items():
        for c_idx, chapter in enumerate(chapters):
            for r_idx, reminder in enumerate(chapter["reminders"]):
                if reminder["time"].date() == sel_date:
                    revision_entries.append((subj, c_idx, chapter, r_idx, reminder))
    st.markdown(f"**Total revisions found: {len(revision_entries)}**")
    if revision_entries:
        status_counts = {"Revised": 0, "Pending": 0}
        for entry in revision_entries:
            status_counts[entry[4]["status"]] += 1
        df_status = pd.DataFrame({"Status": list(status_counts.keys()), "Count": list(status_counts.values())})
        fig = px.pie(df_status, names="Status", values="Count", title="Revision Status Breakdown",
                     color_discrete_map={"Revised": COLOR_SUCCESS, "Pending": COLOR_WARNING})
        st.plotly_chart(fig, use_container_width=True)
        for subj, c_idx, chapter, r_idx, reminder in revision_entries:
            with st.container():
                st.markdown(
                    f"<div class='container-box'>"
                    f"<strong>{subj}</strong> | {chapter['chapter_name']} | {reminder['type']} at {reminder['time'].strftime('%I:%M %p')} | Status: {reminder['status']}"
                    f"</div>", unsafe_allow_html=True)
                key = f"rev_{subj}_{c_idx}_{r_idx}"
                current = reminder["status"] == "Revised"
                new_stat = st.checkbox("Mark Revised", value=current, key=key)
                if new_stat != current:
                    if new_stat:
                        mark_reminder_revised(subj, c_idx, r_idx)
                    else:
                        mark_reminder_pending(subj, c_idx, r_idx)
    else:
        st.info("No revisions scheduled for the selected date.")

# ----- Productivity Tracking Tab -----
with tabs[len(SUBJECT_CHOICES) + 1]:
    display_productivity_tracking()

# ----- To Do List Tab -----
with tabs[-1]:
    st.header("To Do List")
    st.subheader("Add New Task")
    new_task = st.text_input("Enter today's task:", key="new_todo_task")
    if st.button("Add Task", key="add_task"):
        if new_task:
            new_task_entry = {
                "task": new_task,
                "status": "Pending",
                "timestamp": datetime.datetime.now().isoformat()
            }
            st.session_state['todo_list'].append(new_task_entry)
            save_todo_to_firebase(st.session_state['todo_list'])
            st.success("Task added!")
        else:
            st.warning("Please enter a task.")
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    
    st.subheader("Manual Tasks")
    if st.session_state['todo_list']:
        for i, task in enumerate(st.session_state['todo_list']):
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                key = f"todo_{i}"
                current = task["status"] == "Completed"
                new_val = st.checkbox(task["task"], value=current, key=key)
                if new_val != current:
                    st.session_state['todo_list'][i]["status"] = "Completed" if new_val else "Pending"
                    save_todo_to_firebase(st.session_state['todo_list'])
            with col2:
                delete_key = f"delete_{i}"
                if st.button("❌", key=delete_key):
                    del st.session_state['todo_list'][i]
                    save_todo_to_firebase(st.session_state['todo_list'])
                    st.experimental_rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No manual tasks added yet.")
    
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    st.subheader("Today's Revision Reminders")
    today_date = datetime.date.today()
    rev_tasks = []
    for subj, chapters in st.session_state['subject_chapters_data'].items():
        for c_idx, chapter in enumerate(chapters):
            for r_idx, reminder in enumerate(chapter["reminders"]):
                if reminder["time"].date() == today_date:
                    rev_tasks.append((subj, c_idx, chapter, r_idx, reminder))
    if rev_tasks:
        for subj, c_idx, chapter, r_idx, reminder in rev_tasks:
            with st.container():
                st.markdown(
                    f"<div class='container-box'>"
                    f"<strong>{subj}</strong> | {chapter['chapter_name']} | {reminder['type']} at {reminder['time'].strftime('%I:%M %p')} | Status: {reminder['status']}"
                    f"</div>", unsafe_allow_html=True)
                key = f"todo_rev_{subj}_{c_idx}_{r_idx}"
                current = reminder["status"] == "Revised"
                new_stat = st.checkbox("Mark Revised", value=current, key=key)
                if new_stat != current:
                    if new_stat:
                        mark_reminder_revised(subj, c_idx, r_idx)
                    else:
                        mark_reminder_pending(subj, c_idx, r_idx)
    else:
        st.info("No revision reminders scheduled for today.")
    
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    st.subheader("Today's To-Do Overview")
    total_manual = len(st.session_state['todo_list'])
    completed_manual = sum(1 for t in st.session_state['todo_list'] if t["status"] == "Completed")
    total_rev = len(rev_tasks)
    completed_rev = sum(1 for entry in rev_tasks if entry[4]["status"] == "Revised")
    total_tasks = total_manual + total_rev
    completed_tasks = completed_manual + completed_rev
    pending_tasks = total_tasks - completed_tasks
    if total_tasks > 0:
        df_overview = pd.DataFrame({
            "Status": ["Completed", "Pending"],
            "Count": [completed_tasks, pending_tasks]
        })
        fig = px.pie(df_overview, names="Status", values="Count", title="Today's To-Do Status")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No tasks for today.")

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
