from entsoe.files import EntsoeFileClient
import pandas as pd
from datetime import datetime
import os

# Get credentials from environment variables
username = os.environ.get("API_USERNAME")
password = os.environ.get("API_PASSWORD")

if not username or not password:
    raise ValueError("API_USERNAME and API_PASSWORD must be set")

# ENTSO-E TP
client = EntsoeFileClient(username=username, pwd=password)
# this returns a dict of {filename: unique_id}:

# Production and Generation Units
file_list = client.list_folder("ProductionAndGenerationUnits_r2")

df_units = client.download_single_file(
    folder="ProductionAndGenerationUnits_r2", filename=list(file_list.keys())[0]
)
# Create the directory if it doesn't exist
os.makedirs("data/unit list", exist_ok=True)
df_units.to_csv("data/unit list/ProductionAndGenerationUnits_r2.csv", index=False)

# Generation Data
file_list = client.list_folder("ActualGenerationOutputPerGenerationUnit_16.1.A_r2.1")
for year in range(datetime.now().year, datetime.now().year + 1):
    filtered_file_list = {k: v for k, v in file_list.items() if k.startswith(str(year))}
    ids_list = list(filtered_file_list.values())
    df_generation = client.download_multiple_files(ids_list)

    # Daily generation
    df_generation["Hour"] = df_generation["ResolutionCode"].apply(
        lambda x: 0.25 if x == "PT15M" else (0.5 if x == "PT30M" else 1)
    )
    df_generation["Generation_MWh"] = (
        df_generation["ActualGenerationOutput(MW)"] * df_generation["Hour"]
    )
    df_generation["DateTime"] = pd.to_datetime(df_generation["DateTime (UTC)"])
    df_generation["DateTime"] = df_generation["DateTime"].dt.strftime("%Y-%m-%d")

    result = (
        df_generation.groupby(
            [
                "DateTime",
                "GenerationUnitCode",
                "GenerationUnitName",
                "AreaDisplayName",
                "GenerationUnitType",
            ],
            observed=False,
        )["Generation_MWh"]
        .sum()
        .reset_index()
    )

    # Create the directory if it doesn't exist
    os.makedirs("data/generation", exist_ok=True)
    result.to_csv(
        f"data/generation/all_units_daily_generation_{str(year)}.csv", index=False
    )
