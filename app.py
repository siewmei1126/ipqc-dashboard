import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image

# Set page layout to wide for dashboard viewing
st.set_page_config(layout="wide", page_title="IPQC Attendance Dashboard")

st.title("IPQC Attendance & Shift Roster Dashboard")

# --- 1. OPERATOR MANAGEMENT ---
st.header("1. Operator Management")
st.write("Add, remove, or update operator names and shift assignments.")

# Initialize a default dataframe in session state if it doesn't exist
if 'operators_df' not in st.session_state:
    st.session_state.operators_df = pd.DataFrame({
        "Name": ["Luqman", "Mohd Azim", "Yogany", "Rizwan", "Siti nur Fatihah"],
        "EMP #": ["508939", "512047", "511634", "512416", "508578"],
        "Shift Group": ["A", "A", "B", "C", "D"]
    })

# The st.data_editor allows you to add/delete rows dynamically like Excel
edited_operators = st.data_editor(
    st.session_state.operators_df, 
    num_rows="dynamic", 
    use_container_width=True
)
st.session_state.operators_df = edited_operators

st.markdown("---")

# --- 2. CALENDAR UPLOAD & PARSING ---
st.header("2. Auto-Read Shift Pattern")
uploaded_calendar = st.file_uploader("Upload the Work Roster Screenshot (e.g., TF AMD 2026 Roster)", type=["png", "jpg", "jpeg"])

@st.cache_data
def extract_roster_data(image_file):
    """
    In a production environment, you would send this image to a Vision API 
    (e.g., Gemini 1.5 Pro) with a prompt to return a JSON mapping of:
    { "YYYY-MM-DD": {"Day": "A", "Night": "C"} }
    For this prototype, we return a mock dictionary based on WW14-WW26 patterns.
    """
    # Mock data simulating a successful Vision API extraction
    return {
        "2026-05-14": {"Day": "D", "Night": "C"},
        "2026-05-15": {"Day": "D", "Night": "C"},
        "2026-05-16": {"Day": "A", "Night": "B"},
        "2026-05-17": {"Day": "A", "Night": "B"}
    }

if uploaded_calendar:
    image = Image.open(uploaded_calendar)
    st.image(image, caption="Uploaded Calendar", width=600)
    
    with st.spinner("Extracting shift patterns using Vision API..."):
        shift_schedule = extract_roster_data(uploaded_calendar)
        st.success("Shift pattern extracted successfully!")
        
        # Display the parsed schedule
        schedule_df = pd.DataFrame(shift_schedule).T.reset_index()
        schedule_df.columns = ["Date", "Day Shift Group", "Night Shift Group"]
        st.dataframe(schedule_df, use_container_width=True)

st.markdown("---")

# --- 3. ATTENDANCE TRACKING & OVERRIDES ---
st.header("3. Daily Attendance Tracking")
st.write("The system auto-populates 'M' or 'N' based on the roster. You can override with MC, AL, OTM, etc.")

# Generate the attendance grid based on the operators and the parsed dates
if uploaded_calendar:
    # Get active dates from the parsed schedule
    active_dates = list(shift_schedule.keys())
    
    # Create an empty attendance matrix
    attendance_data = []
    
    for _, row in st.session_state.operators_df.iterrows():
        emp_record = {"Name": row["Name"], "EMP #": row["EMP #"], "Shift": row["Shift Group"]}
        
        # Auto-fill logic
        for date in active_dates:
            day_group = shift_schedule[date]["Day"]
            night_group = shift_schedule[date]["Night"]
            
            if row["Shift Group"] == day_group:
                emp_record[date] = "M"
            elif row["Shift Group"] == night_group:
                emp_record[date] = "N"
            else:
                emp_record[date] = "" # Rest day
                
        attendance_data.append(emp_record)
        
    attendance_df = pd.DataFrame(attendance_data)
    
    # Make the generated matrix editable for exceptions (MC, AL, OT)
    final_attendance = st.data_editor(attendance_df, use_container_width=True)
    
    # --- 4. VISUALIZATION (Plotly) ---
    st.subheader("Attendance Status Breakdown")
    # Flatten the dataframe to count attendance codes
    melted_df = final_attendance.melt(id_vars=["Name", "EMP #", "Shift"], value_vars=active_dates, var_name="Date", value_name="Status")
    status_counts = melted_df[melted_df["Status"] != ""].groupby("Status").size().reset_index(name="Count")
    
    fig = px.bar(status_counts, x="Status", y="Count", color="Status", title="Total Attendance Codes (M, N, MC, AL)")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Please upload a calendar screenshot to generate the attendance grid.")
