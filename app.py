
import pandas as pd
import streamlit as st

from database import (
    initialize_database,
    add_patient,
    get_patients,
    get_resources,
    update_resource,
    update_patient_status,
    delete_patient,
)
from workflow import process_patient


st.set_page_config(
    page_title="Hospital Flow Agent",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_database()

# ---------------- PAGE HEADER ----------------

st.title("🏥 Hospital Flow Agent")
st.caption(
    "AI-Powered Hospital Management and Patient Flow "
    "| University Project Prototype"
)

st.warning(
    "EDUCATIONAL DEMO ONLY — Do not enter real patient "
    "information. This application does not provide medical "
    "advice or validated clinical triage."
)

# ---------------- NAVIGATION ----------------

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Register Patient",
        "Patient Queue",
        "Resource Management",
        "Agent Workflow",
        "About Project",
    ],
)

st.sidebar.divider()
st.sidebar.caption("Hospital Flow Agent | Student Project")


# ---------------- DASHBOARD ----------------

if page == "Dashboard":
    patients = get_patients()
    resources = get_resources()

    st.header("Hospital Dashboard")
    st.write(
        "Monitor simulated patient records and hospital resources."
    )

    total_patients = len(patients)
    waiting = sum(p["status"] == "Waiting" for p in patients)
    under_review = sum(
        p["status"] == "Under Review" for p in patients
    )
    completed = sum(
        p["status"] == "Completed" for p in patients
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Patients", total_patients)
    c2.metric("Waiting Patients", waiting)
    c3.metric("Under Review", under_review)
    c4.metric("Completed", completed)

    st.divider()

    left, right = st.columns([1.2, 1])

    with left:
        st.subheader("Patient Queue")

        if patients:
            queue_data = [
                {
                    "Patient ID": p["patient_code"],
                    "Priority Flag": p["priority"],
                    "Status": p["status"],
                }
                for p in patients
            ]

            st.dataframe(
                pd.DataFrame(queue_data),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                "No patients registered yet. "
                "Use Register Patient to add demo records."
            )

    with right:
        st.subheader("Hospital Resources")

        if resources:
            chart_data = pd.DataFrame(
                {
                    "Available": {
                        r["name"]: r["available"]
                        for r in resources
                    },
                    "In Use": {
                        r["name"]: r["total"] - r["available"]
                        for r in resources
                    },
                }
            )

            st.bar_chart(chart_data)

            st.dataframe(
                pd.DataFrame(resources),
                use_container_width=True,
                hide_index=True,
            )

    st.caption(
        "All patient and resource figures are demonstration data."
    )


# ---------------- PATIENT REGISTRATION ----------------

elif page == "Register Patient":
    st.header("📝 Register a Patient")
    st.write("Register a simulated patient for the workflow demo.")

    with st.form("patient_registration", clear_on_submit=True):
        patient_code = st.text_input(
            "Patient ID",
            placeholder="DEMO-001",
        )

        age = st.number_input(
            "Age",
            min_value=0,
            max_value=120,
            value=25,
            step=1,
        )

        symptoms = st.text_area(
            "Symptoms (simulated demo text)",
            placeholder="Example: routine check-up",
        )

        submitted = st.form_submit_button(
            "Register Patient",
            type="primary",
        )

    if submitted:
        patient_code = patient_code.strip()
        symptoms = symptoms.strip()

        if not patient_code or not symptoms:
            st.error("Please enter both a patient ID and demo text.")
        else:
            try:
                result = process_patient(
                    patient_code,
                    int(age),
                    symptoms,
                )

                add_patient(
                    patient_code,
                    int(age),
                    symptoms,
                    result["priority"],
                )

                st.success("Demo patient registered successfully!")
                st.subheader("Workflow Report")
                st.code(result["final_report"])

            except Exception as error:
                if "UNIQUE constraint failed" in str(error):
                    st.error(
                        "That patient ID already exists. "
                        "Please use a different demo ID."
                    )
                else:
                    st.error(
                        "Registration failed. Check the app logs "
                        "for the technical error."
                    )


# ---------------- PATIENT QUEUE ----------------

elif page == "Patient Queue":
    st.header("📋 Patient Queue")

    patients = get_patients()

    if not patients:
        st.info("No patients registered yet.")
    else:
        st.dataframe(
            pd.DataFrame(patients),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Update Demonstration Status")

        patient_ids = [p["patient_code"] for p in patients]

        selected_id = st.selectbox(
            "Select patient",
            patient_ids,
        )

        new_status = st.selectbox(
            "New status",
            ["Waiting", "Under Review", "Completed"],
        )

        if st.button("Update Status", type="primary"):
            update_patient_status(selected_id, new_status)
            st.success("Patient demonstration status updated.")
            st.rerun()

        st.divider()
        st.subheader("Delete a Demo Record")

        delete_id = st.selectbox(
            "Select record to delete",
            patient_ids,
            key="delete_patient_id",
        )

        if st.button("Delete Demo Record"):
            delete_patient(delete_id)
            st.success("Demo record deleted.")
            st.rerun()

    st.caption(
        "Statuses and priority flags are for demonstration only. "
        "They do not determine real clinical urgency."
    )


# ---------------- RESOURCE MANAGEMENT ----------------

elif page == "Resource Management":
    st.header("🛏️ Resource Management")
    st.write("Update the simulated hospital resource inventory.")

    resources = get_resources()

    for resource in resources:
        with st.expander(resource["name"]):
            with st.form(f"resource_form_{resource['name']}"):
                total = st.number_input(
                    "Total units",
                    min_value=0,
                    value=int(resource["total"]),
                    step=1,
                    key=f"total_{resource['name']}",
                )

                available = st.number_input(
                    "Available units",
                    min_value=0,
                    max_value=int(total),
                    value=min(
                        int(resource["available"]),
                        int(total),
                    ),
                    step=1,
                    key=f"available_{resource['name']}",
                )

                save = st.form_submit_button("Save Resource")

            if save:
                update_resource(
                    resource["name"],
                    int(total),
                    int(available),
                )
                st.success("Resource counts saved.")
                st.rerun()

    st.subheader("Current Resource Summary")
    st.dataframe(
        pd.DataFrame(get_resources()),
        use_container_width=True,
        hide_index=True,
    )


# ---------------- AGENT WORKFLOW ----------------

elif page == "Agent Workflow":
    st.header("🤖 LangGraph Agent Workflow")
    st.write(
        "Run the workflow using simulated patient information."
    )

    with st.form("workflow_demo"):
        code = st.text_input(
            "Demo patient ID",
            value="TEST-001",
        )

        age = st.number_input(
            "Age",
            min_value=0,
            max_value=120,
            value=30,
        )

        symptoms = st.text_area(
            "Simulated symptoms",
            value="routine check-up",
        )

        run_workflow = st.form_submit_button(
            "Run LangGraph Workflow",
            type="primary",
        )

    if run_workflow:
        if not code.strip() or not symptoms.strip():
            st.error("Please fill in all fields.")
        else:
            try:
                with st.spinner("Running workflow..."):
                    result = process_patient(
                        code.strip(),
                        int(age),
                        symptoms.strip(),
                    )

                st.success("Workflow completed.")
                st.subheader("Workflow Result")

                a, b = st.columns(2)

                a.metric(
                    "Demonstration Flag",
                    result["priority"],
                )

                b.metric(
                    "Workflow Nodes",
                    3,
                )

                st.subheader("Resource Summary")
                st.write(result["resource_summary"])

                st.subheader("Final Report")
                st.code(result["final_report"])

            except Exception:
                st.error(
                    "Workflow failed. Check the Streamlit logs "
                    "for the technical error."
                )


# ---------------- ABOUT ----------------

elif page == "About Project":
    st.header("About Hospital Flow Agent")

    st.markdown("""
    ### Problem Statement
    Hospital staff need a clear overview of simulated patient
    queues and resource availability.

    ### Objectives
    - Register and store demonstration patient records.
    - Monitor waiting and completed records.
    - Track hospital resource counts.
    - Demonstrate a LangGraph-based workflow.
    - Display information through a web dashboard.

    ### Technologies
    - Python
    - Streamlit
    - SQLite
    - Pandas
    - LangGraph

    ### Workflow
    Patient Intake → Resource Monitoring → Coordinator → Report

    ### Limitations
    This is an academic prototype using demonstration rules and
    data. It is not a medical diagnosis or clinical triage system.
    """)
