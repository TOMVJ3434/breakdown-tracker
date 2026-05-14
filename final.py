import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import os
from datetime import datetime, timedelta
from io import BytesIO

# Modern Charts
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DB_PATH = "breakdown_database.db"

# ================================================================================
# DATABASE FUNCTIONS (Same as before)
# ================================================================================
def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='breakdown_log'")
    table_exists = cursor.fetchone()

    if not table_exists:
        cursor.execute("""
            CREATE TABLE breakdown_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT,
                mc_name TEXT NOT NULL,
                division TEXT,
                issue TEXT NOT NULL,
                date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                close_time TEXT NOT NULL,
                close_date TEXT,
                total_time_mins INTEGER NOT NULL,
                action_taken TEXT,
                shift TEXT,
                maintenance_name TEXT,
                severity TEXT,
                status TEXT DEFAULT 'Open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    conn.close()

def get_all_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM breakdown_log ORDER BY date DESC", conn)
    conn.close()
    return df

def save_to_database(df):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO breakdown_log 
            (machine_id, mc_name, division, issue, date, start_time, close_time, close_date, total_time_mins, action_taken, shift, maintenance_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(row.get('Machine ID', '')), str(row.get('M/C Name', '')), 
            str(row.get('Division', 'DIV-1')), str(row.get('Issue', '')),
            str(row.get('Date', datetime.now().strftime('%d-%m-%Y'))),
            str(row.get('Start Time', '08:00')), str(row.get('Close Time', '09:00')),
            str(row.get('Close Date', row.get('Date', ''))),
            int(row.get('Total Time (mins)', 30)),
            str(row.get('Action Taken', '')), str(row.get('Shift', '1')),
            str(row.get('Maintenance Name', 'Technician_1'))
        ))
    conn.commit()
    conn.close()
    return len(df)

def delete_record(record_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM breakdown_log WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

def clear_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM breakdown_log")
    conn.commit()
    conn.close()

init_database()

# ================================================================================
# MODERN UI CONFIGURATION
# ================================================================================
st.set_page_config(
    page_title="🔧 AI Breakdown Tracker",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern CSS with Glassmorphism + Dark Theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    * {
        font-family: 'Inter', sans-serif !important;
    }

    /* Dark Gradient Background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }

    /* Glassmorphism Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 24px;
        margin: 12px 0;
        transition: all 0.3s ease;
    }
    .glass-card:hover {
        background: rgba(255, 255, 255, 0.08);
        border-color: rgba(255, 255, 255, 0.2);
        transform: translateY(-2px);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
    }

    /* Neon Glow Text */
    .neon-text {
        color: #00f5ff;
        text-shadow: 0 0 10px rgba(0, 245, 255, 0.5);
    }

    /* Gradient Text */
    .gradient-text {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }

    /* Sidebar Glass */
    [data-testid="stSidebar"] {
        background: rgba(15, 12, 41, 0.8) !important;
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* Modern Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
    }

    /* KPI Cards with Gradient */
    .kpi-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 24px;
        text-align: center;
        transition: all 0.3s ease;
    }
    .kpi-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        border-color: rgba(0, 245, 255, 0.3);
    }

    /* Animated Border */
    .animated-border {
        position: relative;
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(16px);
        padding: 24px;
        overflow: hidden;
    }
    .animated-border::before {
        content: '';
        position: absolute;
        top: -2px; left: -2px; right: -2px; bottom: -2px;
        background: linear-gradient(45deg, #ff00cc, #3333ff, #00ccff, #ff00cc);
        background-size: 400% 400%;
        z-index: -1;
        border-radius: 22px;
        animation: gradient-rotate 3s ease infinite;
    }
    @keyframes gradient-rotate {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Status Badges */
    .badge-ok {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75em;
        font-weight: 600;
    }
    .badge-ng {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75em;
        font-weight: 600;
    }
    .badge-warning {
        background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);
        color: #333;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75em;
        font-weight: 600;
    }

    /* Modern Table */
    .modern-table {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 16px;
        overflow: hidden;
    }

    /* Section Headers */
    .section-header {
        font-size: 1.5em;
        font-weight: 700;
        color: #fff;
        margin: 24px 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid rgba(0, 245, 255, 0.3);
    }

    /* Floating Action Button */
    .fab {
        position: fixed;
        bottom: 30px;
        right: 30px;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.5);
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .fab:hover {
        transform: scale(1.1) rotate(90deg);
    }

    /* Chart Container */
    .chart-container {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 20px;
        margin: 12px 0;
    }

    /* Progress Bar Modern */
    .progress-modern {
        height: 8px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        overflow: hidden;
    }
    .progress-modern-fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        transition: width 1s ease;
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.05);
    }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ================================================================================
# DEMO DATA
# ================================================================================
def generate_demo_data():
    np.random.seed(42)
    machines = ['Press-01', 'Press-02', 'CNC-01', 'CNC-02', 'Lathe-01', 'Lathe-02', 'Welding-01', 'Drill-01']
    machine_ids = ['MC-001', 'MC-002', 'MC-003', 'MC-004', 'MC-005', 'MC-006', 'MC-007', 'MC-008']
    divisions = ['DIV-1', 'DIV-2', 'DIV-3', 'DIV-4', 'DIV-5']
    issues = ['Sensor Fail', 'Air Pressure Low', 'Hydraulic Leak', 'Motor Overheat', 'Belt Break', 'Tool Wear', 'Lubrication Issue', 'Electrical Fault']
    actions = {
        'Sensor Fail': 'Sensor Changed', 'Air Pressure Low': 'Compressor Serviced',
        'Hydraulic Leak': 'Seal Replaced', 'Motor Overheat': 'Motor Cooling Checked',
        'Belt Break': 'Belt Replaced', 'Tool Wear': 'Tool Changed',
        'Lubrication Issue': 'Oil Refilled', 'Electrical Fault': 'Wiring Checked'
    }
    maintenance_names = ['Ramesh', 'Suresh', 'Kumar', 'Vijay', 'Arun', 'Dinesh']
    data = []
    base_date = datetime(2026, 5, 1)
    for i in range(150):
        machine = np.random.choice(machines)
        machine_id = machine_ids[machines.index(machine)]
        division = np.random.choice(divisions, p=[0.35, 0.25, 0.15, 0.15, 0.10])
        issue = np.random.choice(issues, p=[0.18, 0.15, 0.12, 0.12, 0.10, 0.13, 0.10, 0.10])
        if i > 50 and np.random.random() < 0.3:
            issue = data[np.random.randint(0, i)]['Issue']
        date = base_date + timedelta(days=np.random.randint(0, 30))
        start_hour = np.random.randint(8, 19)
        start_min = np.random.choice([0, 15, 30, 45])
        start_time = datetime.strptime(f"{start_hour:02d}:{start_min:02d}", "%H:%M")
        duration_mins = np.random.randint(15, 240)
        close_time = start_time + timedelta(minutes=duration_mins)
        close_date = date
        if close_time.hour < start_time.hour:
            close_date = date + timedelta(days=1)
        data.append({
            'ID': i + 1, 'Machine ID': machine_id, 'M/C Name': machine, 'Division': division,
            'Issue': issue, 'Date': date.strftime('%d-%m-%Y'), 'Start Time': start_time.strftime('%H:%M'),
            'Close Time': close_time.strftime('%H:%M'), 'Close Date': close_date.strftime('%d-%m-%Y'),
            'Total Time (mins)': duration_mins, 'Action Taken': actions[issue],
            'Shift': str(np.random.choice([1, 2, 3])), 'Maintenance Name': np.random.choice(maintenance_names),
            'Severity': np.random.choice(['Low', 'Medium', 'High'], p=[0.5, 0.3, 0.2])
        })
    return pd.DataFrame(data)

# ================================================================================
# SIDEBAR - MODERN GLASS
# ================================================================================
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 30px 20px; background: linear-gradient(135deg, rgba(102,126,234,0.3) 0%, rgba(118,75,162,0.3) 100%); 
                border-radius: 20px; margin-bottom: 24px; border: 1px solid rgba(255,255,255,0.1);">
        <div style="font-size: 3em; margin-bottom: 12px;">🔧</div>
        <h2 style="color: #fff; margin: 0; font-size: 1.3em; font-weight: 700;">AI Breakdown Tracker</h2>
        <p style="color: rgba(255,255,255,0.6); margin-top: 8px; font-size: 0.85em;">Industrial Maintenance System</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

    st.subheader("🏭 Division Filter")
    try:
        conn_temp = sqlite3.connect(DB_PATH)
        divs_from_db = pd.read_sql_query("SELECT DISTINCT division FROM breakdown_log WHERE division IS NOT NULL", conn_temp)
        conn_temp.close()
        available_divisions = divs_from_db['division'].tolist()
        if not available_divisions:
            available_divisions = ['DIV-1', 'DIV-2', 'DIV-3']
    except:
        available_divisions = ['DIV-1', 'DIV-2', 'DIV-3']
    available_divisions.append("All")
    division_filter = st.multiselect("Select Divisions", available_divisions, default=["All"])

    st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

    st.subheader("⚙️ Settings")
    shift_start = st.time_input("🌅 Shift Start", datetime.strptime("08:00", "%H:%M").time())
    shift_end = st.time_input("🌙 Shift End", datetime.strptime("20:00", "%H:%M").time())
    target_mttr = st.slider("🎯 Target MTTR (mins)", 15, 120, 30)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align: center; color: rgba(255,255,255,0.4); font-size: 0.75em; margin-top: 20px;">
        <p>v3.0 | SQLite + Streamlit + Plotly</p>
    </div>
    """, unsafe_allow_html=True)

