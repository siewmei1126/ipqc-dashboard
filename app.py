import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

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
st.set_page_config(page_title="Advanced IPQC Dashboard", layout="wide")
st.title("🏭 Advanced IPQC Attendance & Workforce Dashboard")

# --- INITIALIZE DATA ---
if 'departments_df' not in st.session_state:
    st.session_state.departments_df = pd.read_csv(DEPARTMENTS_FILE) if os.path.exists(DEPARTMENTS_FILE) else pd.DataFrame({"Department": ["IPQC Line 1", "IPQC Line 2", "QA Check", "Final Insp"]})

if 'operators_df' not in st.session_state:
    st.session_state.operators_df = pd.read_csv(OPERATORS_FILE, dtype={"Emp_ID": str}) if os.path.exists(OPERATORS_FILE) else pd.DataFrame({"Emp_ID": ["508939"], "Name": ["Luqman"], "Department": ["IPQC Line 1"], "Shift Group": ["A"], "Supervisor": ["John Doe"]})

if 'attendance_df' not in st.session_state:
    cols = ["Date", "Emp_ID", "Name", "Department", "Shift Group", "Shift Timing", "Supervisor", "Status", "Late_Mins", "OT_Hours"]
    if os.path.exists(ATTENDANCE_FILE):
        st.session_state.attendance_df = pd.read_csv(ATTENDANCE_FILE)
    else:
        st.session_state.attendance_df = pd.DataFrame(columns=cols)

# FORCE DATETIME FORMAT
st.session_state.attendance_df['Date'] = pd.to_datetime(st.session_state.attendance_df['Date'], errors='coerce')

# --- SIDEBAR FILTERS ---
df = st.session_state.attendance_df
st.sidebar.header("🔍 Global Filters")
filtered_df = df.copy()
if not df.empty:
    selected_dates = st.sidebar.date_input("Date Range", [df['Date'].min().date() if pd.notnull(df['Date'].min()) else datetime.today(), df['Date'].max().date() if pd.notnull(df['Date'].max()) else datetime.today()])
    if len(selected_dates) == 2:
        mask = (df['Date'].dt.date >= selected_dates[0]) & (df['Date'].dt.date <= selected_dates[1])
        filtered_df = df.loc[mask]

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
        st.success("Operators saved and history synced!")

    st.header("2. Daily Attendance Entry")
    entry_date = st.date_input("Select Date", datetime.today().date())
    current_att = st.session_state.attendance_df[st.session_state.attendance_df['Date'].dt.date == entry_date].copy()
    if current_att.empty:
        current_att = st.session_state.operators_df.copy()
        current_att['Date'] = pd.to_datetime(entry_date)
        current_att[['Status', 'Late_Mins', 'OT_Hours', 'Shift Timing']] = ['Present', 0, 0, 'Day']
    
    edited_att = st.data_editor(current_att, key="attendance_editor")
    if st.button("💾 Save Daily Attendance"):
        other_dates = st.session_state.attendance_df[st.session_state.attendance_df['Date'].dt.date != entry_date]
        st.session_state.attendance_df = pd.concat([other_dates, edited_att], ignore_index=True)
        st.session_state.attendance_df.to_csv(ATTENDANCE_FILE, index=False)
        st.success("Attendance saved!")

# --- TABS 2-6 ---
with tab2:
    st.subheader("KPI Overview")
    if not filtered_df.empty:
        col1, col2 = st.columns(2)
        col1.metric("Total Unique Employees", filtered_df['Emp_ID'].nunique())
        col2.metric("Attendance Rate", f"{(len(filtered_df[filtered_df['Status'] == 'Present'])/len(filtered_df)*100):.1f}%")

with tab3:
    if not filtered_df.empty:
        st.plotly_chart(px.line(filtered_df.groupby(['Date', 'Status']).size().reset_index(name='Count'), x='Date', y='Count', color='Status'), use_container_width=True)

with tab4:
    if not filtered_df.empty:
        st.bar_chart(filtered_df[filtered_df['Status'] != 'Present']['Status'].value_counts())

with tab5:
    if not filtered_df.empty and (filtered_df['Status'] == 'ABS').any():
        st.warning("⚠️ ABSENCE DETECTED")

with tab6:
    st.subheader("📋 CAPA Tracking")
    # Corrected usage of os.path.exists here:
    if 'action_log' not in st.session_state:
        st.session_state.action_log = pd.read_csv(CAPA_FILE) if os.path.exists(CAPA_FILE) else pd.DataFrame(columns=["Issue", "Owner", "Status"])
    
    st.session_state.action_log = st.data_editor(st.session_state.action_log, num_rows="dynamic")
    if st.button("💾 Save CAPA"):
        st.session_state.action_log.to_csv(CAPA_FILE, index=False)
        st.success("CAPA updated!")
