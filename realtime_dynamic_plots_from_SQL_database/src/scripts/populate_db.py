"""
Module for fetching parking data, processing changes, and storing it in a PostgreSQL database.
Logs are store in the filepath  "../logs/populate_db.log"

This module:
- Fetches parking data from an API.
- Stores and processes it in temporary JSON files.
- Detects state changes in parking availability.
- Writes updates to a PostgreSQL database table.

Dependencies:
- PostgreSQL server and connection details
- Environment variables for PGPASSWORD

Environment Variables:
- Ensure PGPASSWORD is set to connect to the database.

Main Function:
- The 'main' function sets up the database connection,
  initializes the state, and continuously fetches and updates parking data.
"""

import json
import logging
import os
import pandas as pd
import psycopg2
import requests
import shutil
import time

API_URL = "https://download.data.grandlyon.com/files/rdata/lpa_mobilite.donnees/parking_temps_reel.json"
OUTPUT_PATH = "./tmp_json_files"
LOGS_OUTPUT_DIR = "../logs"
LOGS_FILENAME = "populate_db.log"
LOGS_FILEPATH = os.path.join(LOGS_OUTPUT_DIR, LOGS_FILENAME )
REQUEST_FREQUENCY = 60
REQUIRED_COLUMNS_SET = {"mv:currentValue", "ferme", "Parking_schema:identifier", "dct:date"}

PGPASSWORD = os.environ.get('PGPASSWORD')
PGSQL_CONFIG_DICT = {
    "user": "postgres",
    "host": "127.0.1",
    #"host": "172.31.4.218", 
    "port": "5432",   
    "password": PGPASSWORD,
    "database": "parking_lyon_db",
    "table": "parking_table"
}

os.makedirs(LOGS_OUTPUT_DIR, exist_ok=True)
logging.basicConfig(filename=LOGS_FILEPATH, level=logging.INFO)

class CriticalDataFrameError(Exception):
    """Custom exception for critical DataFrame validation errors."""

def get_current_time():
    """
    Returns the current time as a formatted string.
    """
    localtime = time.localtime()
    current_time = f"{localtime.tm_hour}h:{localtime.tm_min}min:{localtime.tm_sec}s"
    return current_time

def fetch_data_and_save(request_id, api_url, output_path):
    """
    Fetch data from an API and save it as a JSON file in the specified directory.

    Parameters:
    - request_id (str): Unique request identifier.
    - api_url (str): URL of the API.
    - output_path (str): Directory to store JSON files.
    """
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path, exist_ok=True)

    try:
        tmp_json_filename = f"data_{request_id}.json"
        tmp_json_filepath = os.path.join(output_path, tmp_json_filename)

        response = requests.get(api_url)
   
        current_time = get_current_time()
        logging.info(f"Request_id: {request_id}")
        logging.info(f"Time: {current_time} - status_code request of API: {response.status_code}.")

        if response.status_code == 200:
            data = response.json()

            with open(tmp_json_filepath, "w") as f:
                json.dump(data, f)
                current_time = get_current_time()
                logging.info(f"Time: {current_time} - temporary json_file created.")
        else:
            logging.info(f"HTTP Error: {response.status_code}")
    except Exception:
        current_time = get_current_time()
        error_msg = f"Time: {current_time} - Error fetching data."
        logging.error(error_msg)
        raise

def get_postgresql_connection(pgsql_config_dict):
    """
    Establish a persistent connection to a PostgreSQL database.

    Parameters:
    - pgsql_config_dict (dict): Dictionary containing PostgreSQL connection parameters 
    (database, user, password, host, port).

    Returns:
    tuple: A tuple containing the database connection and the cursor object.
    """
    try:
        conn = psycopg2.connect(
                dbname=pgsql_config_dict.get('database'),
                user=pgsql_config_dict.get('user'),
                password=pgsql_config_dict.get('password'),
                host=pgsql_config_dict.get('host'),
                port=pgsql_config_dict.get('port')
            )
        cursor = conn.cursor()
    except Exception:
        current_time = get_current_time()
        error_msg = f"Time: {current_time} - Error connecting to PostgreSQL database."
        logging.error(error_msg)
        raise
    
    return conn, cursor

def load_new_json(output_path, request_id):
    """
    Load a new JSON file into a DataFrame.

    Parameters:
    - output_path (str): Directory where the JSON file is stored.
    - request_id (str): Unique identifier for the request, used to locate the JSON file.

    Returns:
    pd.DataFrame: DataFrame containing the data from the JSON file.
    """
    tmp_json_filename = f"data_{request_id}.json"
    tmp_json_filepath = os.path.join(output_path, tmp_json_filename)

    try:
        with open(tmp_json_filepath, 'r') as f:
            tmp_json_file = json.load(f)
            batch_df = pd.DataFrame(tmp_json_file)

    except Exception:
        current_time = get_current_time()
        error_msg = f"Time: {current_time} - Error loading {tmp_json_filename}."
        logging.error(error_msg)
        raise

    return batch_df

def rename_columns(batch_df, required_columns_set):
    """
    Rename columns in a DataFrame to match the required schema.

    Parameters:
    - batch_df (pd.DataFrame): DataFrame containing the parking data.
    - required_columns_set (set): Set of expected column names.

    Returns:
    pd.DataFrame: DataFrame with renamed columns according to the mapping.
    """
    if not required_columns_set.issubset(batch_df.columns):
        current_time = get_current_time()
        error_msg = f"Time: {current_time} - JSON does not contain expected columns."
        logging.error(error_msg)
        raise ValueError()
    
    columns_renamer = {
        "mv:currentValue": "nb_of_available_parking_spaces",
        "Parking_schema:identifier": "parking_id",
        "dct:date": "date"
        }
    
    return batch_df.rename(columns=columns_renamer)