# ================================================================================
# HEADER - MODERN
# ================================================================================
col_title, col_time = st.columns([3, 1])
with col_title:
    st.markdown("""
    <h1 style="font-size: 2.5em; font-weight: 800; margin-bottom: 8px;">
        <span class="gradient-text">🔧 AI Breakdown Tracker</span>
    </h1>
    <p style="color: rgba(255,255,255,0.6); font-size: 1em; margin-top: 0;">
        <span style="color: #00f5ff;">●</span> Division Wise 
        <span style="color: #667eea; margin-left: 15px;">●</span> Machine ID 
        <span style="color: #38ef7d; margin-left: 15px;">●</span> MTTR/MTBF Analytics
    </p>
    """, unsafe_allow_html=True)

with col_time:
    st.markdown(f"""
    <div class="glass-card" style="text-align: center; padding: 16px;">
        <p style="color: rgba(255,255,255,0.6); font-size: 0.85em; margin: 0;">📅 {datetime.now().strftime('%d-%m-%Y')}</p>
        <p style="color: #00f5ff; font-size: 1.2em; margin: 8px 0 0 0; font-weight: 600;">🕐 {datetime.now().strftime('%H:%M:%S')}</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

# ================================================================================
# DATA INPUT - MODERN CARDS
# ================================================================================
st.markdown("<div class='section-header'>💾 Data Input & Database</div>", unsafe_allow_html=True)

input_col1, input_col2 = st.columns([2, 1])

with input_col1:
    st.markdown("""
    <div class="glass-card">
        <h4 style="color: #00f5ff; margin: 0 0 15px 0; font-weight: 600;">📁 Import Data</h4>
    """, unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Excel/CSV File", type=["xlsx", "xls", "csv"], label_visibility="collapsed")
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_upload = pd.read_csv(uploaded_file)
            else:
                df_upload = pd.read_excel(uploaded_file)
            st.success(f"✅ Loaded {len(df_upload)} records from {uploaded_file.name}")
            st.dataframe(df_upload.head(3), use_container_width=True, height=150)
            if st.button("💾 SAVE TO DATABASE", type="primary", use_container_width=True):
                saved_count = save_to_database(df_upload)
                st.success(f"✅ {saved_count} records saved!")
                st.balloons()
        except Exception as e:
            st.error(f"❌ Error: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

with input_col2:
    st.markdown("""
    <div class="glass-card">
        <h4 style="color: #38ef7d; margin: 0 0 15px 0; font-weight: 600;">📝 Manual Entry</h4>
    """, unsafe_allow_html=True)
    with st.form("manual_entry"):
        m_id = st.text_input("🏷️ Machine ID", "MC-001")
        m_name = st.text_input("🔧 Machine Name", "Press-01")
        m_division = st.text_input("🏭 Division", "DIV-1")
        m_issue = st.text_input("⚠️ Issue", "Sensor Fail")
        m_date = st.date_input("📅 Start Date", datetime.now())
        m_start = st.time_input("⏱️ Start Time", datetime.strptime("10:00", "%H:%M").time())
        m_close_date = st.date_input("📅 Close Date", datetime.now())
        m_close = st.time_input("✅ Close Time", datetime.strptime("11:00", "%H:%M").time())
        m_action = st.text_input("🔩 Action Taken", "Sensor Changed")
        m_shift = st.text_input("🌅 Shift", "1")
        m_maintenance = st.text_input("🔧 Maintenance Name", "Ramesh")
        m_severity = st.selectbox("🔴 Severity", ["Low", "Medium", "High"])
        submitted = st.form_submit_button("➕ ADD TO DATABASE", use_container_width=True)
        if submitted:
            start_dt = datetime.combine(m_date, m_start)
            close_dt = datetime.combine(m_close_date, m_close)
            if close_dt < start_dt:
                close_dt += timedelta(days=1)
            duration = int((close_dt - start_dt).total_seconds() / 60)
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO breakdown_log 
                (machine_id, mc_name, division, issue, date, start_time, close_time, close_date, total_time_mins, action_taken, shift, maintenance_name, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (m_id, m_name, m_division, m_issue, m_date.strftime('%d-%m-%Y'), 
                m_start.strftime('%H:%M'), m_close.strftime('%H:%M'), 
                close_dt.strftime('%d-%m-%Y'), duration, m_action, m_shift, m_maintenance, m_severity))
            conn.commit()
            conn.close()
            st.success(f"✅ Record added! Duration: {duration} mins")
            st.balloons()
    st.markdown("</div>", unsafe_allow_html=True)

# ================================================================================
# LOAD DATA
# ================================================================================
st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
st.markdown("<div class='section-header'>📊 Load Data from Database</div>", unsafe_allow_html=True)

load_option = st.radio("Select Data Source:", ["📊 Database (Saved Records)", "🎲 Demo Data"], horizontal=True)

if load_option == "📊 Database (Saved Records)":
    df = get_all_data()
    if len(df) == 0:
        st.warning("⚠️ Database empty! Upload Excel or add manual entry first.")
        st.stop()
    df['Machine ID'] = df['machine_id']
    df['M/C Name'] = df['mc_name']
    df['Division'] = df['division']
    df['Issue'] = df['issue']
    df['Date'] = df['date']
    df['Start Time'] = df['start_time']
    df['Close Time'] = df['close_time']
    df['Close Date'] = df['close_date'].fillna(df['date'])
    df['Total Time (mins)'] = df['total_time_mins']
    df['Action Taken'] = df['action_taken']
    df['Shift'] = df['shift']
    df['Maintenance Name'] = df['maintenance_name']
    st.success(f"✅ Loaded {len(df)} records from Database")
else:
    df = generate_demo_data()
    st.info(f"📊 Using DEMO DATA — {len(df)} records")

# ================================================================================
# DATA PROCESSING
# ================================================================================
mc_col = 'M/C Name'
issue_col = 'Issue'
date_col = 'Date'
start_col = 'Start Time'
close_col = 'Close Time'
action_col = 'Action Taken'
time_col = 'Total Time (mins)'
machine_id_col = 'Machine ID'
division_col = 'Division'

if 'Close Date' not in df.columns:
    df['Close Date'] = df[date_col]

if time_col not in df.columns:
    df[time_col] = 30

if 'Shift' not in df.columns:
    df['Shift'] = '1'
if 'Maintenance Name' not in df.columns:
    df['Maintenance Name'] = 'Technician_1'
if 'Division' not in df.columns:
    df['Division'] = 'DIV-1'
if 'Machine ID' not in df.columns:
    df['Machine ID'] = 'MC-000'

if division_filter and "All" not in division_filter:
    df = df[df[division_col].isin(division_filter)].copy()

df = df.dropna(subset=[mc_col, issue_col]).copy()

# ================================================================================
# KPI CARDS - MODERN
# ================================================================================
st.markdown("<br>", unsafe_allow_html=True)

total_breakdowns = len(df)
total_downtime = df[time_col].sum()
avg_downtime = df[time_col].mean()
mttr = df[time_col].mean()
unique_issues = df[issue_col].nunique()
unique_machines = df[mc_col].nunique()
unique_divisions = df[division_col].nunique()
repeated_issues = df[issue_col].value_counts()
top_repeated = repeated_issues.iloc[0] if len(repeated_issues) > 0 else 0
top_issue = repeated_issues.index[0] if len(repeated_issues) > 0 else 'N/A'

total_runtime = 30 * 24 * 60
mtbf = total_runtime / total_breakdowns if total_breakdowns > 0 else 0

kpi_data = [
    ("🔧 Total Breakdowns", f"{total_breakdowns}", '#667eea', 'breakdowns'),
    ("⏱️ Total Downtime", f"{total_downtime//60}h {total_downtime%60}m", '#f093fb', 'downtime'),
    ("📊 Avg Downtime", f"{avg_downtime:.0f} mins", '#4facfe', 'avg'),
    ("🎯 MTTR", f"{mttr:.0f} mins", '#43e97b' if mttr <= target_mttr else '#fa709a', 'mttr'),
    ("⏰ MTBF", f"{mtbf//60:.0f}h {mtbf%60:.0f}m", '#38f9d7', 'mtbf'),
    ("🏭 Divisions", f"{unique_divisions}", '#ffecd2', 'divisions'),
]

kpi_cols = st.columns(6)
for col, (label, value, color, key) in zip(kpi_cols, kpi_data):
    with col:
        st.markdown(f"""
        <div class="kpi-card">
            <h3 style="color: {color}; margin: 0; font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">{label}</h3>
            <h2 style="color: #fff; margin: 12px 0; font-size: 1.8em; font-weight: 800;">{value}</h2>
            <div class="progress-modern">
                <div class="progress-modern-fill" style="width: {min(100, int(value.split()[0]) if value.split()[0].isdigit() else 75)}%"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ================================================================================
# AI INTELLIGENCE - MODERN ALERTS
# ================================================================================
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<div class='section-header'>🧠 AI Maintenance Intelligence</div>", unsafe_allow_html=True)

ai_insights = []
ai_sev = []

if mttr > target_mttr:
    ai_insights.append(f"🔴 HIGH MTTR: {mttr:.0f} mins exceeds target ({target_mttr} mins)")
    ai_sev.append("critical")
if top_repeated > 5:
    ai_insights.append(f"🟡 REPEATED: '{top_issue}' occurred {top_repeated} times")
    ai_sev.append("warning")
if total_breakdowns > 50:
    ai_insights.append(f"⚠️ HIGH FREQUENCY: {total_breakdowns} breakdowns")
    ai_sev.append("warning")
if mtbf < 8 * 60:
    ai_insights.append(f"⏰ LOW MTBF: {mtbf//60:.0f}h between failures")
    ai_sev.append("warning")
if mttr <= target_mttr and top_repeated <= 3:
    ai_insights.append("✅ EXCELLENT: MTTR within target")
    ai_sev.append("success")
if unique_divisions > 1:
    div_counts = df[division_col].value_counts()
    worst_div = div_counts.index[0]
    worst_count = div_counts.iloc[0]
    ai_insights.append(f"🏭 WORST DIVISION: '{worst_div}' with {worst_count} breakdowns")
    ai_sev.append("warning")

if ai_insights:
    insight_cols = st.columns(min(len(ai_insights), 3))
    for idx, (insight, sev) in enumerate(zip(ai_insights, ai_sev)):
        with insight_cols[idx % 3]:
            if sev == "critical":
                st.markdown(f"""
                <div class="glass-card" style="border-left: 4px solid #ff006e;">
                    <p style="color: #ff006e; font-weight: 600; margin: 0;">{insight}</p>
                </div>
                """, unsafe_allow_html=True)
            elif sev == "warning":
                st.markdown(f"""
                <div class="glass-card" style="border-left: 4px solid #fb5607;">
                    <p style="color: #fb5607; font-weight: 600; margin: 0;">{insight}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="glass-card" style="border-left: 4px solid #38b000;">
                    <p style="color: #38b000; font-weight: 600; margin: 0;">{insight}</p>
                </div>
                """, unsafe_allow_html=True)

# ================================================================================
# MODERN TABS WITH INTERACTIVE CHARTS
# ================================================================================
st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Dashboard", "🏭 Division View", "🔄 Repeated Issues", "🔍 Issue Detail", "🏭 Machine View", "📋 Full Data", "💾 DB Manager"
])

