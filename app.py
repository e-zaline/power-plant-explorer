import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import glob
import os
from formatting import *

# Page configuration
st.set_page_config(page_title="Power plants explorer", page_icon="⚡", layout="wide")

# Title
st.title("⚡ Power plant generation explorer")


# Load data
@st.cache_data
def load_csv_data(folder, delimiter=",", dtypes=None, parse_dates=None, usecols=None):
    csv_files = glob.glob(os.path.join(folder, "*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {folder}")
    dfs = []
    for f in csv_files:
        df = pd.read_csv(
            f,
            encoding="utf-8",
            delimiter=delimiter,
            dtype=dtypes,
            parse_dates=parse_dates,
            usecols=usecols,
            low_memory=False,
        )
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


@st.cache_data
def load_parquet_data(folder):
    parquet_files = glob.glob(os.path.join(folder, "*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No Parquet files found in {folder}")
    dfs = []
    for f in parquet_files:
        df = pd.read_parquet(f)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


# Load ENTSO-E units list
df_units_entsoe = load_csv_data("data/unit list/entsoe")
df_units_entsoe = format_entsoe_units(df_units_entsoe)

# Load Elexon units list
df_units_elexon = load_csv_data("data/unit list/elexon")
df_units_elexon = format_elexon_units(df_units_elexon)

# Concatenate ENTSO-E and Elexon units
df_units = pd.concat([df_units_entsoe, df_units_elexon], ignore_index=True)
# Sort units by Area, Fuel, Fuel detailled, Generation Unit Name
df_units = df_units.sort_values(
    by=["Area", "Fuel", "Fuel (detailled)", "Generation Unit Name"]
).reset_index(drop=True)

# Load ENTSO-E generation data
df_generation_entsoe = load_parquet_data("data/generation/entsoe/")
df_generation_entsoe = format_entsoe_generation(df_generation_entsoe)

# Load Elexon generation data
df_generation_elexon = load_parquet_data("data/generation/elexon/")
df_generation_elexon = format_elexon_generation(df_generation_elexon)

# Concatenate ENTSO-E and Elexon generation data
df_generation = pd.concat(
    [df_generation_entsoe, df_generation_elexon], ignore_index=True
)


# Add a helper to reset filter widgets using session_state
def reset_filters():
    st.session_state["search_term"] = ""
    st.session_state["selected_areas"] = []
    st.session_state["selected_types"] = []
    st.session_state["selected_status"] = []
    st.session_state["show_selected_only"] = False


# Callback to sync selection changes
def sync_selection():
    if "unit_editor" in st.session_state:
        edited_df = st.session_state["unit_editor"]["edited_rows"]

        # Get the current filtered dataframe to know which rows correspond to which units
        for idx, changes in edited_df.items():
            if "Selected" in changes:
                # Get the ID for this row
                unit_code = filtered_df_units.iloc[idx]["ID"]

                if changes["Selected"]:
                    # Add to selected units if not already there
                    if unit_code not in st.session_state["selected_units"]:
                        st.session_state["selected_units"].append(unit_code)
                else:
                    # Remove from selected units
                    if unit_code in st.session_state["selected_units"]:
                        st.session_state["selected_units"].remove(unit_code)


if "selected_units" not in st.session_state:
    st.session_state["selected_units"] = []

# Main content - Tabs
tab1, tab2, tab3 = st.tabs(
    ["🔍 Select your generation unit(s)", "📊 Explore generation", "ℹ️ Read me"]
)

with tab1:
    st.header("Select your generation unit(s)")
    st.markdown(
        "Explore, filter and select your generation units by ticking the checkboxes. When you're ready, go to the 'Explore generation' tab to visualize the data."
    )

    # Filter section
    with st.expander("Filters", expanded=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # Text search
            search_term = st.text_input("Search (any column)", "", key="search_term")

        with col2:
            # Area filter
            areas = []
            if df_units is not None:
                areas = sorted(df_units["Area"].dropna().unique())
            selected_areas = st.multiselect(
                "Area", options=list(areas), key="selected_areas"
            )

        with col3:
            # Fuel filter
            unit_types = []
            if df_units is not None:
                unit_types = sorted(df_units["Fuel"].dropna().unique())
            selected_types = st.multiselect(
                "Fuel", options=list(unit_types), key="selected_types"
            )

        with col4:
            # Status filter
            unit_status = []
            if df_units is not None:
                unit_status = sorted(df_units["Status"].dropna().unique())
            selected_status = st.multiselect(
                "Status", options=list(unit_status), key="selected_status"
            )

        col1, col2, col3 = st.columns(3)
        with col1:
            # Show only selected unit
            show_selected_only = st.checkbox(
                "Show only the selected units",
                value=False,
                key="show_selected_only",
            )

        with col2:
            # Reset button
            st.button("Reset filters", on_click=reset_filters)

        with col3:
            # Unselect all button
            st.button(
                "Unselect all",
                on_click=lambda: st.session_state["selected_units"].clear(),
            )

    # Apply filters
    filtered_df_units = df_units.copy()

    # Filter by selected unit
    if show_selected_only:
        filtered_df_units = filtered_df_units[
            filtered_df_units["ID"].isin(st.session_state["selected_units"])
        ]

    # Filter by Area
    if selected_areas:
        filtered_df_units = filtered_df_units[
            filtered_df_units["Area"].isin(selected_areas)
        ]

    # Filter by Fuel
    if selected_types:
        filtered_df_units = filtered_df_units[
            filtered_df_units["Fuel"].isin(selected_types)
        ]

    # Filter by Status
    if selected_status:
        filtered_df_units = filtered_df_units[
            filtered_df_units["Status"].isin(selected_status)
        ]

    # Apply text search
    if search_term:
        mask = (
            filtered_df_units.astype(str)
            .apply(lambda x: x.str.contains(search_term, case=False, na=False))
            .any(axis=1)
        )
        filtered_df_units = filtered_df_units[mask]

    # Add Selected column based on current session state
    filtered_df_units.insert(
        0,
        "Selected",
        filtered_df_units["ID"].isin(st.session_state["selected_units"]),
    )

    # Display dataframe
    filtered_df_units = filtered_df_units.drop_duplicates().reset_index(drop=True)

    # Display current selection count
    if len(st.session_state["selected_units"]) == 0:
        select_message = "Select at least one unit to visualise its generation."
    elif len(st.session_state["selected_units"]) > 0:
        select_message = (
            "Go to the 'Explore generation' tab to visualize the generation."
        )
    st.info(
        f"📌 Currently selected: {len(st.session_state['selected_units'])} unit(s). \n{select_message}"
    )

    # Use data_editor for interactive selection with callback
    edited_df = st.data_editor(
        filtered_df_units,
        hide_index=True,
        key="unit_editor",
        on_change=sync_selection,
        disabled=[col for col in filtered_df_units.columns if col != "Selected"],
    )

    # Download button
    csv = filtered_df_units.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download filtered data as CSV",
        data=csv,
        file_name="filtered_generation_units.csv",
        mime="text/csv",
    )

with tab2:
    selected_units = st.session_state["selected_units"]
    st.header("Explore generation")
    col1, col2, col3 = st.columns(3)
    with col1:
        filtered_years = st.slider(
            "Select year range",
            min_value=2014,
            max_value=datetime.now().year,
            value=(datetime.now().year - 1, datetime.now().year),
        )

    generation_units_name = (
        df_units.drop_duplicates(subset="ID", keep="first")[
            ["ID", "Generation Unit Name"]
        ]
        .set_index("ID")["Generation Unit Name"]
        .to_dict()
    )

    filtered_generation = (
        df_generation[["DateTime", "ID", "Generation_MWh"]].drop_duplicates().copy()
    )

    if len(selected_units) > 0:
        filtered_generation = filtered_generation[
            filtered_generation["ID"].isin(selected_units)
        ]
        filtered_generation = filtered_generation[
            filtered_generation["DateTime"].between(
                f"{filtered_years[0]}-01-01", f"{filtered_years[1]}-12-31"
            )
        ]
        filtered_generation = (
            filtered_generation.groupby(["DateTime", "ID"]).mean().reset_index()
        )
    else:
        st.info("Select at least one generation unit to see the data.")

    if len(selected_units) > 0 and not filtered_generation.empty:
        # Create a new column with the formatted legend label
        filtered_generation["Unit_Label"] = (
            filtered_generation["ID"].map(generation_units_name)
            + " ("
            + filtered_generation["ID"]
            + ")"
        )

        # Plot
        fig = px.line(
            filtered_generation,
            x="DateTime",
            y="Generation_MWh",
            color="Unit_Label",
            labels={
                "DateTime": "DateTime",
                "Generation_MWh": "Daily generation (MWh)",
                "ID": "Generation Unit",
            },
        )

        fig.update_layout(legend=dict(yanchor="top", y=-0.2, xanchor="left", x=0.01))

        st.plotly_chart(fig)

        # Download button
        csv = filtered_generation.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download generation data as CSV",
            data=csv,
            file_name="generation_data.csv",
            mime="text/csv",
        )

    elif len(selected_units) > 0 and filtered_generation.empty:
        st.warning("No generation data available for the selected units and years.")

with tab3:
    st.header("About this App")
    st.markdown(
        """

This application allows you to explore generation units and their daily generation data from the [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) and [Elexon](https://bmrs.elexon.co.uk/).
The data is uploaded daily from ENTSO-E and Elexon using their APIs.
Elexon data is included to provide more detailed information on generation units in Great Britain, which are not fully covered in the ENTSO-E dataset.
ENTSO-E data is generally available with a delay of around 1 day, while Elexon data is available with a delay of around 6 days.

**Note:** We do not own this data.

Developed by **e-zaline** for **Beyond Fossil Fuels**.
"""
    )

    last_update = (
        df_generation["DateTime"].max() if df_generation is not None else "N/A"
    )
    st.markdown(f"**Data last updated:** {last_update}")
