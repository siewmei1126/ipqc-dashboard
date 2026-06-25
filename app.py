import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import random
from datetime import datetime, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Advanced IPQC Attendance Dashboard", layout="wide")
st.title("🏭 Advanced IPQC Attendance & Workforce Dashboard")

# --- 1. MOCK DATA GENERATION (To populate the new features) ---
@st.cache_data
def generate_mock_data():
    dates = [datetime.today().date() - timedelta(days=x) for x in range(30)]
    departments = ["IPQC Line 1", "IPQC Line 2", "QA Check", "Final Insp"]
    shifts = ["A (Morning)", "B (Morning)", "C (Night)", "D (Night)"]
    supervisors = ["John Doe", "Jane Smith", "Alan Turing", "Grace Hopper"]
    statuses = ["Present", "Present", "Present", "Present", "MC", "AL", "EL", "Unplanned", "No Show"]
    
    data = []
    for _ in range(500):  # 500 random attendance records
        status = random.choice(statuses)
        is_present = status == "Present"
        data.append({
            "Date": random.choice(dates),
            "Emp_ID": f"EMP{random.randint(1000, 1050)}",
            "Name": f"Operator {random.randint(1, 50)}",
            "Department": random.choice(departments),
            "Shift": random.choice(shifts),
            "Supervisor": random.choice(supervisors),
            "Status": status,
            "Late_Mins": random.randint(10, 120) if is_present and random.random() > 0.8 else 0,
            "OT_Hours": random.randint(1, 4) if is_present and random.random() > 0.7 else 0,
            "Target_Attendance": 95.0
        })
    df = pd.DataFrame(data).sort_values(by="Date", ascending=False)
    # Convert Date to datetime format for plotting
    df['Date'] = pd.to_datetime(df['Date'])
    return df

df = generate_mock_data()

# --- 2. SIDEBAR FILTERS ---
st.sidebar.header("🔍 Global Filters")
selected_dates = st.sidebar.date_input("Date Range", [df['Date'].min(), df['Date'].max()])
selected_depts = st.sidebar.multiselect("Department", df['Department'].unique(), default=df['Department'].unique())
selected_shifts = st.sidebar.multiselect("Shift", df['Shift'].unique(), default=df['Shift'].unique())
selected_sups = st.sidebar.multiselect("Supervisor", df['Supervisor'].unique(), default=df['Supervisor'].unique())

# Apply Filters
if len(selected_dates) == 2:
    start_date, end_date = selected_dates
    mask = (df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date) & \
           (df['Department'].isin(selected_depts)) & \
           (df['Shift'].isin(selected_shifts)) & \
           (df['Supervisor'].isin(selected_sups))
    filtered_df = df.loc[mask]
else:
    filtered_df = df.copy()

# --- 3. DASHBOARD TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 KPI Overview", 
    "📈 Trends & Shift Analysis", 
    "🧑‍🤝‍🧑 Absence & Performance", 
    "⚠️ Alerts & Exceptions", 
    "📋 Action Tracking"
])

# --- TAB 1: KPI OVERVIEW ---
with tab1:
    st.subheader("1. Attendance Overview (KPI Summary)")
    
    # Calculate KPIs
    total_headcount = len(filtered_df)
    present_count = len(filtered_df[filtered_df['Status'] == 'Present'])
    absent_count = total_headcount - present_count
    
    att_rate = (present_count / total_headcount * 100) if total_headcount > 0 else 0
    abs_rate = 100 - att_rate
    late_count = len(filtered_df[filtered_df['Late_Mins'] > 0])
    late_rate = (late_count / present_count * 100) if present_count > 0 else 0
    total_ot = filtered_df['OT_Hours'].sum()
    no_show_count = len(filtered_df[filtered_df['Status'] == 'No Show'])
    leave_util = len(filtered_df[filtered_df['Status'].isin(['AL', 'MC', 'EL'])]) / total_headcount * 100 if total_headcount > 0 else 0

    # Display Metrics in Columns
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Headcount (Scheduled)", f"{total_headcount}")
    col2.metric("Present Employees", f"{present_count}")
    col3.metric("Attendance Rate", f"{att_rate:.1f}%", delta=f"{att_rate - 95:.1f}% vs Target", delta_color="normal")
    col4.metric("Absenteeism Rate", f"{abs_rate:.1f}%")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Late Arrival Rate", f"{late_rate:.1f}%")
    col6.metric("Total Overtime (Hours)", f"{total_ot} hrs")
    col7.metric("Leave Utilization", f"{leave_util:.1f}%")
    col8.metric("No Show Cases", f"{no_show_count}", delta="Requires Action!" if no_show_count > 0 else "Good", delta_color="inverse")