# ==================== TAB 1: DASHBOARD - MODERN CHARTS ====================
with tab1:
    st.markdown("<div class='section-header'>📊 Maintenance Dashboard</div>", unsafe_allow_html=True)

    # Division Bar Chart - Modern
    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #00f5ff; margin-bottom: 16px;'>🏭 Division-wise Breakdown Summary</h4>", unsafe_allow_html=True)

    div_summary = df.groupby(division_col).agg({
        time_col: ['sum', 'mean', 'count'],
        mc_col: 'nunique'
    }).round(0)
    div_summary.columns = ['Total Downtime (mins)', 'Avg Downtime (mins)', 'Breakdown Count', 'Machines Affected']
    div_summary = div_summary.sort_values('Breakdown Count', ascending=False)
    st.dataframe(div_summary, use_container_width=True)

    # Interactive Plotly Bar Chart
    div_counts = df[division_col].value_counts().reset_index()
    div_counts.columns = ['Division', 'Count']

    fig_div = px.bar(div_counts, x='Division', y='Count',
                     title='Breakdown Count by Division',
                     color='Count', color_continuous_scale='viridis',
                     template='plotly_dark')
    fig_div.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        title_font_size=16,
        title_x=0.5,
        showlegend=False
    )
    st.plotly_chart(fig_div, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Top 5 Issues - Interactive Pie
    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #00f5ff; margin-bottom: 16px;'>🔄 Top 5 Repeated Issues</h4>", unsafe_allow_html=True)

    top5 = df[issue_col].value_counts().head(5).reset_index()
    top5.columns = ['Issue', 'Count']

    fig_pie = px.pie(top5, values='Count', names='Issue',
                     title='Top 5 Issues Distribution',
                     color_discrete_sequence=px.colors.sequential.Plasma_r,
                     template='plotly_dark',
                     hole=0.4)
    fig_pie.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        title_x=0.5,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2)
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Machine Downtime - Interactive
    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #00f5ff; margin-bottom: 16px;'>🏭 Machine-wise Total Downtime</h4>", unsafe_allow_html=True)

    machine_downtime = df.groupby(mc_col)[time_col].sum().sort_values(ascending=False).reset_index()
    machine_downtime.columns = ['Machine', 'Downtime (mins)']
    machine_downtime['Downtime (hours)'] = machine_downtime['Downtime (mins)'] / 60

    fig_machine = px.bar(machine_downtime, x='Machine', y='Downtime (hours)',
                        title='Machine Downtime (Hours)',
                        color='Downtime (hours)',
                        color_continuous_scale='reds',
                        template='plotly_dark')
    fig_machine.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        title_x=0.5,
        xaxis_tickangle=-45
    )
    st.plotly_chart(fig_machine, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Daily Trend - Interactive Line
    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #00f5ff; margin-bottom: 16px;'>📅 Daily Breakdown Trend</h4>", unsafe_allow_html=True)

    daily = df.groupby(date_col).size().reset_index()
    daily.columns = ['Date', 'Count']

    fig_line = px.line(daily, x='Date', y='Count',
                      title='Daily Breakdown Count Trend',
                      markers=True,
                      template='plotly_dark')
    fig_line.update_traces(line_color='#00f5ff', marker_color='#667eea', marker_size=8)
    fig_line.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        title_x=0.5,
        xaxis_tickangle=-45
    )
    st.plotly_chart(fig_line, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== TAB 2: DIVISION VIEW ====================
with tab2:
    st.markdown("<div class='section-header'>🏭 Division-wise Analysis</div>", unsafe_allow_html=True)

    all_divisions = sorted(df[division_col].unique())
    selected_division = st.selectbox("🏭 Select Division", all_divisions)

    if selected_division:
        div_df = df[df[division_col] == selected_division].copy()

        # KPI Cards
        div_cols = st.columns(4)
        div_metrics = [
            ("💥 Breakdowns", f"{len(div_df)}", '#ff006e'),
            ("⏱️ Total Time", f"{div_df[time_col].sum()//60}h", '#8338ec'),
            ("📊 Avg Time", f"{div_df[time_col].mean():.0f}m", '#3a86ff'),
            ("🔧 Machines", f"{div_df[mc_col].nunique()}", '#38b000'),
        ]
        for col, (label, value, color) in zip(div_cols, div_metrics):
            with col:
                st.markdown(f"""
                <div class="kpi-card">
                    <h4 style="color: {color}; margin: 0; font-size: 0.9em; font-weight: 600;">{label}</h4>
                    <h2 style="color: #fff; margin: 8px 0; font-size: 1.5em; font-weight: 700;">{value}</h2>
                </div>
                """, unsafe_allow_html=True)

        # Division Issues Chart
        div_issues = div_df[issue_col].value_counts().reset_index()
        div_issues.columns = ['Issue', 'Count']

        fig_div_issue = px.barh(div_issues, y='Issue', x='Count',
                               title=f'{selected_division} — Issue Breakdown',
                               color='Count',
                               color_continuous_scale='magma',
                               template='plotly_dark')
        fig_div_issue.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            title_x=0.5,
            yaxis_autorange="reversed"
        )
        st.plotly_chart(fig_div_issue, use_container_width=True)

        # Timeline Table
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        timeline = div_df[[date_col, machine_id_col, mc_col, issue_col, start_col, close_col, time_col, action_col, 'Maintenance Name']].sort_values(date_col)
        st.dataframe(timeline, use_container_width=True, height=300)
        st.markdown("</div>", unsafe_allow_html=True)

