import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import glob
import os

# Page configuration
st.set_page_config(
    page_title="ENTSO-E Generation Unit Explorer", page_icon="⚡", layout="wide"
)

# Title
st.title("⚡ ENTSO-E Transparency Platform Generation Unit Explorer")


# Load data
@st.cache_data
def load_data(folder, delimiter=","):
    try:
        csv_files = glob.glob(os.path.join(folder, "*.csv"))
        if not csv_files:
            st.error(f"No CSV files found in {folder}")
            return None
        df = pd.concat(
            [pd.read_csv(f, encoding="utf-8", delimiter=delimiter) for f in csv_files],
            ignore_index=True,
        )
        return df
    except FileNotFoundError:
        st.error(f"Error: folder '{folder}' not found")
        return None


# Load units list
df_units = load_data("data/unit list/")
df_units = df_units[
    df_units["GenerationUnitCode"].notna() & df_units["AreaDisplayName"].notna()
].reset_index()

# Load generation data
df_generation = load_data("data/generation/")


# Initialize session state for selected units
if "selected_units" not in st.session_state:
    st.session_state["selected_units"] = []


# Add a helper to reset filter widgets using session_state
def reset_filters():
    st.session_state["search_term"] = ""
    st.session_state["selected_areas"] = []
    st.session_state["selected_types"] = []
    st.session_state["selected_status"] = []
    st.session_state["show_selected_only"] = False


# Sidebar navigation
st.sidebar.header("Generation Units")

# Get unique generation unit codes, handling NaN values
unit_codes = df_units["GenerationUnitCode"].dropna().unique()
unit_codes = sorted(unit_codes)

selected_units = st.sidebar.multiselect(
    "Select your Generation Unit Codes",
    options=list(unit_codes),
    default=st.session_state["selected_units"],
    key="sidebar_multiselect",
)

# Update session state when sidebar selection changes
if selected_units != st.session_state["selected_units"]:
    st.session_state["selected_units"] = selected_units


# Display selected unit info
if len(selected_units) > 0:
    selected_units_info = df_units[df_units["GenerationUnitCode"].isin(selected_units)][
        ["GenerationUnitCode", "GenerationUnitName"]
    ]
    selected_units_info = dict(
        zip(
            selected_units_info["GenerationUnitCode"],
            selected_units_info["GenerationUnitName"],
        )
    )
    selected_units_info_str = "\n \n ".join(
        f"{code} ({selected_units_info.get(code, 'N/A')})" for code in selected_units
    )
    st.sidebar.info(f"Selected: \n \n {selected_units_info_str} ")

st.sidebar.markdown("---")
last_update = df_generation["DateTime"].max() if df_generation is not None else "N/A"
st.sidebar.markdown(f"**Data last updated:** {last_update}")


# Main content - Tabs
tab1, tab2, tab3 = st.tabs(
    ["🔍 Find your Generation Unit", "📊 Explore generation", "ℹ️ Read me"]
)

