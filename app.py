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

# --- SYNC LOGIC (THE ENHANCEMENT) ---
def sync_attendance_with_operators(attendance_df, operators_df):
    if attendance_df.empty: return attendance_df
    dates = attendance_df['Date'].unique()
    updated_records = []
    for d in dates:
        daily_snapshot = attendance_df[attendance_df['Date'] == d]
        # Merge ensures operator details stay in sync with the Master List
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

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Advanced IPQC Attendance Dashboard", layout="wide")
st.title("🏭 Advanced IPQC Attendance & Workforce Dashboard")

# --- 1. INITIALIZE PERSISTENT DATA STATE ---
if 'departments_df' not in st.session_state:
    if os.path.exists(DEPARTMENTS_FILE):
        st.session_state.departments_df = pd.read_csv(DEPARTMENTS_FILE)
    else:
        st.session_state.departments_df = pd.DataFrame({"Department": ["IPQC Line 1", "IPQC Line 2", "QA Check", "Final Insp"]})

if 'operators_df' not in st.session_state:
    if os.path.exists(OPERATORS_FILE):
        st.session_state.operators_df = pd.read_csv(OPERATORS_FILE, dtype={"Emp_ID": str})
    else:
        st.session_state.operators_df = pd.DataFrame({
            "Emp_ID": ["508939", "512047", "511634", "512416", "508578"],
            "Name": ["Luqman", "Mohd Azim", "Yogany", "Rizwan", "Siti nur Fatihah"],
            "Department": ["IPQC Line 1", "IPQC Line 1", "IPQC Line 2", "QA Check", "Final Insp"],
            "Shift Group": ["A", "A", "B", "C", "D"],
            "Supervisor": ["John Doe", "John Doe", "Jane Smith", "Alan Turing", "Grace Hopper"]
        })

if 'attendance_df' not in st.session_state:
    if os.path.exists(ATTENDANCE_FILE):
        st.session_state.attendance_df = pd.read_csv(ATTENDANCE_FILE)
        st.session_state.attendance_df['Date'] = pd.to_datetime(st.session_state.attendance_df['Date'])
    else:
        # Default baseline data
        st.session_state.attendance_df = pd.DataFrame() 

# --- 2. SIDEBAR FILTERS ---
df = st.session_state.attendance_df
st.sidebar.header("🔍 Global Filters")

if not df.empty:
    selected_dates = st.sidebar.date_input("Date Range", [df['Date'].min(), df['Date'].max()])
    dept_options = st.session_state.departments_df['Department'].tolist()
    all_depts = list(set(df['Department'].unique().tolist() + dept_options))
    selected_depts = st.sidebar.multiselect("Department", all_depts, default=all_depts)
    selected_shifts = st.sidebar.multiselect("Shift Group", df['Shift Group'].unique(), default=df['Shift Group'].unique())
    selected_sups = st.sidebar.multiselect("Supervisor", df['Supervisor'].unique(), default=df['Supervisor'].unique())

    if len(selected_dates) == 2:
        start_date, end_date = selected_dates
        mask = (df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date) & \
               (df['Department'].isin(selected_depts)) & \
               (df['Shift Group'].isin(selected_shifts)) & \
               (df['Supervisor'].isin(selected_sups))
        filtered_df = df.loc[mask]
    else: filtered_df = df.copy()
else: filtered_df = df.copy()

# --- 3. DASHBOARD TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📝 Data Entry & Operators", "📊 KPI Overview", "📈 Trends & Shift Analysis", 
    "🧑‍🤝‍🧑 Absence & Performance", "⚠️ Alerts & Exceptions", "📋 Action Tracking"
])

# --- TAB 1: DATA ENTRY ---
with tab1:
    with st.expander("🏢 Department Management"):
        edited_depts = st.data_editor(st.session_state.departments_df, num_rows="dynamic", key="dept_editor")
        if st.button("💾 Save Departments"):
            st.session_state.departments_df = edited_depts
            st.session_state.departments_df.to_csv(DEPARTMENTS_FILE, index=False)
            st.success("Department list saved!")

    st.header("1. Operator Management")
    edited_ops = st.data_editor(st.session_state.operators_df, num_rows="dynamic", key="operator_editor")
    if st.button("💾 Save Operator List"):
        st.session_state.operators_df = edited_ops
        st.session_state.operators_df.to_csv(OPERATORS_FILE, index=False)
        # Apply Synchronization
        st.session_state.attendance_df = sync_attendance_with_operators(st.session_state.attendance_df, st.session_state.operators_df)
        st.session_state.attendance_df.to_csv(ATTENDANCE_FILE, index=False)
        st.success("Operators saved and history synchronized!")

    st.header("2. Daily Attendance Entry")
    entry_date = st.date_input("Select Date to Input/Edit Attendance", datetime.today().date())
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