# ==================== TAB 3: REPEATED ISSUES ====================
with tab3:
    st.markdown("<div class='section-header'>🔄 Repeated Issues Analysis</div>", unsafe_allow_html=True)

    issue_counts = df[issue_col].value_counts().reset_index()
    issue_counts.columns = ['Issue', 'Count']
    issue_counts['Total Downtime (mins)'] = df.groupby(issue_col)[time_col].sum().values
    issue_counts['Avg Repair (mins)'] = df.groupby(issue_col)[time_col].mean().values
    issue_counts['Repeated'] = issue_counts['Count'].apply(
        lambda x: '🔴 HIGH' if x > 5 else '🟡 MEDIUM' if x > 2 else '🟢 LOW'
    )

    # Interactive Table
    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
    st.dataframe(issue_counts, use_container_width=True, height=400)
    st.markdown("</div>", unsafe_allow_html=True)

    # Treemap for Issues
    fig_treemap = px.treemap(issue_counts, path=['Issue'], values='Count',
                            color='Count', color_continuous_scale='RdYlBu_r',
                            title='Issue Frequency Treemap',
                            template='plotly_dark')
    fig_treemap.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        title_x=0.5
    )
    st.plotly_chart(fig_treemap, use_container_width=True)

# ==================== TAB 4: ISSUE DETAIL ====================
with tab4:
    st.markdown("<div class='section-header'>🔍 Issue Detail View</div>", unsafe_allow_html=True)

    all_issues = sorted(df[issue_col].unique())
    selected_issue = st.selectbox("🔍 Select Issue", all_issues)

    if selected_issue:
        issue_df = df[df[issue_col] == selected_issue].copy()

        # Metrics
        issue_cols = st.columns(4)
        issue_metrics = [
            ("🔄 Occurrences", f"{len(issue_df)}", '#667eea'),
            ("⏱️ Total Time", f"{issue_df[time_col].sum()//60}h", '#f093fb'),
            ("📊 Avg Time", f"{issue_df[time_col].mean():.0f}m", '#4facfe'),
            ("🏭 Machines", f"{issue_df[mc_col].nunique()}", '#43e97b'),
        ]
        for col, (label, value, color) in zip(issue_cols, issue_metrics):
            with col:
                st.markdown(f"""
                <div class="kpi-card">
                    <h4 style="color: {color}; margin: 0; font-size: 0.9em; font-weight: 600;">{label}</h4>
                    <h2 style="color: #fff; margin: 8px 0; font-size: 1.5em; font-weight: 700;">{value}</h2>
                </div>
                """, unsafe_allow_html=True)

        # Maintenance Chart
        maint_count = issue_df['Maintenance Name'].value_counts().reset_index()
        maint_count.columns = ['Maintenance Name', 'Repairs']

        fig_maint = px.bar(maint_count, x='Maintenance Name', y='Repairs',
                          title=f'{selected_issue} — Repairs by Maintenance',
                          color='Repairs',
                          color_continuous_scale='teal',
                          template='plotly_dark')
        fig_maint.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            title_x=0.5
        )
        st.plotly_chart(fig_maint, use_container_width=True)

