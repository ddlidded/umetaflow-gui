import streamlit as st
from src.common.common import page_setup, page_header
from pathlib import Path
import json

params = page_setup(page="main")

page_header(
    "UmetaFlow",
    "Untargeted metabolomics preprocessing, annotation, and downstream analysis — in a clean, modern UI.",
    badges=["OpenMS", "pyOpenMS", "UmetaFlow pipeline"],
)

cols = st.columns([0.72, 0.28], gap="large")
with cols[0]:
    with st.container(border=True):
        st.markdown("### Overview")
        st.markdown(
            """
This app offers the powerful UmetaFlow **[1]** pipeline for untargeted metabolomics in an accessible user interface. Raw data pre-processing converts raw data to a feature quantification table by feature detection, alignment, grouping, adduct annotation and optional re-quantification of missing values. Features can be annotated by in-house libraries based on MS1 m/z and retention time matching as well as MS2 fragment spectrum similarity as well as with formula, structure and compound classes by SIRIUS **[2]**, CSI:FingerID **[3]** & CANOPUS **[4]** and chemical analogues by MS2Query **[5]**. Furthermore, required input files for GNPS Feature Based Molecular Networking **[6]** and Ion Identity Molecular Networking **[7]** can be generated.

UmetaFlow is further implemented as a [snakemake pipeline](https://github.com/NBChub/snakemake-UmetaFlow) and as a Python version in [Jupyter notebooks](https://github.com/eeko-kon/pyOpenMS_UmetaFlow) based on [pyOpenMS](https://pyopenms.readthedocs.io/en/latest/index.html).
            """
        )

    with st.container(border=True):
        st.markdown("### Getting started")
        st.markdown(
            """
- **Workspaces**: create/switch a workspace in the sidebar (your data + results live there).
- **Upload data**: open **File Upload** and add your `mzML` files.
- **Configure & run**: go to **UmetaFlow → Configure** then **Run**.
- **Explore results**: use **Results**, **View MS data**, **Extracted Ion Chromatograms**, and **Statistics**.
            """
        )

with cols[1]:
    with st.container(border=True):
        st.markdown("### Built with")
        st.image("assets/umetaflow-logo.png", use_container_width=True)
        st.image("assets/pyopenms-logo.png", use_container_width=True)


if Path("UmetaFlow-App.zip").exists():
    with st.container(border=True):
        st.markdown("### Installation (Windows)")
        st.markdown(
            "Download and extract the zip file. The folder contains an executable UmetaFlow file — no installation needed."
        )
        with open("UmetaFlow-App.zip", "rb") as file:
            st.download_button(
                label="Download for Windows",
                data=file,
                file_name="UmetaFlow-App.zip",
                mime="archive/zip",
                type="primary",
                use_container_width=True,
            )
# st.image("assets/umetaflow-app-overview.png", width=800)

with st.container(border=True):
    st.markdown("### Notes")
    st.markdown(
        """
#### Workspaces
On the left side of this page you can define a workspace where all your data including uploaded `mzML` files will be stored. Entering a workspace will switch to an existing one or create a new one if it does not exist yet. In the web app, you can share your results via the unique workspace ID. Be careful with sensitive data, anyone with access to this ID can view your data.

#### File handling
Upload `mzML` files via the **File Upload** tab. The data will be stored in your workspace. With the web app you can upload only one file at a time.
Locally there is no limit in files. However, it is recommended to upload a large number of files by specifying the path to a directory containing the files.

Result files are available via specified download buttons or, if run locally, within the workspace directory.
        """
    )

with st.container(border=True):
    st.markdown("### References")
    st.markdown(
        """
**[1]** Kontou, Eftychia E., et al. "UmetaFlow: an untargeted metabolomics workflow for high-throughput data processing and analysis." Journal of Cheminformatics 15.1 (2023): 52.

**[2]** Dührkop K, et al. SIRIUS 4. Nat Methods 2019;16:299–302.

**[3]** Dührkop K, et al. CSI:FingerID. PNAS 2015;112:12580–5.

**[4]** Dührkop K, et al. CANOPUS. Nat Biotechnol 2021;39:462–71.

**[5]** de Jonge NF, et al. MS2Query. Nat Commun 2023;14:1752.

**[6]** Nothias L-F, et al. GNPS FBMN. Nat Methods 2020;17:905–8.

**[7]** Schmid R, et al. IIMN. Nat Commun 2021;12:3832.

**[8]** Shah, Abzer K. Pakkir, et al. "The Hitchhiker’s Guide to Statistical Analysis of Feature-based Molecular Networks from Non-Targeted Metabolomics Data." (2023).
        """
    )