# --- TABS 2-6 (Your original code preserved exactly) ---
with tab2:
    st.subheader("Attendance Overview (KPI Summary)")
    if not filtered_df.empty:
        working_statuses = ["Present", "OTM", "OTN"]
        leave_statuses = ["AL", "UPL", "EL", "MC", "HL"]
        exempt_statuses = ["PH", "SD"]
        actual_headcount = filtered_df['Emp_ID'].nunique()
        total_shift_records = len(filtered_df)
        present_count = len(filtered_df[filtered_df['Status'].isin(working_statuses)])
        exempt_count = len(filtered_df[filtered_df['Status'].isin(exempt_statuses)])
        scheduled_shifts = total_shift_records - exempt_count
        att_rate = (present_count / scheduled_shifts * 100) if scheduled_shifts > 0 else 0
        abs_rate = 100 - att_rate if att_rate > 0 else 0
        late_count = len(filtered_df[filtered_df['Late_Mins'] > 0])
        late_rate = (late_count / present_count * 100) if present_count > 0 else 0
        total_ot = filtered_df['OT_Hours'].sum()
        no_show_count = len(filtered_df[filtered_df['Status'] == 'ABS'])
        leave_util = len(filtered_df[filtered_df['Status'].isin(leave_statuses)]) / total_shift_records * 100 if total_shift_records > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Employees", f"{actual_headcount}")
        col2.metric("Total Shifts Worked", f"{present_count}")
        col3.metric("Attendance Rate", f"{att_rate:.1f}%")
        col4.metric("Absenteeism Rate", f"{abs_rate:.1f}%")
        col5, col6, col7, col8 = st.columns(4)
        col5.metric("Late Arrival Rate", f"{late_rate:.1f}%")
        col6.metric("Total Overtime", f"{total_ot} hrs")
        col7.metric("Leave Utilization", f"{leave_util:.1f}%")
        col8.metric("No Show Cases", f"{no_show_count}")

with tab3:
    if not filtered_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Daily Attendance Trend")
            trend_df = filtered_df.groupby(['Date', 'Status']).size().reset_index(name='Count')
            st.plotly_chart(px.line(trend_df, x='Date', y='Count', color='Status'), use_container_width=True)
        with col2:
            st.subheader("Attendance by Department")
            dept_df = filtered_df[filtered_df['Status'].isin(["Present", "OTM", "OTN"])].groupby('Department').size().reset_index(name='Present Count')
            st.plotly_chart(px.bar(dept_df, x='Department', y='Present Count'), use_container_width=True)

with tab4:
    if not filtered_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Absence Breakdown")
            absent_df = filtered_df[filtered_df['Status'].isin(["AL", "UPL", "EL", "MC", "HL", "ABS"])]
            st.plotly_chart(px.pie(absent_df['Status'].value_counts().reset_index(), names='index', values='Status'), use_container_width=True)
        with col2:
            st.subheader("Top Late Arrivals")
            late_emps = filtered_df[filtered_df['Late_Mins'] > 0].groupby('Name')['Late_Mins'].sum().sort_values(ascending=False).head(5)
            st.dataframe(late_emps)

with tab5:
    st.subheader("⚠️ Automated Exception Alerts")
    if not filtered_df.empty:
        no_show_count = len(filtered_df[filtered_df['Status'] == 'ABS'])
        if no_show_count > 0: st.warning(f"Detected {no_show_count} 'ABS' cases.")

with tab6:
    st.subheader("📋 Corrective & Preventive Action (CAPA)")
    if 'action_log' not in st.session_state:
        st.session_state.action_log = pd.read_csv(CAPA_FILE) if os.path.exists(CAPA_FILE) else pd.DataFrame(columns=["Issue", "Root Cause", "Corrective Action", "Owner", "Target Date", "Status"])
    st.session_state.action_log = st.data_editor(st.session_state.action_log, num_rows="dynamic")
    if st.button("💾 Save Action Log"):
        st.session_state.action_log.to_csv(CAPA_FILE, index=False)
        st.success("CAPA log saved!")
