import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os

# --- FILE PATHS ---
OPERATORS_FILE = "operators.csv"
ATTENDANCE_FILE = "attendance.csv"
CAPA_FILE = "capa_log.csv"
DEPARTMENTS_FILE = "departments.csv"

# --- SYNC LOGIC ---
def sync_attendance_with_operators(attendance_df, operators_df):
    """Updates historical attendance records with current operator details."""
    if attendance_df.empty: return attendance_df
    
    dates = attendance_df['Date'].unique()
    updated_records = []
    
    for d in dates:
        daily_snapshot = attendance_df[attendance_df['Date'] == d]
        merged = pd.merge(
            operators_df[['Emp_ID', 'Name', 'Department', 'Shift Group', 'Supervisor']],
            daily_snapshot[['Date', 'Emp_ID', 'Status', 'Late_Mins', 'OT_Hours', 'Shift Timing']],
            on='Emp_ID',
            how='left'
        )
        merged['Date'] = d
        merged['Status'] = merged['Status'].fillna('Present')
        merged['Late_Mins'] = merged['Late_Mins'].fillna(0)
        merged['OT_Hours'] = merged['OT_Hours'].fillna(0)
        merged['Shift Timing'] = merged['Shift Timing'].fillna("Day")
        updated_records.append(merged)
        
    return pd.concat(updated_records, ignore_index=True)

# --- PAGE CONFIGURATION ---
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
if not df.empty:
    selected_dates = st.sidebar.date_input("Date Range", [df['Date'].min(), df['Date'].max()])
    selected_depts = st.sidebar.multiselect("Department", df['Department'].unique(), default=df['Department'].unique())
    mask = (df['Date'].dt.date >= selected_dates[0]) & (df['Date'].dt.date <= selected_dates[1]) & (df['Department'].isin(selected_depts))
    filtered_df = df.loc[mask]
else:
    filtered_df = df.copy()

# --- TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📝 Data Entry", "📊 KPI", "📈 Trends", "🧑‍🤝‍🧑 Absence", "⚠️ Alerts", "📋 CAPA"])

with tab1:
    with st.expander("🏢 Department Management"):
        edited_depts = st.data_editor(st.session_state.departments_df, num_rows="dynamic")
        if st.button("💾 Save Departments"):
            st.session_state.departments_df = edited_depts
            st.session_state.departments_df.to_csv(DEPARTMENTS_FILE, index=False)
            st.rerun()

    st.header("1. Operator Management")
    edited_ops = st.data_editor(st.session_state.operators_df, num_rows="dynamic", key="operator_editor")
    if st.button("💾 Save Operator List"):
        st.session_state.operators_df = edited_ops
        st.session_state.operators_df.to_csv(OPERATORS_FILE, index=False)
        st.session_state.attendance_df = sync_attendance_with_operators(st.session_state.attendance_df, st.session_state.operators_df)
        st.session_state.attendance_df.to_csv(ATTENDANCE_FILE, index=False)
        st.success("Changes saved and history synchronized!")

    st.header("2. Daily Attendance Entry")
    entry_date = st.date_input("Select Date", datetime.today().date())
    current_att = st.session_state.attendance_df[st.session_state.attendance_df['Date'].dt.date == entry_date].copy()
    if current_att.empty:
        current_att = st.session_state.operators_df.copy()
        current_att['Date'] = pd.to_datetime(entry_date)
        current_att['Status'] = 'Present'
        current_att['Late_Mins'] = 0
        current_att['OT_Hours'] = 0
        current_att['Shift Timing'] = 'Day'
    
    edited_att = st.data_editor(current_att, use_container_width=True)
    if st.button("💾 Save Daily Attendance"):
        other_dates = st.session_state.attendance_df[st.session_state.attendance_df['Date'].dt.date != entry_date]
        st.session_state.attendance_df = pd.concat([other_dates, edited_att], ignore_index=True)
        st.session_state.attendance_df.to_csv(ATTENDANCE_FILE, index=False)
        st.success("Attendance saved!")

# (Include your existing code for Tab 2-6 here...)
