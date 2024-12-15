# BOKEH DYNAMIC PLOTS

Welcome to the **bokeh dynamic plots** repository! This project leverages Bokeh, a powerful Python library for creating interactive visualizations, to dynamically display parking occupancy data for parking facilities in Lyon, France.

## Overview

This repository demonstrates how Bokeh can be used to visualize parking occupancy data in Lyon. It is divided into two sub-repositories, each focusing on different data sources and deployment methods:

1. "**plots_from_csv**":

    - Focus: Visualizing data sourced from **CSV files**

    - Deployment: Uses **Flask**

2. "**realtime_plots_from_sql**":

    - Focus: Visualizing **real-time data** sourced from a **PostgreSQL Database**

    - Deployment: Utilizes the **Bokeh server**

### Data Sources

All data are sourced from the following website: https://data.grandlyon.com

## Repository Structure

The repository is structured as follows:
```
/bokeh_dynamic_plots
    /plots_from_csv
        /src
            /data
                - parking_general_information.csv     # Dataset with general information
                - parking_occupancy_history.csv     # Dataset with parking historical occupancy
            /scripts
                - plot.py                           # Create a Bokeh Layout to be displayed with Flask
            /templates
                - index.html                         # Flask HTML template
            - flask_app.py                         # Flask main application
        - Dockerfile                               # Build the "plot" Docker image
        - README.md                                 # Documentation file for the sub-repository "plots_from_csv"
        - requirements.txt                         # Project dependencies

    /realtime_plots_from_sql
        /realtime_plotter                           # Folder dedicated to build a Bokeh Document to be displayed on a Bokeh server
            /src
                /data
                    - parking_general_information.csv  # Dataset with general information
                /scripts
                    /config
                        - pgsql_config.py              # Configuration files for PostgreSQL database                    
                    - plot_realtime.py                  # Create the Bokeh Document with Bokeh Layout
            - Dockerfile                               # Build the "plot_realtime" Docker image
            - requirements.txt                         # Dependencies for the "plot_realtime" Docker image
        
        /data_collector                                # Folder dedicated to collect data on PostgreSQL database
            /src
                /scripts
                    /config
                        - pgsql_config.py              # Configuration files for PostgreSQL database
                    - collect_data.py                  # Automates data fetching and populates the PostgreSQL database 
            /test
                - test_collect_data.py                  # Unit test for "collect_data.py"
            - Dockerfile                               # Build the "collect_data" image
            - requirements.txt                         # Dependencies for the "collect_data" Docker image
    
        - README.md                                    # Documentation file for the sub-repository "realtime_plots_from_sql"

    - README.md                                     # This documentation file
```

## Getting Started

Each sub-repository contains its own README.md with specific instructions tailored to:

- "**plots_from_csv**":

    Instructions to run Flask and visualize data from CSV files.

- "**realtime_plots_from_sql**":

    Instructions to set up the PostgreSQL database, collect data, populate the database, and finally run the Bokeh server for real-time visualizations.

Make sure to follow the appropriate README.md located in the corresponding subdirectory.
   
## Contributing

Feel free to contribute to the projects by opening issues or submitting pull requests. If you have suggestions or improvements, I welcome your feedback!

## License

This repository is licensed under the MIT License. See the LICENSE file for more details.