with tab1:
    st.header("Find your Generation Unit")
    st.markdown("Explore and filter the generation units database")

    # Filter section
    with st.expander("🔧 Filters", expanded=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # Text search
            search_term = st.text_input("Search (any column)", "", key="search_term")

        with col2:
            # AreaDisplayName filter
            areas = []
            if df_units is not None:
                areas = sorted(df_units["AreaDisplayName"].dropna().unique())
            selected_areas = st.multiselect(
                "AreaDisplayName", options=list(areas), key="selected_areas"
            )

        with col3:
            # GenerationUnitType filter
            unit_types = []
            if df_units is not None:
                unit_types = sorted(df_units["GenerationUnitType"].dropna().unique())
            selected_types = st.multiselect(
                "GenerationUnitType", options=list(unit_types), key="selected_types"
            )

        with col4:
            # GenerationUnitStatus filter
            unit_status = []
            if df_units is not None:
                unit_status = sorted(df_units["GenerationUnitStatus"].dropna().unique())
            selected_status = st.multiselect(
                "GenerationUnitStatus", options=list(unit_status), key="selected_status"
            )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            # Show only selected unit
            show_selected_only = st.checkbox(
                "Show only the units you have selected in the navigation panel",
                value=False,
                key="show_selected_only",
            )

        with col4:
            # Reset button
            st.markdown("")  # spacing
            st.button("Reset filters", on_click=reset_filters)

    # Apply filters
    filtered_df_units = df_units.copy()

    # Add Selected column based on session state
    filtered_df_units["Selected"] = filtered_df_units["GenerationUnitCode"].isin(
        st.session_state["selected_units"]
    )

    filtered_df_units = filtered_df_units[
        [
            "Selected",
            "AreaDisplayName",
            "GenerationUnitCode",
            "GenerationUnitName",
            "GenerationUnitType",
            "GenerationUnitStatus",
            "GenerationUnitInstalledCapacity(MW)",
            "ProductionUnitCode",
            "ProductionUnitName",
            "UpdateTime(UTC)",
        ]
    ]

    filtered_df_units = (
        filtered_df_units.sort_values("UpdateTime(UTC)")
        .groupby("GenerationUnitCode")
        .tail(1)
    ).reset_index(drop=True)

    # Filter by selected unit
    if show_selected_only:
        filtered_df_units = filtered_df_units[filtered_df_units["Selected"] == True]

    # Filter by AreaDisplayName
    if selected_areas:
        filtered_df_units = filtered_df_units[
            filtered_df_units["AreaDisplayName"].isin(selected_areas)
        ]

    # Filter by GenerationUnitType
    if selected_types:
        filtered_df_units = filtered_df_units[
            filtered_df_units["GenerationUnitType"].isin(selected_types)
        ]

    # Filter by GenerationUnitStatus
    if selected_status:
        filtered_df_units = filtered_df_units[
            filtered_df_units["GenerationUnitStatus"].isin(selected_status)
        ]

    # Apply text search
    if search_term:
        mask = (
            filtered_df_units.astype(str)
            .apply(lambda x: x.str.contains(search_term, case=False, na=False))
            .any(axis=1)
        )
        filtered_df_units = filtered_df_units[mask]

    # Display dataframe
    filtered_df_units = filtered_df_units.drop_duplicates().reset_index(drop=True)

    # Use data_editor for interactive selection
    edited_df = st.data_editor(
        filtered_df_units,
        column_config={
            "Selected": st.column_config.CheckboxColumn(
                default=False,
            )
        },
        disabled=[col for col in filtered_df_units.columns if col != "Selected"],
        hide_index=True,
        use_container_width=True,
        height=500,
        key="unit_editor",
    )

    # Update session state based on checkbox changes
    newly_selected = edited_df[edited_df["Selected"]]["GenerationUnitCode"].tolist()
    if set(newly_selected) != set(st.session_state["selected_units"]):
        st.session_state["selected_units"] = newly_selected
        st.rerun()

    # Download button
    csv = filtered_df_units.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download filtered data as CSV",
        data=csv,
        file_name="filtered_generation_units.csv",
        mime="text/csv",
    )

with tab2:
    st.header("Explore generation")
    col1, col2, col3 = st.columns(3)
    with col1:
        filtered_years = st.slider(
            "Select year",
            min_value=2014,
            max_value=datetime.now().year,
            value=(datetime.now().year - 1, datetime.now().year),
        )

    filtered_generation = (
        df_generation[["DateTime", "GenerationUnitCode", "Generation_MWh"]]
        .drop_duplicates()
        .copy()
    )

    if len(selected_units) > 0:
        filtered_generation = filtered_generation[
            filtered_generation["GenerationUnitCode"].isin(selected_units)
        ]
        filtered_generation = filtered_generation[
            filtered_generation["DateTime"].between(
                f"{filtered_years[0]}-01-01", f"{filtered_years[1]}-12-31"
            )
        ]
        filtered_generation = (
            filtered_generation.groupby(["DateTime", "GenerationUnitCode"])
            .mean()
            .reset_index()
        )
    else:
        st.info("Please select at least one Generation Unit Code to see the data.")

    if len(selected_units) > 0 and not filtered_generation.empty:
        # Create a new column with the formatted legend label
        filtered_generation["Unit_Label"] = filtered_generation[
            "GenerationUnitCode"
        ].map(
            lambda code: (
                f"{code} ({selected_units_info[code]})"
                if code in selected_units_info
                else code
            )
        )

        # Display dataframe
        # st.dataframe(filtered_generation, use_container_width=True, height=500)

        # Plot
        fig = px.line(
            filtered_generation,
            x="DateTime",
            y="Generation_MWh",
            color="Unit_Label",
            labels={
                "DateTime": "DateTime",
                "Generation_MWh": "Generation (MWh)",
                "GenerationUnitCode": "Generation Unit",
            },
        )

        fig.update_layout(legend=dict(yanchor="top", y=-0.2, xanchor="left", x=0.01))

        st.plotly_chart(fig, use_container_width=True)

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

This application allows you to explore generation units and their daily generation data from the [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/).
The data is uploaded daily from ENTSO-E using their API.

**Note:** We do not own this data.

Developed by **e-zaline** for **Beyond Fossil Fuels**.
"""
    )
