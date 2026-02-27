from entsoe.files import EntsoeFileClient
import pandas as pd
from datetime import datetime, timedelta
import os
import requests

# ------------  ENTSO-E TP

# Get credentials from environment variables
username = os.environ.get("API_USERNAME")
password = os.environ.get("API_PASSWORD")

if not username or not password:
    raise ValueError("API_USERNAME and API_PASSWORD must be set")

client = EntsoeFileClient(username=username, pwd=password)
# this returns a dict of {filename: unique_id}:

# ----- Units
file_list = client.list_folder("ProductionAndGenerationUnits_r3")

df_units_entsoe = client.download_single_file(
    folder="ProductionAndGenerationUnits_r3", filename=list(file_list.keys())[0]
)
# Create the directory if it doesn't exist
os.makedirs("data/unit list", exist_ok=True)
df_units_entsoe.to_csv(
    "data/unit list/entsoe/ProductionAndGenerationUnits_r3.csv", index=False
)

# ----- Generation
file_list = client.list_folder("ActualGenerationOutputPerGenerationUnit_16.1.A_r3")
for year in range(datetime.now().year, datetime.now().year + 1):
    filtered_file_list = {k: v for k, v in file_list.items() if k.startswith(str(year))}
    ids_list = list(filtered_file_list.values())
    df_generation_entsoe = client.download_multiple_files(ids_list)

    # Daily generation
    df_generation_entsoe["Hour"] = df_generation_entsoe["ResolutionCode"].apply(
        lambda x: 0.25 if x == "PT15M" else (0.5 if x == "PT30M" else 1)
    )
    df_generation_entsoe["Generation_MWh"] = (
        (
            df_generation_entsoe["ActualGenerationOutput[MW]"]
            * df_generation_entsoe["Hour"]
        )
        .fillna(0)
        .astype("int32")
    )
    df_generation_entsoe = df_generation_entsoe[
        ["DateTime(UTC)", "GenerationUnitCode", "Generation_MWh"]
    ].drop_duplicates()  # Some units appear in multiple bidding zones, we keep only one occurrence
    df_generation_entsoe["DateTime"] = pd.to_datetime(
        df_generation_entsoe["DateTime(UTC)"]
    )
    df_generation_entsoe["DateTime"] = df_generation_entsoe["DateTime"].dt.strftime(
        "%Y-%m-%d"
    )

    result_entsoe = (
        df_generation_entsoe.groupby(
            [
                "DateTime",
                "GenerationUnitCode",
            ],
            observed=False,
        )["Generation_MWh"]
        .sum()
        .reset_index()
    )

    # Create the directory if it doesn't exist
    os.makedirs("data/generation/entsoe", exist_ok=True)
    result_entsoe.to_parquet(
        f"data/generation/entsoe/all_units_daily_generation_{str(year)}.parquet",
        index=False,
    )


# ------------  ELEXON
# ----- Units
url = "https://data.elexon.co.uk/bmrs/api/v1/reference/bmunits/all"  # f"https://api.bmreports.com/BMRS/bmunits/v1?APIKey={api_key}"
res = requests.get(url)
data = res.json()
df_units_elexon = pd.DataFrame(data)
df_units_elexon = df_units_elexon.drop_duplicates()

df_units_elexon.to_csv("data/unit list/elexon/ElexonUnits.csv", index=False)

# ----- Generation
for year in range(datetime.now().year, datetime.now().year + 1):
    result_elexon = pd.DataFrame()
    first_day = datetime(year, 1, 1)
    last_day = datetime.today() + timedelta(
        days=-7
    )  # Data is published with a delay of 5 days. We take a margin to ensure we have the data available and we won't have errors.
    for day in pd.date_range(first_day, last_day):
        print(day)
        date_from = day.strftime("%Y-%m-%d")
        date_to = date_from
        url = f"https://data.elexon.co.uk/bmrs/api/v1/datasets/B1610/stream?from={date_from}T00:00Z&to={date_to}T23:30Z"
        res = requests.get(url)
        data = res.json()
        df_generation_elexon = pd.DataFrame(data)
        df_generation_elexon = df_generation_elexon.drop_duplicates()

        # We sum the energy (quantity, already in MWh) per bmUnit and settlementDate to get daily generation per unit
        if len(df_generation_elexon) > 0:  # if there is no data for the day, we skip it
            df_generation_elexon["quantity"] = (
                (df_generation_elexon["quantity"]).fillna(0).astype("float")
            )

            df_generation_elexon["DateTime"] = pd.to_datetime(
                df_generation_elexon["settlementDate"]
            ).dt.strftime("%Y-%m-%d")

            result_day = (
                df_generation_elexon.groupby(
                    [
                        "DateTime",
                        "bmUnit",
                    ],
                    observed=False,
                )["quantity"]
                .sum()
                .reset_index()
            )

            result_day.rename(
                columns={"bmUnit": "ID", "quantity": "Generation_MWh"}, inplace=True
            )

            # We append the result of the day to the result of the year
            result_elexon = pd.concat([result_elexon, result_day], ignore_index=True)

    # Create the directory if it doesn't exist
    os.makedirs("data/generation/elexon", exist_ok=True)
    result_elexon.to_parquet(
        f"data/generation/elexon/all_units_daily_generation_{str(year)}.parquet",
        index=False,
    )
