# REALTIME_DYNAMIC PLOTS FROM SQL DATABASE

Welcome to the **Realtime Dynamic Plots from SQL Database** sub-repository!

This sub-repository is part of the main  **Bokeh Dynamic Plots** project. The main repository uses Bokeh, a powerful Python library for creating interactive visualizations, to dynamically display parking occupancy data for parking facilities in Lyon, France.

In this subsection, we focus on visualizing **real-time data** sourced specifically from **PostgreSQL Database** and deploying it using the **Bokeh server**.

## Overview

This repository demonstrates how Bokeh can be used to visualize parking occupancy data in Lyon, with data being continuously fetched from a PostgreSQL database. We use the Bokeh server to display plots in real-time.

### Data Sources

All data are sourced from the following website: https://data.grandlyon.com

We previously have created a PostgreSQL database

1. **Parking general information**:

- **File**: parking_general_information.csv
- Contains general information about parking facilities in Lyon.
- **Download link**: https://data.grandlyon.com/fr/datapusher/ws/rdata/lpa_mobilite.parking_lpa_2_0_0/all.csv?maxfeatures=-1&filename=parkings-lyon-parc-auto-metropole-lyon-v2


2. **Parking occupancy history**:

 - This data is automatically populated in the PostgreSQL database by sending requests every 4 minutes to the following **API URL**:
https://download.data.grandlyon.com/files/rdata/lpa_mobilite.donnees/parking_temps_reel.json
- The JSON data contains historical information on available parking spaces.

## Repository Structure

The sub-repository is structured as follows:
```
/realtime_dynamic_plots_from_SQL_database
    /src
        /data
            - parking_general_information.csv
        /scripts
            - bokeh_server.py
    - Dockerfile
    - README.md
    - requirements.txt

- **`parking_general_information.csv`**: dataset with general information about parking in Lyon.
- **`bokeh_server.py`**: create Bokeh plots on a Bokeh server.
- **`Dockerfile`**: Configuration to build the Docker image.
- **`README.md`**: This documentation file.
- **`requirements.txt`**
```

## Getting Started

### Step 1: Feeding Data into the PostgreSQL Database

Before you run the Bokeh application, you need to populate the database with real-time data. Follow these steps:

1. Connect to the PostgreSQL session.
For a local session, use the following command:

    ```bash
        psql -h localhost -U postgres -p 5432
    ```

2. Create the Database and Table.

    ```sql
        CREATE DATABASE parking_lyon_db;

        \c parking_lyon_db

        CREATE TABLE parking_table (
            nb_of_available_parking_spaces INT,
            ferme BOOLEAN,
            date TIMESTAMP
        );
    ```

3. Populate the Table Automatically.
Automate data fetching every 4 minutes by sending requests to:

    **API URL**:
    "https://download.data.grandlyon.com/files/rdata/lpa_mobilite.donnees/parking_temps_reel.json".


### Step 2: Running the Bokeh Application

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/RemiFigea/bokeh_dynamic_plots.git
   
2. **Navigate to to the Sub-directory:**
   ```bash
   cd bokeh_dynamic_plots
   cd realtime_dynamic_plots_from_sql_database

3. **Build and Run the Docker Container:**
   ```bash
   docker build -t realtime_plots_from_sql_bd .
   docker run -e PGPASSWORD="your_posgresql_password" -p 5006:5006 realtime_plots_from_sql_bd

4. **Access the Application:**
   - Open your web browser and navigate to http://localhost:5006.

   - The Bokeh server will run and display interactive plots updating in real-time as data is populated in the database.
   
## Contributing

Feel free to contribute to the projects by opening issues or submitting pull requests. If you have suggestions or improvements, I welcome your feedback!

## License

This repository is licensed under the MIT License. See the LICENSE file for more details.


