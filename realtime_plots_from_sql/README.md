# REALTIME PLOTS FROM SQL

Welcome to the "**realtime plots from sql**" sub-repository!

This sub-repository is part of the main  "**bokeh dynamic plots**" repository, showcasing the power of **Bokeh** for creating interactive, real-time visualizations.

Here, we focus on visualizing parking occupancy data from Lyon, France, sourced from an automatically updated **PostgreSQL database** and deployed using the **Bokeh server**.


## Quick Access to the Deployed App

You can find the project deployed at the following address:
http://35.181.43.132:5006/bokeh_server

If you prefer to deploy your own instance of the application, follow the steps in the **Getting Started** section of this README.


## Overview

This project demonstrates how real-time data can be effectively visualized using Bokeh and PostgreSQL. It highlights:

- **Real-time updates**: The dashboard reflects the most current parking data in Lyon.
- **Dynamic interactivity**: Features like radio buttons allow users to customize their view.
- **Scalable design**: The architecture can handle continuous data streams from the API and display it seamlessly.

By combining PostgreSQL for data storage and Bokeh for visualization, this repository showcases a robust pipeline for creating dynamic, interactive dashboards.


### Data Sources

All data are sourced from the following website: https://data.grandlyon.com

We previously have created a PostgreSQL database

1. **Parking general information**:

    - **File**: parking_general_information.csv
    - Contains general information about parking facilities in Lyon.
    - **Download link**: https://data.grandlyon.com/fr/datapusher/ws/rdata/lpa_mobilite.parking_lpa_2_0_0/all.csv?maxfeatures=-1&filename=parkings-lyon-parc-auto-metropole-lyon-v2

2. **Parking occupancy history**:

    - This data is automatically populated in the PostgreSQL database by sending requests at a specify frequency to the following **API URL**:
https://download.data.grandlyon.com/files/rdata/lpa_mobilite.donnees/parking_temps_reel.json
    - The JSON data contains real-time information on available parking spaces.


## Repository Structure

The sub-repository is structured as follows:
```
/realtime_plots_from_sql
    /realtime_plotter                              # Folder dedicated to display Bokeh Figures
        /src
            /data
                - parking_general_information.csv  # Dataset with general information
            /scripts
                /config
                    - pgsql_config.py              # Configuration files for PostgreSQL database                    
                - plot_realtime.py                 # Create Bokeh Document to be displayed on a Bokeh server
        - Dockerfile                               # Build the plot_realtime Docker image
        - requirements.txt                         # Dependencies for the plot_realtime Docker image
    
    /data_collector                                # Folder dedicated to collect data on PostgreSQL database
        /src
            /scripts
                /config
                    - pgsql_config.py              # Configuration files for PostgreSQL database
                - collect_data.py                  # Automates data fetching and populates the database 
        /test
            - test_collect_data.py                 # Unit test for collect_data.py
        - Dockerfile                               # Build the collect_data image
        - requirements.txt                         # Dependencies for the collect_data Docker image
    
    - README.md                                    # This documentation file
```

## Getting Started

### Step 1: Collect data

1. Initialiaze a PostgreSQL database and table.

    Before running the Bokeh application, ensure a PostgreSQL database with a proper configurate table is initialized.Execute the following commands to initialize up the database and table:

        ```sql
            CREATE DATABASE parking_lyon_db;

            \c parking_lyon_db

            CREATE TABLE parking_table (
                parking_id TEXT,
                nb_of_available_parking_spaces INT,
                ferme BOOLEAN,
                date TIMESTAMP
            );
        ```

2.  Allow Docker to Access the Database.

    The method to enable Docker to access the database depends on where the database is hosted. If you've set up the database locally, follow these steps:

    - Ensure communication between Docker and PostgreSQL is possible on port 5432. Make sure your firewall allows traffic on this port. On a Linux system, you can add the following rule:
        
        ```bash
        sudo ufw allow 5432
    
    - Edit the PostgreSQL configuration file postgresql.conf to specify that PostgreSQL should listen to external IP addresses. Locate the following line and update it:

        ```bash
        # Connexions settings
        listen_addresses = '*'

    - Edit the PostgreSQL pg_hba.conf file to define the connection method. Set md5 for password authentication and change the default IP address to 0.0.0.0/0:

        ```bash
        # IPv4 local connections:
        host    all             all             0.0.0.0/0               md5
    
    - Restart PostgreSQL to apply the modification

        ```bash
        sudo systemctl restart postgresql

    - Ensure you have a password set for the database user. If not, create one:

        ```bash
        sudo -u postgres psql

        -- In the psql prompt
        ALTER USER you_user_name PASSWORD 'your_password'

3. Configure the psql_config.py file:

        "user": "your_user_name",
        "host": "IP_where_your_database_is_running"

    Note:
    If you have created the Postgresql database locally, you should specify the specific IP use by Docker to identify your local machine. You can find it by running this command:

        ```bash
        ip a 

4. Populate the Database Using Docker

   Follow these steps to populate the PostgreSQL database:

    - **Clone the Repository:**

        ```bash
        git clone https://github.com/RemiFigea/bokeh_dynamic_plots.git
   
    - **Navigate to the "data_collector" directory:**

        ```bash
        cd bokeh_dynamic_plots/realtime_plots_from_sql/data_collector

    - **Congigure your PostgreSQL session**

        Set your PostgreSQL password as an environement variable:

            ```bash
            export PGPASSWORD='your_password'


    - **Build and Run the Docker Container:**

        ```bash
        docker build -t collect_data_image .
        docker run -e PGPASSWORD=$PGPASSWORD collect_data_image
 

### Step 2: Run the Bokeh Application

1. Ensure PostgreSQL Configuration for Docker Communication

    If you've already completed the previous step, PostgreSQL should be configured to communicate with Docker.

    However, you still need to update the psql_config.py configuration file to reflect the settings for this section. Make sure the following fields match your database configuration:

        "user": "your_user_name"
        "host": "IP_where_your_database_is_running"

2. **Navigate to the "realtime_plotter" directory:**
   ```bash
   cd ../realtime_plotter

3. **Congigure your PostgreSQL session**

        Set your PostgreSQL password as an environement variable:

            ```bash
            export PGPASSWORD='your_password'

3. **Build and Run the Docker Container:**
   ```bash
   docker build -t plot_realtime_image .
   docker run -e PGPASSWORD=$PGPASSWORD -p 5006:5006 plot_realtime_image

**Note: If you are running the container on a virtual machine or any non-localhost environment, uncomment the appropriate line in the Dockerfile and adapt it to specify the IP address of your instance. By default, Bokeh only allows WebSocket connections from localhost:5006.**

4. **Access the Application:**

   - Open your browser and navigate to:

        - http://localhost:5006 (if running locally)

        - http://<IP_of_your_instance>:5006 (if running on a virtual machine)

   - The Bokeh server will display interactive Bokeh Figures that update in real-time as new data is populated into the database.
   

## Contributing

Feel free to contribute to the projects by opening issues or submitting pull requests. If you have suggestions or improvements, I welcome your feedback!


## License

This repository is licensed under the MIT License. See the LICENSE file for more details.