# --- TAB 2: TRENDS & SHIFT ANALYSIS ---
with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Daily Attendance Trend")
        trend_df = filtered_df.groupby(['Date', 'Status']).size().reset_index(name='Count')
        fig_trend = px.line(trend_df, x='Date', y='Count', color='Status', title="Daily Status Breakdown")
        st.plotly_chart(fig_trend, use_container_width=True)
        
    with col2:
        st.subheader("Attendance by Department")
        dept_df = filtered_df[filtered_df['Status'] == 'Present'].groupby('Department').size().reset_index(name='Present Count')
        fig_dept = px.bar(dept_df, x='Department', y='Present Count', title="Present Headcount by Dept", color='Department')
        st.plotly_chart(fig_dept, use_container_width=True)

    st.subheader("Attendance by Shift & Manpower Shortage")
    shift_df = filtered_df.groupby(['Shift', 'Status']).size().reset_index(name='Count')
    fig_shift = px.bar(shift_df, x='Shift', y='Count', color='Status', barmode='group', title="Shift Breakdown")
    st.plotly_chart(fig_shift, use_container_width=True)

# --- TAB 3: ABSENCE & PERFORMANCE ANALYSIS ---
with tab3:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Absence Breakdown by Reason")
        absent_df = filtered_df[filtered_df['Status'] != 'Present']
        reason_counts = absent_df['Status'].value_counts().reset_index()
        reason_counts.columns = ['Reason', 'Count']
        fig_pie = px.pie(reason_counts, names='Reason', values='Count', hole=0.4, title="Leave/Absence Distribution")
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col2:
        st.subheader("Employee Attendance Performance (Bottom 5)")
        # Calculate individual absence counts
        emp_absences = absent_df.groupby(['Name', 'Emp_ID']).size().reset_index(name='Absence Days')
        emp_absences = emp_absences.sort_values(by='Absence Days', ascending=False).head(5)
        st.dataframe(emp_absences, use_container_width=True)
        
        st.subheader("Top Late Arrivals")
        late_emps = filtered_df[filtered_df['Late_Mins'] > 0].groupby(['Name']).agg({'Late_Mins': 'sum', 'Date':'count'})
        late_emps.columns = ['Total Late Mins', 'Frequency']
        late_emps = late_emps.sort_values(by='Total Late Mins', ascending=False).head(5)
        st.dataframe(late_emps, use_container_width=True)

# --- TAB 4: ALERTS & EXCEPTIONS ---
with tab4:
    st.subheader("⚠️ Automated Exception Alerts")
    
    # Alert 1: Low Attendance
    if att_rate < 90:
        st.error(f"🔴 CRITICAL: Overall attendance rate is at {att_rate:.1f}%, below the 90% threshold target.")
    else:
        st.success(f"🟢 Overall attendance rate is healthy ({att_rate:.1f}%).")
        
    # Alert 2: No Shows
    if no_show_count > 0:
        st.warning(f"🟠 WARNING: Detected {no_show_count} 'No Show' case(s). Immediate supervisor follow-up required.")
        no_show_df = filtered_df[filtered_df['Status'] == 'No Show'][['Date', 'Name', 'Department', 'Supervisor']]
        st.dataframe(no_show_df, hide_index=True)
        
    # Alert 3: High Latenss
    high_late_count = len(filtered_df[filtered_df['Late_Mins'] > 30])
    if high_late_count > 0:
        st.info(f"🟡 NOTICE: {high_late_count} instances of employees arriving more than 30 minutes late.")

# --- TAB 5: ACTION TRACKING (CAPA) ---
with tab5:
    st.subheader("📋 Corrective & Preventive Action (CAPA) Tracking")
    st.write("Log issues identified from the dashboard, assign owners, and track completion.")
    
    if 'action_log' not in st.session_state:
        df_log = pd.DataFrame({
            "Issue Identified": ["High 'No Show' in Night Shift C", "Line 1 Manpower Shortage"],
            "Root Cause": ["Transport delay", "Flu outbreak"],
            "Corrective Action": ["Coordinate with bus vendor", "Approve OT for Line 2 to cover"],
            "Owner": ["Jane Smith", "John Doe"],
            "Target Date": ["2026-06-30", "2026-06-26"],
            "Status": ["Open", "In Progress"]
        })
        # Fix: Convert the text strings to actual Python date objects so Streamlit's DateColumn can read them
        df_log['Target Date'] = pd.to_datetime(df_log['Target Date']).dt.date
        st.session_state.action_log = df_log
        
    # Editable Dataframe for CAPA
    edited_log = st.data_editor(
        st.session_state.action_log, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Status": st.column_config.SelectboxColumn("Status", options=["Open", "In Progress", "Closed"]),
            "Target Date": st.column_config.DateColumn("Target Date")
        }
    )
    st.session_state.action_log = edited_log
