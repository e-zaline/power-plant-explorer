import pandas as pd

# Columns to display on the app for units
cols = [
    "Area",
    "ID",
    "Generation Unit Name",
    "Production Unit Name",
    "Fuel",
    "Fuel (detailled)",
    "Status",
    "Capacity (MW)",
    "Production Unit Code",
    "Generation Unit EIC Code",
]


def format_entsoe_units(df_units_entsoe):
    df_units_entsoe = df_units_entsoe[
        df_units_entsoe["GenerationUnitCode"].notna()
        & df_units_entsoe["AreaDisplayName"].notna()
    ].reset_index(drop=True)

    # Convert ValidFrom to datetime
    df_units_entsoe["ValidFrom"] = pd.to_datetime(
        df_units_entsoe["ValidFrom"], errors="coerce"
    )

    # Keep only the entry with the most recent ValidFrom
    df_units_entsoe = (
        df_units_entsoe.sort_values("ValidFrom").groupby("GenerationUnitCode").tail(1)
    ).reset_index(drop=True)

    # Drop ValidFrom column as it's no longer needed
    df_units_entsoe = df_units_entsoe.drop(columns=["ValidFrom"])

    # Rename the GenerationUnitCode column to "Generation Unit EIC Code" and add an "ID" column
    df_units_entsoe.rename(
        columns={"GenerationUnitCode": "Generation Unit EIC Code"}, inplace=True
    )
    df_units_entsoe["ID"] = df_units_entsoe["Generation Unit EIC Code"]

    # Rename GB in AreaDisplayName to GB (ENTSO-E)
    df_units_entsoe["AreaDisplayName"] = df_units_entsoe["AreaDisplayName"].str.replace(
        "GB", "GB (ENTSO-E)"
    )

    df_units_entsoe.rename(
        columns={
            "AreaDisplayName": "Area",
            "GenerationUnitName": "Generation Unit Name",
            "ProductionUnitName": "Production Unit Name",
            "GenerationUnitStatus": "Status",
            "GenerationUnitInstalledCapacity(MW)": "Capacity (MW)",
            "ProductionUnitCode": "Production Unit Code",
            "GenerationUnitType": "Fuel (detailled)",
        },
        inplace=True,
    )

    # Fuel mapping
    fuel_mapping = {
        "Hydro Water Reservoir": "Hydro",
        "Solar": "Solar",
        "Fossil Gas": "Gas",
        "Fossil Hard coal": "Coal",
        "Fossil Oil": "Oil",
        "Hydro Pumped Storage": "Pumped Storage",
        "Hydro Run-of-river and pondage": "Hydro",
        "Energy storage": "Other/Unknown",
        "Waste": "Other/Unknown",
        "Wind Offshore": "Wind",
        "Biomass": "Biomass",
        "Nuclear": "Nuclear",
        "Fossil Brown coal/Lignite": "Coal",
        "Wind Onshore": "Wind",
        "Other": "Other/Unknown",
        "Fossil Coal-derived gas": "Gas",
        "Fossil Oil shale": "Oil",
        "Fossil Peat": "Coal",
        "Marine": "Other/Unknown",
        "Other renewable": "Other/Unknown",
        "Geothermal": "Other/Unknown",
    }

    df_units_entsoe["Fuel"] = (
        df_units_entsoe["Fuel (detailled)"].map(fuel_mapping).fillna("Other/Unknown")
    )

    df_units_entsoe = df_units_entsoe[cols].drop_duplicates()

    return df_units_entsoe


def format_elexon_units(df_units_elexon):
    df_units_elexon = df_units_elexon.drop_duplicates()
    # We only keep units whith a generation capacity
    df_units_elexon["generationCapacity"] = df_units_elexon[
        "generationCapacity"
    ].astype(float)
    df_units_elexon = df_units_elexon[df_units_elexon["generationCapacity"] > 0]

    # We remove interconnectors (I) and GSP Groups (G) as they are not generation units
    df_units_elexon = df_units_elexon[~df_units_elexon["bmUnitType"].isin(["I", "G"])]
    # df_units_elexon.to_csv("test.csv")

    # We rename column to match the format of the ENTSO-E dataset
    df_units_elexon.rename(
        columns={
            "elexonBmUnit": "ID",
            "eic": "Generation Unit EIC Code",
            "bmUnitName": "Generation Unit Name",
            "fuelType": "Fuel",
            "generationCapacity": "Capacity (MW)",
        },
        inplace=True,
    )

    df_units_elexon["Area"] = "GB (Elexon)"
    df_units_elexon["Status"] = "NOT SPECIFIED"
    df_units_elexon["Production Unit Name"] = df_units_elexon["Generation Unit Name"]
    df_units_elexon["Production Unit Code"] = ""
    df_units_elexon["Fuel (detailled)"] = ""

    # We clean the fuel types
    fuel_mapping = {
        "WIND": "Wind",
        "OTHER": "Other/Unknown",
        "CCGT": "Gas",
        "OCGT": "Gas",
        "NPSHYD": "Hydro",
        "PS": "Pumped Storage",
        "BIOMASS": "Biomass",
        "NUCLEAR": "Nuclear",
        "COAL": "Coal",
    }

    df_units_elexon["Fuel"] = (
        df_units_elexon["Fuel"].map(fuel_mapping).fillna("Other/Unknown")
    )

    df_units_elexon = df_units_elexon[cols].drop_duplicates()

    return df_units_elexon


def format_entsoe_generation(df_generation_entsoe):
    df_generation_entsoe["ID"] = df_generation_entsoe["GenerationUnitCode"]
    df_generation_entsoe = df_generation_entsoe[
        ["DateTime", "ID", "Generation_MWh"]
    ].drop_duplicates()
    df_generation_entsoe = (
        df_generation_entsoe.groupby(["DateTime", "ID"]).mean().reset_index()
    )  # We average the generation values if there are duplicates for the same DateTime and ID (it can happen when there are multiple production units for the same generation unit, we don't want to lose this information but we want to have only one value per day and per unit)
    return df_generation_entsoe


def format_elexon_generation(df_generation_elexon):
    df_generation_elexon = df_generation_elexon[
        ["DateTime", "ID", "Generation_MWh"]
    ].drop_duplicates()
    df_generation_elexon = (
        df_generation_elexon.groupby(["DateTime", "ID"]).mean().reset_index()
    )
    return df_generation_elexon
