import streamlit as st
from src.common.common import page_setup, page_header
from src.UmetaFlowTOPPWorkflow import Workflow

# The rest of the page can, but does not have to be changed
params = page_setup()

page_header(
    "Run UmetaFlow",
    "Start/stop the workflow and monitor logs. Settings and parameters are saved in your workspace.",
    badges=[f"Workspace: {st.session_state.workspace.name}"],
)

wf = Workflow(st.session_state["workspace"])

wf.show_execution_section()

