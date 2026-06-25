import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# --- FILE PATHS FOR SAVING DATA ---
OPERATORS_FILE = "operators.csv"
ATTENDANCE_FILE = "attendance.csv"
CAPA_FILE = "capa_log.csv"
DEPARTMENTS_FILE = "departments.csv" # New file for custom departments

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Advanced IPQC Attendance Dashboard", layout="wide")
st.title("🏭 Advanced IPQC Attendance & Workforce Dashboard")

# --- 1. INITIALIZE PERSISTENT DATA STATE ---

# Initialize Departments
if 'departments_df' not in st.session_state:
    if os.path.exists(DEPARTMENTS_FILE):
        st.session_state.departments_df = pd.read_csv(DEPARTMENTS_FILE)
    else:
        st.session_state.departments_df = pd.DataFrame({
            "Department": ["IPQC Line 1", "IPQC Line 2", "QA Check", "Final Insp"]
        })

# Initialize Operators
if 'operators_df' not in st.session_state:
    if os.path.exists(OPERATORS_FILE):
        # Load from saved file if it exists
        st.session_state.operators_df = pd.read_csv(OPERATORS_FILE, dtype={"Emp_ID": str})
    else:
        # Default starting data
        st.session_state.operators_df = pd.DataFrame({
            "Emp_ID": ["508939", "512047", "511634", "512416", "508578"],
            "Name": ["Luqman", "Mohd Azim", "Yogany", "Rizwan", "Siti nur Fatihah"],
            "Department": ["IPQC Line 1", "IPQC Line 1", "IPQC Line 2", "QA Check", "Final Insp"],
            "Shift Group": ["A", "A", "B", "C", "D"],
            "Supervisor": ["John Doe", "John Doe", "Jane Smith", "Alan Turing", "Grace Hopper"]
        })

# Initialize Attendance
if 'attendance_df' not in st.session_state:
    if os.path.exists(ATTENDANCE_FILE):
        # Load saved attendance data
        st.session_state.attendance_df = pd.read_csv(ATTENDANCE_FILE)
        st.session_state.attendance_df['Date'] = pd.to_datetime(st.session_state.attendance_df['Date'])
    else:
        # Generate 7 days of historical baseline data so charts aren't empty on first load
        base_data = []
        for i in range(7):
            date = datetime.today().date() - timedelta(days=i)
            for _, op in st.session_state.operators_df.iterrows():
                base_data.append({
                    "Date": pd.to_datetime(date),
                    "Emp_ID": op["Emp_ID"],
                    "Name": op["Name"],
                    "Department": op["Department"],
                    "Shift Group": op["Shift Group"],
                    "Shift Timing": "Day" if op["Shift Group"] in ["A", "C"] else "Night",
                    "Supervisor": op["Supervisor"],
                    "Status": "Present",
                    "Late_Mins": 0,
                    "OT_Hours": 0
                })
        st.session_state.attendance_df = pd.DataFrame(base_data)

# Ensure Date column is always datetime format
st.session_state.attendance_df['Date'] = pd.to_datetime(st.session_state.attendance_df['Date'])

# --- 2. SIDEBAR FILTERS ---
df = st.session_state.attendance_df
st.sidebar.header("🔍 Global Filters")

# Only show filters if we have data
if not df.empty:
    selected_dates = st.sidebar.date_input("Date Range", [df['Date'].min(), df['Date'].max()])
    
    # Use the active departments from our state for the filter options
    dept_options = st.session_state.departments_df['Department'].tolist()
    # Also include any old departments that might be in historical data but were removed
    all_depts = list(set(df['Department'].unique().tolist() + dept_options))
    
    selected_depts = st.sidebar.multiselect("Department", all_depts, default=all_depts)
    selected_shifts = st.sidebar.multiselect("Shift Group", df['Shift Group'].unique(), default=df['Shift Group'].unique())
    selected_sups = st.sidebar.multiselect("Supervisor", df['Supervisor'].unique(), default=df['Supervisor'].unique())

    # Apply Filters
    if len(selected_dates) == 2:
        start_date, end_date = selected_dates
        mask = (df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date) & \
               (df['Department'].isin(selected_depts)) & \
               (df['Shift Group'].isin(selected_shifts)) & \
               (df['Supervisor'].isin(selected_sups))
        filtered_df = df.loc[mask]
    else:
        filtered_df = df.copy()
