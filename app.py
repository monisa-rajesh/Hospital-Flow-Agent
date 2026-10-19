
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Hospital Flow Agent",
    page_icon="🏥",
    layout="wide",
)

st.title("🏥 Hospital Flow Agent")
st.subheader("AI-Powered Hospital Management Dashboard")
st.caption("University Project | Educational Prototype")

st.success("Hospital Flow Agent dashboard is running!")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Patients", 25)
col2.metric("Waiting Patients", 12)
col3.metric("Available Beds", 8)
col4.metric("Available Doctors", 4)

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Patient Queue")

    patients = pd.DataFrame([
        {"Patient ID": "DEMO-001", "Status": "Waiting"},
        {"Patient ID": "DEMO-002", "Status": "Under Review"},
        {"Patient ID": "DEMO-003", "Status": "Waiting"},
    ])

    st.dataframe(
        patients,
        use_container_width=True,
        hide_index=True,
    )

with right:
    st.subheader("Hospital Resources")

    resources = pd.DataFrame({
        "Available": [8, 4, 12, 6],
        "In Use": [12, 6, 8, 4],
    }, index=["Beds", "Doctors", "Nurses", "Wheelchairs"])

    st.bar_chart(resources)

st.divider()
st.info(
    "This dashboard uses sample data for demonstration. "
    "It does not make clinical decisions."
)