# ==================== TAB 5: MACHINE VIEW ====================
with tab5:
    st.markdown("<div class='section-header'>🏭 Machine-wise Analysis</div>", unsafe_allow_html=True)

    all_machines = sorted(df[mc_col].unique())
    selected_machine = st.selectbox("🔧 Select Machine", all_machines)

    if selected_machine:
        machine_df = df[df[mc_col] == selected_machine].copy()

        m_cols = st.columns(4)
        m_metrics = [
            ("💥 Breakdowns", f"{len(machine_df)}", '#ff006e'),
            ("⏱️ Total Time", f"{machine_df[time_col].sum()//60}h", '#8338ec'),
            ("📊 Avg Time", f"{machine_df[time_col].mean():.0f}m", '#3a86ff'),
            ("⚠️ Issues", f"{machine_df[issue_col].nunique()}", '#fb5607'),
        ]
        for col, (label, value, color) in zip(m_cols, m_metrics):
            with col:
                st.markdown(f"""
                <div class="kpi-card">
                    <h4 style="color: {color}; margin: 0; font-size: 0.9em; font-weight: 600;">{label}</h4>
                    <h2 style="color: #fff; margin: 8px 0; font-size: 1.5em; font-weight: 700;">{value}</h2>
                </div>
                """, unsafe_allow_html=True)

        # Machine Issues Chart
        machine_issues = machine_df[issue_col].value_counts().reset_index()
        machine_issues.columns = ['Issue', 'Count']

        fig_m = px.barh(machine_issues, y='Issue', x='Count',
                       title=f'{selected_machine} — Issue Breakdown',
                       color='Count',
                       color_continuous_scale='cividis',
                       template='plotly_dark')
        fig_m.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            title_x=0.5,
            yaxis_autorange="reversed"
        )
        st.plotly_chart(fig_m, use_container_width=True)