else:
    filtered_df = df.copy()

# --- 3. DASHBOARD TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📝 Data Entry & Operators",
    "📊 KPI Overview", 
    "📈 Trends & Shift Analysis", 
    "🧑‍🤝‍🧑 Absence & Performance", 
    "⚠️ Alerts & Exceptions", 
    "📋 Action Tracking"
])

# --- TAB 1: DATA ENTRY & OPERATOR MANAGEMENT ---
with tab1:
    
    with st.expander("🏢 Department Management", expanded=False):
        st.write("Add, rename, or remove departments. This updates the dropdown in the Operator list.")
        edited_depts = st.data_editor(
            st.session_state.departments_df,
            num_rows="dynamic",
            key="dept_editor",
            use_container_width=True
        )
        if st.button("💾 Save Departments"):
            st.session_state.departments_df = edited_depts
            st.session_state.departments_df.to_csv(DEPARTMENTS_FILE, index=False)
            st.success("Department list saved!")

    st.header("1. Operator Management")
    st.write("Add or remove operators and assign their Shift Group and Department.")
    
    # Get the latest list of departments for the dropdown
    current_dept_list = st.session_state.departments_df['Department'].tolist()
    
    # Using a key here prevents the table from blanking out when typing the first time
    edited_ops = st.data_editor(
        st.session_state.operators_df, 
        num_rows="dynamic", 
        use_container_width=True,
        key="operator_editor",
        column_config={
            "Shift Group": st.column_config.SelectboxColumn("Shift Group", options=["A", "B", "C", "D"]),
            "Department": st.column_config.SelectboxColumn("Department", options=current_dept_list)
        }
    )
    
    # Instantly update session memory to prevent wipe on refresh
    st.session_state.operators_df = edited_ops
    
    # Save button to commit operator changes to a permanent file
    if st.button("💾 Save Operator List"):
        st.session_state.operators_df.to_csv(OPERATORS_FILE, index=False)
        st.success("Operator list saved! Your changes will now remain even if you refresh the page.")
    
    st.markdown("---")
    
    st.header("2. Daily Attendance Entry")
    entry_date = st.date_input("Select Date to Input/Edit Attendance", datetime.today().date())
    
    # Get existing records for this date
    current_att = st.session_state.attendance_df[st.session_state.attendance_df['Date'].dt.date == entry_date].copy()
    
    # If no records exist for this date, pre-populate using the current operators list
    if current_att.empty and not st.session_state.operators_df.empty:
        current_att = st.session_state.operators_df.copy()
        current_att['Date'] = pd.to_datetime(entry_date)
        current_att['Shift Timing'] = "Day" # Default, user can change to Night
        current_att['Status'] = "Present"
        current_att['Late_Mins'] = 0
        current_att['OT_Hours'] = 0
        # Reorder columns to match main dataframe
        current_att = current_att[["Date", "Emp_ID", "Name", "Department", "Shift Group", "Shift Timing", "Supervisor", "Status", "Late_Mins", "OT_Hours"]]

    st.write(f"Keying in attendance for: **{entry_date}**")
    
    edited_att = st.data_editor(
        current_att,
        use_container_width=True,
        hide_index=True,
        key="attendance_editor",
        column_config={
            "Date": st.column_config.Column(disabled=True),
            "Emp_ID": st.column_config.Column(disabled=True),
            "Name": st.column_config.Column(disabled=True),
            "Shift Timing": st.column_config.SelectboxColumn(
                "Shift Timing", help="Day or Night Shift", options=["Day", "Night", "Off"]
            ),
            "Status": st.column_config.SelectboxColumn(
                "Attendance Status",
                options=["Present", "PH", "AL", "UPL", "EL", "OTM", "OTN", "MC", "SD", "HL", "ABS"],
                required=True
            ),
            "Late_Mins": st.column_config.NumberColumn("Late (Mins)", min_value=0),
            "OT_Hours": st.column_config.NumberColumn("OT (Hours)", min_value=0)
        }
    )
    
    if st.button("💾 Save Daily Attendance", type="primary"):
        # Remove old records for this date and append the new edited records
        other_dates_df = st.session_state.attendance_df[st.session_state.attendance_df['Date'].dt.date != entry_date]
        st.session_state.attendance_df = pd.concat([other_dates_df, edited_att], ignore_index=True)
        # Save to permanent file
        st.session_state.attendance_df.to_csv(ATTENDANCE_FILE, index=False)
        st.success(f"Attendance for {entry_date} saved successfully! KPIs have been updated.")