def parking_state_has_changed(row, df_state):
    """
    Check if the state of a parking row differs from its state in df_state.

    Parameters:
    - row (pd.Series): A row containing "parking_id", "ferme", and "nb_of_available_parking_spaces".
    - df_state (pd.DataFrame): DataFrame containing the current parking states with columns 
    "parking_id", "ferme", and "nb_of_available_parking_spaces".

    Returns:
    bool: True if the parking state has changed, False otherwise.
    """

    parking_id = row["parking_id"]

    if parking_id in df_state["parking_id"].values:
        old_row = df_state.loc[df_state["parking_id"] == parking_id, ['ferme', 'nb_of_available_parking_spaces']].iloc[0]
            
        if (old_row['ferme'] == row['ferme']) and (old_row['nb_of_available_parking_spaces'] == row['nb_of_available_parking_spaces']):
            return False
    
    return True

def collect_changes(batch_df, df_state):
    """
    Detect changes between a new batch DataFrame and the current state.

    Parameters:
    - batch_df (pd.DataFrame): DataFrame containing the new batch data.
    - df_state (pd.DataFrame): DataFrame representing the current state of parking data.

    Returns:
    --------
    tuple: A list of changed rows (as dictionaries) and the updated df_state DataFrame.
    """
    changes_list = []

    for _, row in batch_df.iterrows():
        if parking_state_has_changed(row, df_state):
            changes_list.append(row.to_dict())

            parking_id = row['parking_id']
            columns_filter = ['parking_id', 'ferme', 'nb_of_available_parking_spaces']
 
            if parking_id not in df_state['parking_id'].values:
                df_state = pd.concat([df_state, pd.DataFrame([row[columns_filter]])], ignore_index=True)
            else:
                df_state.loc[df_state['parking_id'] == parking_id] = row[columns_filter].values

    return changes_list, df_state

def validate_df_state_length(df_state):
    """
    Raise a ValueError if the DataFrame has more than 30 rows.

    Parameters:
    - df_state (pd.DataFrame): The DataFrame to validate.
    """
    df_state_length = len(df_state)
    if df_state_length > 30:
        current_time = get_current_time()
        error_msg = f"Time: {current_time} - df_state length shouldn't be over 30, current length: {df_state_length}."
        logging.critical(error_msg)
        raise  CriticalDataFrameError()

def write_to_postgresql(conn, cursor, changes_list, table_name):
    """
    Write changes to a PostgreSQL database table.

    Parameters:
    - conn: The PostgreSQL database connection object.
    - cursor: The database cursor for executing queries.
    - changes_list (list): A list of dictionaries representing changed records.
    - table_name (str): The name of the table where data will be inserted.
    """
    try:
        query = f"""
            INSERT INTO {table_name} (parking_id, nb_of_available_parking_spaces, ferme, date)
            VALUES (%s, %s, %s, %s)
            """

        for record_dict in changes_list:

            cursor.execute(
                query,
                (
                record_dict['parking_id'],
                record_dict['nb_of_available_parking_spaces'],
                record_dict['ferme'],
                record_dict['date']
                )
            )

        conn.commit()
        
        current_time = get_current_time()
        logging.info(f"Time: {current_time} - Data written in PostgreSQL database.")
        
    except Exception as e:
        conn.rollback()
        current_time = get_current_time()
        error_msg = f"Time: {current_time} - Error inserting into PostgreSQL: {str(e)}"
        logging.error(error_msg)
        raise
    
def main():
    """
    Main function to run the data fetching and processing loop.

    Continuously fetches parking data, processes it, detects changes,
    and writes it to a PostgreSQL database.
    Handles reconnection and environment validation.
    """
    
    df_state = pd.DataFrame(columns=['parking_id', "ferme", "nb_of_available_parking_spaces"])
    request_id = 1
    
    if not PGPASSWORD:
        error_msg = (
            "PGPASSWORD environment variable not set.\n"
            "Set it using the command: export PGPASSWORD='your_password_here'"
        )
        logging.critical(error_msg, exc_info=True)
        raise EnvironmentError(error_msg)

    try:
        conn, cursor = get_postgresql_connection(PGSQL_CONFIG_DICT)

        while True:
            try:
                fetch_data_and_save(request_id, API_URL, OUTPUT_PATH)
                if os.listdir(OUTPUT_PATH):
                    batch_df = load_new_json(OUTPUT_PATH, request_id)
                    batch_df = rename_columns(batch_df, REQUIRED_COLUMNS_SET)
                    changes_list, df_state = collect_changes(batch_df, df_state)
                    validate_df_state_length(df_state)
                    if changes_list:
                        write_to_postgresql(conn, cursor, changes_list, PGSQL_CONFIG_DICT.get("table"))
                time.sleep(REQUEST_FREQUENCY)
                request_id += 1

            except CriticalDataFrameError as e:
                logging.error(f"Critical Error!", exc_info=True)
                logging.info("Exiting the main loop due to DataFrame validation failure.")
                break
            except Exception as e:
                logging.error("Unexpected error in main loop!", exc_info=True)
                time.sleep(60)
    finally:
        if conn:
            conn.close()
            logging.info("PostgreSQL connection closed.")

if __name__ == "__main__":
    main()