# ==================== TAB 6: FULL DATA ====================
with tab6:
    st.markdown("<div class='section-header'>📋 Complete Breakdown Log</div>", unsafe_allow_html=True)

    # Filters
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        start_date_filter = st.date_input("From Date", datetime.now() - timedelta(days=30))
    with col_f2:
        end_date_filter = st.date_input("To Date", datetime.now())

    f1, f2, f3 = st.columns(3)
    with f1:
        filter_machine = st.multiselect("🏭 Filter Machine", sorted(df[mc_col].unique()), default=[])
    with f2:
        filter_issue = st.multiselect("⚠️ Filter Issue", sorted(df[issue_col].unique()), default=[])
    with f3:
        filter_division = st.multiselect("🏭 Filter Division", sorted(df[division_col].unique()), default=[])

    filtered = df.copy()
    if filter_machine:
        filtered = filtered[filtered[mc_col].isin(filter_machine)]
    if filter_issue:
        filtered = filtered[filtered[issue_col].isin(filter_issue)]
    if filter_division:
        filtered = filtered[filtered[division_col].isin(filter_division)]

    display_cols = [c for c in ['ID', machine_id_col, mc_col, division_col, issue_col, date_col, start_col, close_col, time_col, 'Shift', 'Maintenance Name', action_col] if c in filtered.columns]

    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
    st.dataframe(filtered[display_cols], use_container_width=True, height=500)
    st.markdown("</div>", unsafe_allow_html=True)

    # Export
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        csv = filtered.to_csv(index=False).encode('utf-8')
        st.download_button("📄 Download CSV", csv, f"breakdown_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
    with col_exp2:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            filtered.to_excel(writer, sheet_name='Breakdown Log', index=False)
        st.download_button("📊 Download Excel", buffer.getvalue(), 
                          f"PM_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==================== TAB 7: DB MANAGER ====================
with tab7:
    st.markdown("<div class='section-header'>💾 Database Manager</div>", unsafe_allow_html=True)

    db_df = get_all_data()

    if len(db_df) > 0:
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        st.dataframe(db_df, use_container_width=True, height=400)
        st.markdown("</div>", unsafe_allow_html=True)

        # Delete
        col_del1, col_del2 = st.columns([1, 3])
        with col_del1:
            del_id = st.number_input("Record ID to Delete", min_value=1, step=1)
        with col_del2:
            if st.button("🗑️ DELETE RECORD", type="primary"):
                delete_record(int(del_id))
                st.success(f"✅ Record {del_id} deleted!")
                st.rerun()

        # Danger Zone
        if st.button("🗑️🗑️ CLEAR ALL DATA"):
            clear_database()
            st.warning("⚠️ All data cleared!")
            st.rerun()
    else:
        st.warning("⚠️ Database is empty!")

# ================================================================================
# FOOTER - MODERN
# ================================================================================
st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
st.markdown(f"""
<div class="glass-card" style="text-align: center; padding: 20px;">
    <p style="color: rgba(255,255,255,0.6); font-size: 0.9em; margin: 0; font-weight: 500;">
        🔧 AI Breakdown Tracker v3.0 | {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}
    </p>
    <p style="color: rgba(255,255,255,0.4); font-size: 0.8em; margin: 8px 0 0 0;">
        SQLite Database | Excel Import | Plotly Interactive Charts | Dark Theme
    </p>
</div>
""", unsafe_allow_html=True)