# --- TAB 2: KPI OVERVIEW ---
with tab2:
    st.subheader("Attendance Overview (KPI Summary)")
    
    if not filtered_df.empty:
        # Define Status Groups based on user remark request
        working_statuses = ["Present", "OTM", "OTN"]
        leave_statuses = ["AL", "UPL", "EL", "MC", "HL"]
        exempt_statuses = ["PH", "SD"]
        
        # HEADCOUNT FIX: Use actual unique employees instead of record count
        actual_headcount = filtered_df['Emp_ID'].nunique()
        total_shift_records = len(filtered_df)
        
        present_count = len(filtered_df[filtered_df['Status'].isin(working_statuses)])
        absent_count = len(filtered_df[filtered_df['Status'].isin(leave_statuses + ["ABS"])])
        exempt_count = len(filtered_df[filtered_df['Status'].isin(exempt_statuses)])
        
        scheduled_shifts = total_shift_records - exempt_count
        
        att_rate = (present_count / scheduled_shifts * 100) if scheduled_shifts > 0 else 0
        abs_rate = 100 - att_rate if att_rate > 0 else 0
        
        late_count = len(filtered_df[filtered_df['Late_Mins'] > 0])
        late_rate = (late_count / present_count * 100) if present_count > 0 else 0
        total_ot = filtered_df['OT_Hours'].sum()
        no_show_count = len(filtered_df[filtered_df['Status'] == 'ABS'])
        leave_util = len(filtered_df[filtered_df['Status'].isin(leave_statuses)]) / total_shift_records * 100 if total_shift_records > 0 else 0

        # Display Metrics in Columns
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Employees (Headcount)", f"{actual_headcount}", help="Actual number of unique employees in this filter.")
        col2.metric("Total Shifts Worked", f"{present_count}", help="Total number of working shifts recorded in this time range.")
        col3.metric("Attendance Rate", f"{att_rate:.1f}%", delta=f"{att_rate - 95:.1f}% vs Target", delta_color="normal")
        col4.metric("Absenteeism Rate", f"{abs_rate:.1f}%")

        col5, col6, col7, col8 = st.columns(4)
        col5.metric("Late Arrival Rate", f"{late_rate:.1f}%")
        col6.metric("Total Overtime (Hours)", f"{total_ot} hrs")
        col7.metric("Leave Utilization", f"{leave_util:.1f}%")
        col8.metric("No Show Cases (ABS)", f"{no_show_count}", delta="Requires Action!" if no_show_count > 0 else "Good", delta_color="inverse")
    else:
        st.info("No attendance data found for the selected filters. Please enter data in Tab 1.")

# --- TAB 3: TRENDS & SHIFT ANALYSIS ---
with tab3:
    if not filtered_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Daily Attendance Trend")
            trend_df = filtered_df.groupby(['Date', 'Status']).size().reset_index(name='Count')
            fig_trend = px.line(trend_df, x='Date', y='Count', color='Status', title="Daily Status Breakdown")
            st.plotly_chart(fig_trend, use_container_width=True)
            
        with col2:
            st.subheader("Attendance by Department")
            dept_df = filtered_df[filtered_df['Status'].isin(["Present", "OTM", "OTN"])].groupby('Department').size().reset_index(name='Present Count')
            if not dept_df.empty:
                fig_dept = px.bar(dept_df, x='Department', y='Present Count', title="Present Headcount by Dept", color='Department')
                st.plotly_chart(fig_dept, use_container_width=True)
            else:
                st.write("No present employees for this selection.")

        st.subheader("Attendance by Shift Group & Manpower Shortage")
        shift_df = filtered_df.groupby(['Shift Group', 'Status']).size().reset_index(name='Count')
        fig_shift = px.bar(shift_df, x='Shift Group', y='Count', color='Status', barmode='group', title="Shift Breakdown")
        st.plotly_chart(fig_shift, use_container_width=True)

