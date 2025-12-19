import json
import os
import shutil
import sys
import uuid
import time
from typing import Any
from pathlib import Path
from streamlit.components.v1 import html

import streamlit as st
import pandas as pd

try:
    from tkinter import Tk, filedialog

    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

from src.common.captcha_ import captcha_control

# Detect system platform
OS_PLATFORM = sys.platform


def inject_tailwind_flowbite_ui() -> None:
    """
    Inject a Tailwind/Flowbite-inspired modern UI layer into the Streamlit app.

    Notes
    - Streamlit does not support a traditional Tailwind build pipeline here.
      We load Flowbite's prebuilt CSS and apply a custom design system on top
      via CSS selectors + small helper classes for consistent layout.
    - This function is safe to call multiple times (idempotent in practice).
    """
    # External stylesheets (Flowbite). Tailwind utility generation via CDN script
    # is not reliably supported inside Streamlit, so we lean on Flowbite CSS +
    # custom app CSS below.
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/flowbite/2.5.2/flowbite.min.css" rel="stylesheet" />
        <style>
          :root{
            --uf-bg: #0b1020;
            --uf-bg2: #0f172a;          /* slate-900 */
            --uf-card: rgba(17, 24, 39, 0.72); /* gray-900 @ 72% */
            --uf-card-border: rgba(148, 163, 184, 0.16); /* slate-400 @ 16% */
            --uf-text: #e5e7eb;         /* gray-200 */
            --uf-muted: #94a3b8;        /* slate-400 */
            --uf-brand: #6366f1;        /* indigo-500 */
            --uf-brand2: #22d3ee;       /* cyan-400 */
            --uf-success: #22c55e;      /* green-500 */
            --uf-warning: #f59e0b;      /* amber-500 */
            --uf-danger: #ef4444;       /* red-500 */
            --uf-radius: 16px;
          }

          html, body, [class*="css"]  {
            font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
          }

          /* App background */
          div[data-testid="stAppViewContainer"]{
            background:
              radial-gradient(1200px 600px at 10% 0%, rgba(99,102,241,0.25), rgba(0,0,0,0) 60%),
              radial-gradient(1200px 600px at 90% 10%, rgba(34,211,238,0.18), rgba(0,0,0,0) 55%),
              linear-gradient(180deg, var(--uf-bg) 0%, var(--uf-bg2) 100%);
            color: var(--uf-text);
          }

          /* Remove Streamlit default menu/footer clutter */
          #MainMenu {visibility: hidden;}
          footer {visibility: hidden;}
          header {visibility: hidden;}

          /* Sidebar */
          section[data-testid="stSidebar"]{
            background: linear-gradient(180deg, rgba(17,24,39,0.85), rgba(15,23,42,0.95));
            border-right: 1px solid rgba(148,163,184,0.12);
          }
          section[data-testid="stSidebar"] * { color: var(--uf-text); }
          div[data-testid="stSidebarNav"]{
            padding-top: 0.75rem;
          }
          div[data-testid="stSidebarNav"] ul li a{
            border-radius: 12px;
          }
          div[data-testid="stSidebarNav"] ul li a:hover{
            background: rgba(99,102,241,0.12);
          }

          /* Containers / cards */
          .uf-card{
            background: var(--uf-card);
            border: 1px solid var(--uf-card-border);
            border-radius: var(--uf-radius);
            padding: 18px 18px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.25);
          }
          .uf-card + .uf-card{ margin-top: 14px; }
          .uf-card h3{
            margin: 0 0 6px 0;
            font-size: 1.05rem;
            font-weight: 700;
          }
          .uf-muted{ color: var(--uf-muted); }

          /* Streamlit "border=True" containers */
          div[data-testid="stVerticalBlockBorderWrapper"]{
            background: var(--uf-card) !important;
            border: 1px solid var(--uf-card-border) !important;
            border-radius: var(--uf-radius) !important;
          }

          /* Buttons */
          .stButton>button, .stDownloadButton>button{
            border-radius: 14px !important;
            border: 1px solid rgba(148,163,184,0.18) !important;
            background: linear-gradient(135deg, rgba(99,102,241,0.95), rgba(34,211,238,0.55)) !important;
            color: #061021 !important;
            font-weight: 700 !important;
            box-shadow: 0 10px 20px rgba(0,0,0,0.25);
            transition: transform .05s ease, filter .15s ease;
          }
          .stButton>button:hover, .stDownloadButton>button:hover{
            filter: brightness(1.02);
            transform: translateY(-1px);
          }
          .stButton>button:active, .stDownloadButton>button:active{
            transform: translateY(0px);
          }

          /* Inputs */
          .stTextInput input, .stTextArea textarea, .stNumberInput input,
          div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div{
            border-radius: 14px !important;
            border: 1px solid rgba(148,163,184,0.18) !important;
            background: rgba(2, 6, 23, 0.35) !important;
          }
          .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus{
            outline: none !important;
            border-color: rgba(99,102,241,0.55) !important;
            box-shadow: 0 0 0 4px rgba(99,102,241,0.16) !important;
          }

          /* Tabs */
          button[data-baseweb="tab"]{
            border-radius: 14px 14px 0 0 !important;
          }
          button[data-baseweb="tab"][aria-selected="true"]{
            background: rgba(99,102,241,0.18) !important;
            border-bottom: 2px solid rgba(99,102,241,0.85) !important;
          }

          /* Code blocks */
          pre{
            border-radius: 14px !important;
            border: 1px solid rgba(148,163,184,0.16) !important;
            background: rgba(2, 6, 23, 0.55) !important;
          }

          /* Page header helper */
          .uf-page-header{
            margin: 6px 0 14px 0;
            padding: 18px 18px;
            border-radius: var(--uf-radius);
            background:
              radial-gradient(900px 220px at 10% 50%, rgba(99,102,241,0.28), rgba(0,0,0,0) 60%),
              radial-gradient(900px 220px at 90% 30%, rgba(34,211,238,0.16), rgba(0,0,0,0) 55%),
              rgba(17,24,39,0.60);
            border: 1px solid rgba(148,163,184,0.16);
          }
          .uf-page-title{
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap: 14px;
          }
          .uf-page-title h1{
            margin: 0;
            font-size: 1.75rem;
            font-weight: 800;
            letter-spacing: -0.02em;
          }
          .uf-page-subtitle{
            margin-top: 6px;
            color: var(--uf-muted);
            font-size: 1rem;
            line-height: 1.4;
          }
          .uf-badges{ display:flex; gap: 8px; flex-wrap: wrap; }
          .uf-badge{
            display:inline-flex;
            align-items:center;
            gap: 6px;
            padding: 6px 10px;
            border-radius: 999px;
            background: rgba(2, 6, 23, 0.35);
            border: 1px solid rgba(148,163,184,0.16);
            color: var(--uf-text);
            font-size: 0.85rem;
            font-weight: 600;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "", badges: list[str] | None = None) -> None:
    """Render a consistent, Flowbite-inspired header block for each page."""
    if badges is None:
        badges = []
    badges_html = "".join([f'<span class="uf-badge">{b}</span>' for b in badges])
    st.markdown(
        f"""
        <div class="uf-page-header">
          <div class="uf-page-title">
            <div>
              <h1>{title}</h1>
              {f'<div class="uf-page-subtitle">{subtitle}</div>' if subtitle else ''}
            </div>
            <div class="uf-badges">{badges_html}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def load_params(default: bool = False) -> dict[str, Any]:
    """
    Load parameters from a JSON file and return a dictionary containing them.

    If a 'params.json' file exists in the workspace, load the parameters from there.
    Otherwise, load the default parameters from 'default-parameters.json'.

    Additionally, check if any parameters have been modified by the user during the current session
    and update the values in the parameter dictionary accordingly. Also make sure that all items from
    the parameters dictionary are accessible from the session state as well.

    Args:
        default (bool): Load default parameters. Defaults to True.

    Returns:
        dict[str, Any]: A dictionary containing the parameters.
    """
    # Construct the path to the parameter file
    path = Path(st.session_state.workspace, "params.json")

    # Load the parameters from the file, or from the default file if the parameter file does not exist
    if path.exists() and not default:
        with open(path, "r", encoding="utf-8") as f:
            params = json.load(f)
    else:
        with open("default-parameters.json", "r", encoding="utf-8") as f:
            params = json.load(f)

    # Return the parameter dictionary
    return params


def save_params(params: dict[str, Any]) -> None:
    """
    Save the given dictionary of parameters to a JSON file.

    If a 'params.json' file already exists in the workspace, overwrite it with the new parameters.
    Otherwise, create a new 'params.json' file in the workspace directory and save the parameters there.

    Additionally, check if any parameters have been modified by the user during the current session
    and update the values in the parameter dictionary accordingly.

    This function should be run at the end of each page, if the parameters dictionary has been modified directly.
    Note that session states with the same keys will override any direct changes!

    Args:
        params (dict[str, Any]): A dictionary containing the parameters to be saved.

    Returns:
        dict[str, Any]: Updated parameters.
    """
    # Update the parameter dictionary with any modified parameters from the current session
    for key, value in st.session_state.items():
        if key in params.keys():
            params[key] = value

    # Save the parameter dictionary to a JSON file in the workspace directory
    path = Path(st.session_state.workspace, "params.json")
    with open(path, "w", encoding="utf-8") as outfile:
        json.dump(params, outfile, indent=4)

    return params


def page_setup(page: str = "") -> dict[str, Any]:
    """
    Set up the Streamlit page configuration and determine the workspace for the current session.

    This function should be run at the start of every page for setup and to get the parameters dictionary.

    Args:
        page (str, optional): The name of the current page, by default "".

    Returns:
        dict[str, Any]: A dictionary containing the parameters loaded from the parameter file.
    """
    if "settings" not in st.session_state:
        with open("settings.json", "r") as f:
            st.session_state.settings = json.load(f)

    # Set Streamlit page configurations
    st.set_page_config(
        page_title=st.session_state.settings["app-name"],
        page_icon="assets/umetaflow-logo.png",
        layout="wide",
        initial_sidebar_state="auto",
        menu_items=None,
    )

    # Modern Tailwind/Flowbite-inspired styling (global)
    inject_tailwind_flowbite_ui()

    # Expand sidebar navigation
    st.markdown(
        """
        <style>
            .stMultiSelect [data-baseweb=select] span{
                max-width: 500px;
                font-size: 1rem;
            }
            div[data-testid='stSidebarNav'] ul {max-height:none}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.logo("assets/pyopenms_transparent_background.png")

    # Create google analytics if consent was given
    if (
        ("tracking_consent" not in st.session_state) 
        or (st.session_state.tracking_consent is None)
        or (not st.session_state.settings['online_deployment'])
    ):
        st.session_state.tracking_consent = None
    else:
        if (st.session_state.settings["analytics"]["google-analytics"]["enabled"]) and (
            st.session_state.tracking_consent["google-analytics"] == True
        ):
            html(
                """
                <!DOCTYPE html>
                <html lang="en">
                    <head></head>
                    <body><script>
                    window.parent.gtag('consent', 'update', {
                    'analytics_storage': 'granted'
                    });
                    </script></body>
                </html>
                """,
                width=1,
                height=1,
            )
        if (st.session_state.settings["analytics"]["piwik-pro"]["enabled"]) and (
            st.session_state.tracking_consent["piwik-pro"] == True
        ):
            html(
                """
                <!DOCTYPE html>
                <html lang="en">
                    <head></head>
                    <body><script>
                    var consentSettings = {
                        analytics: { status: 1 } // Set Analytics consent to 'on' (1 for on, 0 for off)
                    };
                    window.parent.ppms.cm.api('setComplianceSettings', { consents: consentSettings }, function() {
                        console.log("PiwikPro Analytics consent set to on.");
                    }, function(error) {
                        console.error("Failed to set PiwikPro analytics consent:", error);
                    });
                    </script></body>
                </html>
                """,
                width=1,
                height=1,
            )

    # Determine the workspace for the current session
    if ("workspace" not in st.session_state) or (
        ("workspace" in st.query_params)
        and (st.query_params.workspace != st.session_state.workspace.name)
    ):
        # Clear any previous caches
        st.cache_data.clear()
        st.cache_resource.clear()
        # Check location
        if not st.session_state.settings["online_deployment"]:
            st.session_state.location = "local"
            st.session_state["previous_dir"] = os.getcwd()
            st.session_state["local_dir"] = ""
        else:
            st.session_state.location = "online"
        # if we run the packaged windows version, we start within the Python directory -> need to change working directory to ..\streamlit-template
        if "windows" in sys.argv:
            os.chdir("../streamlit-template")
        # Define the directory where all workspaces will be stored
        workspaces_dir = Path("..", "workspaces-" + st.session_state.settings["repository-name"])
        if "workspace" in st.query_params:
            st.session_state.workspace = Path(workspaces_dir, st.query_params.workspace)
        elif st.session_state.location == "online":
            workspace_id = str(uuid.uuid1())
            st.session_state.workspace = Path(workspaces_dir, workspace_id)
            st.query_params.workspace = workspace_id
        else:
            st.session_state.workspace = Path(workspaces_dir, "default")
            st.query_params.workspace = "default"

        if st.session_state.location != "online":
            # not any captcha so, controllo should be true
            st.session_state["controllo"] = True

    if "workspace" not in st.query_params:
        st.query_params.workspace = st.session_state.workspace.name

    # Make sure the necessary directories exist
    st.session_state.workspace.mkdir(parents=True, exist_ok=True)
    Path(st.session_state.workspace, "mzML-files").mkdir(parents=True, exist_ok=True)

    # Render the sidebar
    params = render_sidebar(page)
    
    captcha_control()  

    return params


def render_sidebar(page: str = "") -> None:
    """
    Renders the sidebar on the Streamlit app, which includes the workspace switcher,
    the mzML file selector, the logo, and settings.

    Args:
        params (dict): A dictionary containing the initial parameters of the app.
            Used in the sidebar to display the following settings:
            - selected-mzML-files : str
                A string containing the selected mzML files.
            - image-format : str
                A string containing the image export format.
        page (str): A string indicating the current page of the Streamlit app.

    Returns:
        None
    """
    params = load_params()
    with st.sidebar:
        # The main page has workspace switcher
        with st.expander("🖥️ **Workspaces**"):
            # Define workspaces directory outside of repository
            workspaces_dir = Path("..", "workspaces-" + st.session_state.settings["repository-name"])
            # Online: show current workspace name in info text and option to change to other existing workspace
            if st.session_state.location == "local":
                # Define callback function to change workspace
                def change_workspace():
                    for key in params.keys():
                        if key in st.session_state.keys():
                            del st.session_state[key]
                    st.session_state.workspace = Path(
                        workspaces_dir, st.session_state["chosen-workspace"]
                    )
                    st.query_params.workspace = st.session_state["chosen-workspace"]

                # Get all available workspaces as options
                options = [
                    file.name for file in workspaces_dir.iterdir() if file.is_dir()
                ]
                # Let user chose an already existing workspace
                st.selectbox(
                    "choose existing workspace",
                    options,
                    index=options.index(str(st.session_state.workspace.stem)),
                    on_change=change_workspace,
                    key="chosen-workspace",
                )
                # Create or Remove workspaces
                create_remove = st.text_input("create/remove workspace", "")
                path = Path(workspaces_dir, create_remove)
                # Create new workspace
                if st.button("**Create Workspace**"):
                    path.mkdir(parents=True, exist_ok=True)
                    st.session_state.workspace = path
                    st.query_params.workspace = create_remove
                    # Temporary as the query update takes a short amount of time
                    time.sleep(1)
                    st.rerun()
                # Remove existing workspace and fall back to default
                if st.button("⚠️ Delete Workspace"):
                    if path.exists():
                        shutil.rmtree(path)
                        st.session_state.workspace = Path(workspaces_dir, "default")
                        st.query_params.workspace = "default"
                        st.rerun()

        # All pages have settings, workflow indicator and logo
        with st.expander("⚙️ **Settings**"):
            img_formats = ["svg", "png", "jpeg", "webp"]
            st.selectbox(
                "image export format",
                img_formats,
                img_formats.index(params["image-format"]),
                key="image-format",
            )

    return params


def v_space(n: int, col=None) -> None:
    """
    Prints empty strings to create vertical space in the Streamlit app.

    Args:
        n (int): An integer representing the number of empty lines to print.
        col: A streamlit column can be passed to add vertical space there.

    Returns:
        None
    """
    for _ in range(n):
        if col:
            col.write("#")
        else:
            st.write("#")


def display_large_dataframe(
    df, chunk_sizes: list[int] = [100, 1_000, 10_000], **kwargs
):
    """
    Displays a large DataFrame in chunks with pagination controls and row selection.

    Args:
        df: The DataFrame to display.
        chunk_sizes: A list of chunk sizes to choose from.
        ...: Additional keyword arguments to pass to the `st.dataframe` function. See: https://docs.streamlit.io/develop/api-reference/data/st.dataframe

    Returns:
        Index of selected row.
    """

    # Dropdown for selecting chunk size
    chunk_size = st.selectbox("Select Number of Rows to Display", chunk_sizes)

    # Calculate total number of chunks
    total_chunks = (len(df) + chunk_size - 1) // chunk_size

    if total_chunks > 1:
        page = int(st.number_input("Select Page", 1, total_chunks, 1, step=1))
    else:
        page = 1

    # Function to get the current chunk of the DataFrame
    def get_current_chunk(df, chunk_size, chunk_index):
        start = chunk_index * chunk_size
        end = min(
            start + chunk_size, len(df)
        )  # Ensure end does not exceed dataframe length
        return df.iloc[start:end], start, end

    # Display the current chunk
    current_chunk_df, start_row, end_row = get_current_chunk(df, chunk_size, page - 1)

    event = st.dataframe(current_chunk_df, **kwargs)

    st.write(
        f"Showing rows {start_row + 1} to {end_row} of {len(df)} ({get_dataframe_mem_useage(current_chunk_df):.2f} MB)"
    )

    rows = event["selection"]["rows"]
    if not rows:
        return None
    # Calculate the index based on the current page and chunk size
    base_index = (page - 1) * chunk_size
    return base_index + rows[0]



def show_table(df: pd.DataFrame, download_name: str = "") -> None:
    """
    Displays a pandas dataframe using Streamlit's `dataframe` function and
    provides a download button for the same table.

    Args:
        df (pd.DataFrame): The pandas dataframe to display.
        download_name (str): The name to give to the downloaded file. Defaults to empty string.

    Returns:
        df (pd.DataFrame): The possibly edited dataframe.
    """
    # Show dataframe using container width
    st.dataframe(df, use_container_width=True)
    # Show download button with the given download name for the table if name is given
    if download_name:
        st.download_button(
            "Download Table",
            df.to_csv(sep="\t").encode("utf-8"),
            download_name.replace(" ", "-") + ".tsv",
        )
    return df


def show_fig(
    fig,
    download_name: str,
    container_width: bool = True,
    selection_session_state_key: str = "",
) -> None:
    """
    Displays a Plotly chart and adds a download button to the plot.

    Args:
        fig (plotly.graph_objs._figure.Figure): The Plotly figure to display.
        download_name (str): The name for the downloaded file.
        container_width (bool, optional): If True, the figure will use the container width. Defaults to True.
        selection_session_state_key (str, optional): If set, save the rectangular selection to session state with this key.

    Returns:
        None
    """
    if not selection_session_state_key:
        st.plotly_chart(
            fig,
            use_container_width=container_width,
            config={
                "displaylogo": False,
                "modeBarButtonsToRemove": [
                    "zoom",
                    "pan",
                    "select",
                    "lasso",
                    "zoomin",
                    "autoscale",
                    "zoomout",
                    "resetscale",
                ],
                "toImageButtonOptions": {
                    "filename": download_name,
                    "format": st.session_state["image-format"],
                },
            },
        )
    else:
        st.plotly_chart(
            fig,
            key=selection_session_state_key,
            selection_mode=["points", "box"],
            on_select="rerun",
            config={
                "displaylogo": False,
                "modeBarButtonsToRemove": [
                    "zoom",
                    "pan",
                    "lasso",
                    "zoomin",
                    "autoscale",
                    "zoomout",
                    "resetscale",
                    "select",
                ],
                "toImageButtonOptions": {
                    "filename": download_name,
                    "format": st.session_state["image-format"],
                },
            },
            use_container_width=True,
        )


def reset_directory(path: Path) -> None:
    """
    Remove the given directory and re-create it.

    Args:
        path (Path): Path to the directory to be reset.

    Returns:
        None
    """
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def get_dataframe_mem_useage(df):
    """
    Get the memory usage of a pandas DataFrame in megabytes.

    Args:
        df (pd.DataFrame): The DataFrame to calculate the memory usage for.

    Returns:
        float: The memory usage of the DataFrame in megabytes.
    """
    # Calculate the memory usage of the DataFrame in bytes
    memory_usage_bytes = df.memory_usage(deep=True).sum()
    # Convert bytes to megabytes
    memory_usage_mb = memory_usage_bytes / (1024**2)
    return memory_usage_mb


def tk_directory_dialog(title: str = "Select Directory", parent_dir: str = os.getcwd()):
    """
    Creates a Tkinter directory dialog for selecting a directory.

    Args:
        title (str): The title of the directory dialog.
        parent_dir (str): The path to the parent directory of the directory dialog.

    Returns:
        str: The path to the selected directory.

    Warning:
        This function is not avaliable in a streamlit cloud context.
    """
    root = Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    file_path = filedialog.askdirectory(title=title, initialdir=parent_dir)
    root.destroy()
    return file_path


def tk_file_dialog(
    title: str = "Select File",
    file_types: list[tuple] = [],
    parent_dir: str = os.getcwd(),
    multiple: bool = True,
):
    """
    Creates a Tkinter file dialog for selecting a file.

    Args:
        title (str): The title of the file dialog.
        file_types (list(tuple)): The file types to filter the file dialog.
        parent_dir (str): The path to the parent directory of the file dialog.
        multiple (bool): If True, multiple files can be selected.

    Returns:
        str: The path to the selected file.

    Warning:
        This function is not avaliable in a streamlit cloud context.
    """
    root = Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    file_types.extend([("All files", "*.*")])
    file_path = filedialog.askopenfilename(
        title=title, filetypes=file_types, initialdir=parent_dir, multiple=True
    )
    root.destroy()
    return file_path

def load_parquet(file):
    if Path(file).exists():
        return pd.read_parquet(file)
    else:
        return pd.DataFrame()

# General warning/error messages
WARNINGS = {
    "missing-mzML": "Upload or select some mzML files first!",
}

ERRORS = {
    "general": "Something went wrong.",
    "workflow": "Something went wrong during workflow execution.",
    "visualization": "Something went wrong during visualization of results.",
}
