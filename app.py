import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# --- FILE PATHS ---
OPERATORS_FILE = "operators.csv"
ATTENDANCE_FILE = "attendance.csv"
CAPA_FILE = "capa_log.csv"
DEPARTMENTS_FILE = "departments.csv"

# --- SYNC LOGIC ---
def sync_attendance_with_operators(attendance_df, operators_df):
    if attendance_df.empty: return attendance_df
    dates = attendance_df['Date'].unique()
    updated_records = []
    for d in dates:
        daily_snapshot = attendance_df[attendance_df['Date'] == d]
        # Merge ensures operator details (Name, Dept, etc) stay in sync with the Master List
        merged = pd.merge(
            operators_df[['Emp_ID', 'Name', 'Department', 'Shift Group', 'Supervisor']],
            daily_snapshot[['Date', 'Emp_ID', 'Status', 'Late_Mins', 'OT_Hours', 'Shift Timing']],
            on='Emp_ID', how='left'
        )
        merged['Date'] = d
        merged['Status'] = merged['Status'].fillna('Present')
        merged['Late_Mins'] = merged['Late_Mins'].fillna(0)
        merged['OT_Hours'] = merged['OT_Hours'].fillna(0)
        merged['Shift Timing'] = merged['Shift Timing'].fillna("Day")
        updated_records.append(merged)
    return pd.concat(updated_records, ignore_index=True)

# --- PAGE CONFIG ---
st.set_page_config(page_title="Advanced IPQC Attendance Dashboard", layout="wide")
st.title("🏭 Advanced IPQC Attendance & Workforce Dashboard")

# --- INITIALIZE STATE ---
if 'departments_df' not in st.session_state:
    st.session_state.departments_df = pd.read_csv(DEPARTMENTS_FILE) if os.path.exists(DEPARTMENTS_FILE) else pd.DataFrame({"Department": ["IPQC Line 1", "IPQC Line 2", "QA Check", "Final Insp"]})

if 'operators_df' not in st.session_state:
    st.session_state.operators_df = pd.read_csv(OPERATORS_FILE, dtype={"Emp_ID": str}) if os.path.exists(OPERATORS_FILE) else pd.DataFrame({"Emp_ID": ["508939", "512047"], "Name": ["Luqman", "Mohd Azim"], "Department": ["IPQC Line 1", "IPQC Line 1"], "Shift Group": ["A", "A"], "Supervisor": ["John Doe", "John Doe"]})

if 'attendance_df' not in st.session_state:
    st.session_state.attendance_df = pd.read_csv(ATTENDANCE_FILE) if os.path.exists(ATTENDANCE_FILE) else pd.DataFrame()
    if not st.session_state.attendance_df.empty: st.session_state.attendance_df['Date'] = pd.to_datetime(st.session_state.attendance_df['Date'])

# --- SIDEBAR FILTERS ---
df = st.session_state.attendance_df
st.sidebar.header("🔍 Global Filters")
filtered_df = df.copy()
if not df.empty:
    selected_dates = st.sidebar.date_input("Date Range", [df['Date'].min(), df['Date'].max()])
    if len(selected_dates) == 2:
        mask = (df['Date'].dt.date >= selected_dates[0]) & (df['Date'].dt.date <= selected_dates[1])
        filtered_df = df.loc[mask]

# --- TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📝 Data Entry", "📊 KPI", "📈 Trends", "🧑‍🤝‍🧑 Absence", "⚠️ Alerts", "📋 Action Tracking"])

with tab1:
    with st.expander("🏢 Department Management"):
        edited_depts = st.data_editor(st.session_state.departments_df, num_rows="dynamic", key="dept_editor")
        if st.button("💾 Save Departments"):
            st.session_state.departments_df = edited_depts
            st.session_state.departments_df.to_csv(DEPARTMENTS_FILE, index=False)
            st.success("Departments saved!")

    st.header("1. Operator Management")
    edited_ops = st.data_editor(st.session_state.operators_df, num_rows="dynamic", key="operator_editor")
    if st.button("💾 Save Operator List"):
        st.session_state.operators_df = edited_ops
        st.session_state.operators_df.to_csv(OPERATORS_FILE, index=False)
        # --- THE SYNC FIX ---
        st.session_state.attendance_df = sync_attendance_with_operators(st.session_state.attendance_df, st.session_state.operators_df)
        st.session_state.attendance_df.to_csv(ATTENDANCE_FILE, index=False)
        st.success("Operators saved and history synchronized!")

    st.header("2. Daily Attendance Entry")
    entry_date = st.date_input("Select Date to Edit", datetime.today().date())
    current_att = st.session_state.attendance_df[st.session_state.attendance_df['Date'].dt.date == entry_date].copy()
    if current_att.empty:
        current_att = st.session_state.operators_df.copy()
        current_att['Date'] = pd.to_datetime(entry_date)
        current_att['Status'], current_att['Late_Mins'], current_att['OT_Hours'], current_att['Shift Timing'] = 'Present', 0, 0, 'Day'
    
    edited_att = st.data_editor(current_att, key="attendance_editor")
    if st.button("💾 Save Daily Attendance"):
        other_dates = st.session_state.attendance_df[st.session_state.attendance_df['Date'].dt.date != entry_date]
        st.session_state.attendance_df = pd.concat([other_dates, edited_att], ignore_index=True)
        st.session_state.attendance_df.to_csv(ATTENDANCE_FILE, index=False)
        st.success(f"Attendance for {entry_date} saved!")

# --- TABS 2-6 (Your Original Logic) ---
with tab2:
    st.subheader("KPI Overview")
    if not filtered_df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Headcount", filtered_df['Emp_ID'].nunique())
        col2.metric("Total Shifts", len(filtered_df))
        col3.metric("Attendance Rate", f"{(len(filtered_df[filtered_df['Status'] == 'Present'])/len(filtered_df)*100):.1f}%")

with tab3:
    st.subheader("Trends & Shift Analysis")
    if not filtered_df.empty:
        fig = px.line(filtered_df.groupby(['Date', 'Status']).size().reset_index(name='Count'), x='Date', y='Count', color='Status')
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Absence & Performance")
    if not filtered_df.empty:
        st.bar_chart(filtered_df[filtered_df['Status'] != 'Present']['Status'].value_counts())

with tab5:
    st.subheader("Alerts & Exceptions")
    if not filtered_df.empty and (filtered_df['Status'] == 'ABS').any():
        st.warning("⚠️ Absence/No Show detected. Please follow up.")

with tab6:
    st.subheader("Action Tracking (CAPA)")
    if 'action_log' not in st.session_state:
        st.session_state.action_log = pd.read_csv(CAPA_FILE) if os.path.exists(CAPA_FILE) else pd.DataFrame(columns=["Issue", "Owner", "Status"])
    edited_capa = st.data_editor(st.session_state.action_log, num_rows="dynamic")
    if st.button("💾 Save Action Log"):
        st.session_state.action_log = edited_capa
        st.session_state.action_log.to_csv(CAPA_FILE, index=False)
        st.success("CAPA updated!")