# --- TAB 4: ABSENCE & PERFORMANCE ANALYSIS ---
with tab4:
    if not filtered_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Absence Breakdown by Reason")
            absent_df = filtered_df[filtered_df['Status'].isin(["AL", "UPL", "EL", "MC", "HL", "ABS"])]
            reason_counts = absent_df['Status'].value_counts().reset_index()
            reason_counts.columns = ['Reason', 'Count']
            
            if not reason_counts.empty:
                fig_pie = px.pie(reason_counts, names='Reason', values='Count', hole=0.4, title="Leave/Absence Distribution")
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.success("No absences recorded for this period!")
            
        with col2:
            st.subheader("Employee Attendance Performance (Bottom 5)")
            if not absent_df.empty:
                emp_absences = absent_df.groupby(['Name', 'Emp_ID']).size().reset_index(name='Absence Days')
                emp_absences = emp_absences.sort_values(by='Absence Days', ascending=False).head(5)
                st.dataframe(emp_absences, hide_index=True, use_container_width=True)
            else:
                st.write("No absences to display.")
            
            st.subheader("Top Late Arrivals")
            late_emps = filtered_df[filtered_df['Late_Mins'] > 0].groupby(['Name']).agg({'Late_Mins': 'sum', 'Date':'count'})
            if not late_emps.empty:
                late_emps.columns = ['Total Late Mins', 'Frequency']
                late_emps = late_emps.sort_values(by='Total Late Mins', ascending=False).head(5)
                st.dataframe(late_emps, use_container_width=True)
            else:
                st.write("No late arrivals recorded.")

# --- TAB 5: ALERTS & EXCEPTIONS ---
with tab5:
    st.subheader("⚠️ Automated Exception Alerts")
    if not filtered_df.empty:
        # Alert 1: Low Attendance
        if att_rate < 90:
            st.error(f"🔴 CRITICAL: Overall attendance rate is at {att_rate:.1f}%, below the 90% threshold target.")
        else:
            st.success(f"🟢 Overall attendance rate is healthy ({att_rate:.1f}%).")
            
        # Alert 2: No Shows (ABS)
        if no_show_count > 0:
            st.warning(f"🟠 WARNING: Detected {no_show_count} 'ABS' (Absence/No Show) case(s). Immediate supervisor follow-up required.")
            no_show_df = filtered_df[filtered_df['Status'] == 'ABS'][['Date', 'Name', 'Department', 'Supervisor']]
            st.dataframe(no_show_df, hide_index=True)
            
        # Alert 3: High Latenss
        high_late_count = len(filtered_df[filtered_df['Late_Mins'] > 30])
        if high_late_count > 0:
            st.info(f"🟡 NOTICE: {high_late_count} instances of employees arriving more than 30 minutes late.")
    else:
         st.write("No data available to generate alerts.")

# --- TAB 6: ACTION TRACKING (CAPA) ---
with tab6:
    st.subheader("📋 Corrective & Preventive Action (CAPA) Tracking")
    st.write("Log issues identified from the dashboard, assign owners, and track completion.")
    
    if 'action_log' not in st.session_state:
        if os.path.exists(CAPA_FILE):
            df_log = pd.read_csv(CAPA_FILE)
            df_log['Target Date'] = pd.to_datetime(df_log['Target Date']).dt.date
            st.session_state.action_log = df_log
        else:
            df_log = pd.DataFrame({
                "Issue Identified": ["High 'ABS' in Night Shift C", "Line 1 Manpower Shortage"],
                "Root Cause": ["Transport delay", "Flu outbreak"],
                "Corrective Action": ["Coordinate with bus vendor", "Approve OT for Line 2 to cover"],
                "Owner": ["Jane Smith", "John Doe"],
                "Target Date": ["2026-06-30", "2026-06-26"],
                "Status": ["Open", "In Progress"]
            })
            df_log['Target Date'] = pd.to_datetime(df_log['Target Date']).dt.date
            st.session_state.action_log = df_log
        
    edited_log = st.data_editor(
        st.session_state.action_log, 
        num_rows="dynamic", 
        use_container_width=True,
        key="capa_editor",
        column_config={
            "Status": st.column_config.SelectboxColumn("Status", options=["Open", "In Progress", "Closed"]),
            "Target Date": st.column_config.DateColumn("Target Date")
        }
    )
    
    # Save button for CAPA tracking
    if st.button("💾 Save Action Log"):
        st.session_state.action_log = edited_log
        st.session_state.action_log.to_csv(CAPA_FILE, index=False)
        st.success("Action tracking log saved permanently!")
