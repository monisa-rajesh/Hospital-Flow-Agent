
import pandas as pd
import streamlit as st
import uuid
from langgraph.types import Command


from database import (
    initialize_database,
    add_patient,
    get_patients,
    get_resources,
    update_resource,
    update_patient_status,
    delete_patient,
    get_departments,
    get_beds,
    recommend_bed,
    assign_bed,
    recommend_department,
    discharge_patient,
    get_discharges,
    request_transfer,
    get_transfers,
    update_transfer_status,
    get_notifications,
    mark_notification_read,
    refresh_resource_alerts,
)
from bed_allocation_agent import (
    recommend_bed_for_patient,
    confirm_bed_assignment,
)
from workflow import process_patient
from bed_workflow import bed_workflow



st.set_page_config(
    page_title="Agentic AI for Autonomous Hospital Flow and Resource Management",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_database()

# ---------------- PAGE HEADER ----------------

st.title("🏥 Agentic AI for Autonomous Hospital Flow and Resource Management")
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
        "Bed Allocation",
        "Department Routing",
        "Discharge & Transfers",
        "Notifications",
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
    
    # ---------------- AI OPERATIONS SUMMARY ----------------

    st.divider()
    st.header("🤖 AI Hospital Operations Summary")

    st.write(
        "Use the Agentic AI workflow to analyze the simulated "
        "patient queue and hospital resources."
    )

    if patients:
        patient_options = {
            f"{p['patient_code']} — {p['status']}": p
            for p in patients
        }

        selected_patient_label = st.selectbox(
            "Select a demo patient for analysis",
            list(patient_options.keys()),
            key="dashboard_ai_patient",
        )

        selected_patient = patient_options[selected_patient_label]

        if st.button(
            "Generate AI Operations Summary",
            type="primary",
            key="dashboard_generate_ai",
        ):
            try:
                with st.spinner(
                    "Running LangGraph, MCP, A2A and local Ollama..."
                ):
                    result = process_patient(
                        selected_patient["patient_code"],
                        int(selected_patient["age"]),
                        selected_patient["symptoms"],
                    )

                st.session_state["dashboard_ai_result"] = result

            except Exception as error:
                st.error(f"AI workflow failed: {error}")

        ai_result = st.session_state.get("dashboard_ai_result")

        if ai_result:
            st.subheader("AI-Generated Summary")
            st.markdown(
                ai_result.get(
                    "ai_summary",
                    "No AI summary was returned by the workflow.",
                )
            )

            with st.expander("View MCP data"):
                st.code(ai_result.get("mcp_summary", "No MCP data"))

            with st.expander("View A2A response"):
                st.code(ai_result.get("a2a_summary", "No A2A response"))

            with st.expander("View complete workflow report"):
                st.code(ai_result.get("final_report", "No final report"))

    else:
        st.info(
            "Register a demonstration patient first to generate "
            "an AI operations summary."
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

                st.subheader("🤖 AI Operations Summary")
                st.markdown(
                    result.get(
                        "ai_summary",
                        "No AI summary was returned.",
                    )
                )

                with st.expander("Complete Workflow Report"):
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
        # Beds must be managed individually
        if resource["name"] == "Beds":
            continue

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

    # Bed inventory section — outside the loop
    st.subheader("Bed Management")

    beds = get_beds()

    st.dataframe(
        pd.DataFrame(beds),
        use_container_width=True,
        hide_index=True,
    )

    resources = get_resources()
    bed_resource = next(
        (r for r in resources if r["name"] == "Beds"),
        None,
    )

    if bed_resource:
        st.metric(
            "Available Beds",
            f"{bed_resource['available']} / {bed_resource['total']}",
        )

    st.info(
        "Manage individual beds through the Bed Allocation page. "
        "Bed counts are synchronized automatically."
    )

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
                    6,
                )

                
                st.subheader("Hospital Resource Summary")
                st.write(result["resource_summary"])

                st.divider()
                st.subheader("🤖 Ollama AI Operations Summary")

                st.markdown(
                    result.get(
                        "ai_summary",
                        "No AI summary was returned.",
                    )
                )

                with st.expander("MCP — Resources and Patient Queue"):
                    st.code(
                        result.get("mcp_summary", "No MCP data returned.")
                    )

                with st.expander("A2A — Operations Agent Response"):
                    st.code(
                        result.get("a2a_summary", "No A2A response returned.")
                    )

                with st.expander("Complete Final Workflow Report"):
                    st.code(result["final_report"])

                st.caption(
                    "This is an educational demonstration. "
                    "AI-generated summaries are not clinical advice."
                )


            except Exception:
                st.error(
                    "Workflow failed. Check the Streamlit logs "
                    "for the technical error."
                )


# ---------------- BED ALLOCATION ----------------


elif page == "Bed Allocation":
    st.header("🛏️ Bed Allocation Agent")
    st.write(
        "Find a matching available bed and assign it "
        "after staff confirmation."
    )

    patients = [
        p for p in get_patients()
        if p["status"] not in (
            "Completed",
            "Transferred",
            "Discharged",
        )
    ]

    departments = get_departments()
    beds = get_beds()

    if not patients:
        st.info("Register a demonstration patient first.")
    elif not departments:
        st.warning("No active departments are configured.")
    else:
        patient_options = {
            p["patient_code"]: p for p in patients
        }

        selected_patient_code = st.selectbox(
            "Select patient",
            list(patient_options.keys()),
            key="booking_patient",
        )

        department_names = [
            d["name"] for d in departments
        ]

        selected_department = st.selectbox(
            "Department",
            department_names,
            key="booking_department",
        )

        bed_type = st.selectbox(
            "Bed type",
            ["General", "Private", "ICU"],
            key="booking_bed_type",
        )

        if st.button(
            "Find Available Bed",
            type="primary",
            key="find_booking_bed",
        ):
            result = recommend_bed_for_patient(
                patient_code=selected_patient_code,
                department=selected_department,
                bed_type=bed_type,
            )

            st.session_state["bed_recommendation"] = (
                result if result["success"] else None
            )
            st.session_state["bed_recommendation_message"] = (
                result["message"]
            )
            st.session_state["bed_recommendation_patient"] = (
                selected_patient_code
            )

        recommendation = st.session_state.get(
            "bed_recommendation"
        )
        message = st.session_state.get(
            "bed_recommendation_message"
        )

        if message:
            if recommendation:
                st.success(message)

                bed = recommendation["recommendation"]

                st.write("**Recommended bed details**")
                st.write(f"Bed code: {bed['bed_code']}")
                st.write(f"Department: {bed['department']}")
                st.write(f"Bed type: {bed['bed_type']}")

                st.warning(
                    "Confirm only after the responsible staff "
                    "member has reviewed the proposed assignment."
                )

                confirmed = st.checkbox(
                    "I confirm this simulated bed assignment "
                    "after staff review.",
                    key="confirm_booking",
                )

                if st.button(
                    "Confirm and Assign Bed",
                    type="primary",
                    key="confirm_booking_button",
                    disabled=not confirmed,
                ):
                    try:
                        # Re-check the bed immediately before assignment.
                        current_beds = get_beds()
                        current_bed = next(
                            (
                                b for b in current_beds
                                if b["bed_code"] == bed["bed_code"]
                            ),
                            None,
                        )

                        if (
                            not current_bed
                            or current_bed["status"] != "Available"
                            or current_bed["department"]
                            != selected_department
                            or current_bed["bed_type"] != bed_type
                        ):
                            st.error(
                                "This bed is no longer available "
                                "or no longer matches. Find another bed."
                            )
                            st.session_state[
                                "bed_recommendation"
                            ] = None
                        else:
                            confirm_bed_assignment(
                                selected_patient_code,
                                bed["bed_code"],
                            )

                            # Verify the saved database state.
                            verified_beds = get_beds()
                            assigned_bed = next(
                                (
                                    b for b in verified_beds
                                    if b["bed_code"] == bed["bed_code"]
                                ),
                                None,
                            )

                            if (
                                assigned_bed
                                and assigned_bed["status"] == "Occupied"
                                and assigned_bed["patient_code"]
                                == selected_patient_code
                            ):
                                st.session_state[
                                    "bed_recommendation"
                                ] = None
                                st.session_state[
                                    "bed_recommendation_message"
                                ] = None
                                st.success(
                                    f"Bed {bed['bed_code']} assigned "
                                    f"to {selected_patient_code} "
                                    "and verified successfully."
                                )
                                st.rerun()
                            else:
                                st.error(
                                    "Assignment could not be verified. "
                                    "Check the bed inventory before retrying."
                                )

                    except Exception as error:
                        st.error(f"Bed assignment failed: {error}")

            else:
                st.warning(message)

    st.divider()
    st.subheader("Current Bed Inventory")

    st.dataframe(
        get_beds(),
        use_container_width=True,
        hide_index=True,
    )


# ---------------- DEPARTMENT ROUTING ----------------

elif page == "Department Routing":
    st.header("🧭 Department Routing")
    st.caption(
        "Keyword-based educational suggestions only; "
        "not a medical assessment."
    )

    symptoms = st.text_area(
        "Enter simulated request text",
        placeholder="Example: routine consultation",
    )

    if st.button("Suggest Department", type="primary"):
        if not symptoms.strip():
            st.warning("Enter demo text first.")
        else:
            result = recommend_department(symptoms)
            st.session_state["department_result"] = result

    result = st.session_state.get("department_result")
    if result:
        st.info(f"Suggested department: {result['department']}")
        st.write(f"Reason: {result['reason']}")
        st.warning("Staff review is required before acting on this suggestion.")

    st.subheader("Configured Departments")
    st.dataframe(get_departments(), use_container_width=True, hide_index=True)


# ---------------- DISCHARGE AND TRANSFERS ----------------

elif page == "Discharge & Transfers":
    st.header("🚪 Discharge & Transfers")
    patients = get_patients()

    active_patients = [
        p for p in patients
        if p["status"] not in ("Completed", "Transferred", "Discharged")
    ]

    if not active_patients:
        st.info("No active demo patient records are available.")
    else:
        patient_codes = [p["patient_code"] for p in active_patients]
        selected_patient = st.selectbox(
            "Select patient",
            patient_codes,
            key="discharge_transfer_patient",
        )

        st.subheader("Record Discharge")
        discharge_reason = st.text_input(
            "Discharge reason (demo)",
            key="discharge_reason",
        )

        discharge_confirm = st.checkbox(
            "Confirm this simulated discharge has been reviewed.",
            key="discharge_confirm",
        )

        if st.button("Record Discharge"):
            if not discharge_confirm:
                st.warning("Confirm the review checkbox first.")
            else:
                try:
                    discharge_patient(selected_patient, discharge_reason)
                    st.success("Discharge recorded.")
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

        st.divider()
        st.subheader("Request Department Transfer")

        departments = [
            d["name"] for d in get_departments()
        ]

        destination = st.selectbox(
            "Destination department",
            departments,
            key="transfer_destination",
        )
        transfer_reason = st.text_input(
            "Transfer reason (demo)",
            key="transfer_reason",
        )

        if st.button("Submit Transfer Request"):
            try:
                transfer_id = request_transfer(
                    selected_patient,
                    destination,
                    transfer_reason,
                )
                st.success(f"Transfer request #{transfer_id} recorded.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))

    st.subheader("Transfer Requests")

    transfers = get_transfers()
    if transfers:
        st.dataframe(transfers, use_container_width=True, hide_index=True)

        pending = [
            t for t in transfers
            if t["status"] in ("Requested", "Approved")
        ]

        if pending:
            transfer_ids = [t["id"] for t in pending]
            selected_transfer = st.selectbox(
                "Select transfer request",
                transfer_ids,
            )
            transfer_status = st.selectbox(
                "Update transfer status",
                ["Approved", "Completed", "Cancelled"],
            )

            if st.button("Update Transfer"):
                try:
                    update_transfer_status(
                        selected_transfer,
                        transfer_status,
                    )
                    st.success("Transfer status updated.")
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
    else:
        st.info("No transfer requests yet.")

    st.subheader("Discharge History")
    st.dataframe(
        get_discharges(),
        use_container_width=True,
        hide_index=True,
    )


# ---------------- NOTIFICATIONS ----------------

elif page == "Notifications":
    st.header("🔔 Hospital Notifications")

    if st.button("Check Resource Levels"):
        alerts = refresh_resource_alerts()
        if alerts:
            st.warning(f"{len(alerts)} low-resource alert(s) created.")
        else:
            st.success("No resources are below the configured threshold.")

    notifications = get_notifications()

    if notifications:
        for notification in notifications:
            with st.container(border=True):
                st.write(
                    f"**{notification['severity']} — "
                    f"{notification['category']}**"
                )
                st.write(notification["message"])
                st.caption(str(notification["created_at"]))

                if not notification["is_read"]:
                    if st.button(
                        "Mark as read",
                        key=f"read_notification_{notification['id']}",
                    ):
                        mark_notification_read(notification["id"])
                        st.rerun()
    else:
        st.info("No notifications have been generated.")

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
    - Streamlit — interactive hospital dashboard
    - SQLite — local demonstration database
    - Pandas — tabular data and charts
    - LangGraph — workflow orchestration
    - MCP — resource and patient-queue tools
    - A2A — communication with the Hospital Operations Agent
    - Ollama — local AI-generated summaries
    - LangChain ecosystem — local AI integration where configured

    ### Agentic AI Workflow
    1. Patient Intake: processes demonstration patient information.
    2. Resource Monitor: reads the simulated hospital inventory.
    3. MCP Monitor: retrieves resource and patient-queue data.
    4. A2A Operations Agent: requests an operations response.
    5. Ollama AI Summary: generates a natural-language summary locally.
    6. Coordinator: combines the workflow outputs into a final report.

    ### Limitations
    This is an academic prototype using simulated data and
    demonstration rules. AI-generated summaries may be incorrect.
    It does not provide medical diagnosis or validated clinical triage.
    """)
