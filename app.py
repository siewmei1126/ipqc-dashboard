import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, timedelta

# --- FILE PATHS ---
OPERATORS_FILE = "operators.csv"
ATTENDANCE_FILE = "attendance.csv"
DEPARTMENTS_FILE = "departments.csv"
CAPA_FILE = "capa_log.csv"

st.set_page_config(page_title="Advanced IPQC Dashboard", layout="wide")
st.title("🏭 Advanced IPQC Attendance & Workforce Dashboard")

# --- INITIALIZATION ---
if 'operators_df' not in st.session_state:
    if os.path.exists(OPERATORS_FILE):
        st.session_state.operators_df = pd.read_csv(OPERATORS_FILE, dtype={'Emp_ID': str})
    else:
        st.session_state.operators_df = pd.DataFrame(columns=["Emp_ID", "Name", "Department", "Shift Group", "Supervisor"])

if 'departments_df' not in st.session_state:
    if os.path.exists(DEPARTMENTS_FILE):
        st.session_state.departments_df = pd.read_csv(DEPARTMENTS_FILE)
    else:
        st.session_state.departments_df = pd.DataFrame(columns=["Department"])

if 'attendance_df' not in st.session_state:
    if os.path.exists(ATTENDANCE_FILE):
        st.session_state.attendance_df = pd.read_csv(ATTENDANCE_FILE)
        st.session_state.attendance_df['Date'] = pd.to_datetime(st.session_state.attendance_df['Date'], errors='coerce')
    else:
        st.session_state.attendance_df = pd.DataFrame()

if 'action_log' not in st.session_state:
    if os.path.exists(CAPA_FILE):
        st.session_state.action_log = pd.read_csv(CAPA_FILE)
    else:
        st.session_state.action_log = pd.DataFrame(columns=["Issue Identified", "Root Cause", "Owner", "Status"])

# --- HELPER FUNCTIONS ---
def sync_attendance_with_operators():
    if st.session_state.attendance_df.empty: return
    dates = st.session_state.attendance_df['Date'].dropna().unique()
    new_records = []
    for date in dates:
        for _, op in st.session_state.operators_df.iterrows():
            exists = st.session_state.attendance_df[
                (st.session_state.attendance_df['Date'] == date) & 
                (st.session_state.attendance_df['Emp_ID'] == str(op['Emp_ID']))
            ]
            if exists.empty:
                new_records.append({
                    "Date": date, "Emp_ID": str(op['Emp_ID']), "Name": op['Name'], 
                    "Department": op['Department'], "Shift Group": op['Shift Group'],
                    "Status": "Present", "Late_Mins": 0, "OT_Hours": 0
                })
    if new_records:
        st.session_state.attendance_df = pd.concat([st.session_state.attendance_df, pd.DataFrame(new_records)], ignore_index=True)
        st.session_state.attendance_df.to_csv(ATTENDANCE_FILE, index=False)

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Operators & Depts", "Attendance Entry", "KPIs & Trends", "Exceptions", "CAPA Tracking"])

with tab1:
    st.header("Department Management")
    edited_depts = st.data_editor(st.session_state.departments_df, num_rows="dynamic")
    if st.button("Save Departments"):
        st.session_state.departments_df = edited_depts
        edited_depts.to_csv(DEPARTMENTS_FILE, index=False)
        st.rerun()

    st.header("Operator Master List")
    edited_ops = st.data_editor(
        st.session_state.operators_df, num_rows="dynamic",
        column_config={"Department": st.column_config.SelectboxColumn(options=st.session_state.departments_df['Department'].tolist())}
    )
    if st.button("Save Operators & Sync"):
        st.session_state.operators_df = edited_ops
        edited_ops.to_csv(OPERATORS_FILE, index=False)
        sync_attendance_with_operators()
        st.rerun()

with tab2:
    selected_date = st.date_input("Select Date", datetime.today())
    day_df = st.session_state.attendance_df[st.session_state.attendance_df['Date'].dt.date == selected_date].copy()
    if day_df.empty:
        day_df = st.session_state.operators_df.copy()
        day_df['Date'] = pd.to_datetime(selected_date)
        day_df['Status'] = "Present"
    edited_att = st.data_editor(day_df, hide_index=True)
    if st.button("Save Daily Attendance"):
        other = st.session_state.attendance_df[st.session_state.attendance_df['Date'].dt.date != selected_date]
        st.session_state.attendance_df = pd.concat([other, edited_att], ignore_index=True)
        st.session_state.attendance_df.to_csv(ATTENDANCE_FILE, index=False)
        st.success("Saved!")

with tab3:
    st.header("📊 KPI & Trends")
    if not st.session_state.attendance_df.empty:
        df = st.session_state.attendance_df
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Headcount", df['Emp_ID'].nunique())
        col2.metric("Total Present", len(df[df['Status']=='Present']))
        col3.metric("Total Absent", len(df[df['Status']=='ABS']))
        
        st.subheader("Trend Analysis")
        fig = px.line(df.groupby(['Date', 'Status']).size().reset_index(name='Count'), x='Date', y='Count', color='Status')
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.header("⚠️ Exception Alerts")
    absent = st.session_state.attendance_df[st.session_state.attendance_df['Status'] == 'ABS']
    if not absent.empty:
        st.warning(f"Alert: {len(absent)} No-Show cases found.")
        st.dataframe(absent)
    else:
        st.success("No exceptions found.")

with tab5:
    st.header("📋 CAPA Tracking")
    edited_log = st.data_editor(st.session_state.action_log, num_rows="dynamic")
    if st.button("Save Action Log"):
        st.session_state.action_log = edited_log
        edited_log.to_csv(CAPA_FILE, index=False)
        st.success("Saved!")
