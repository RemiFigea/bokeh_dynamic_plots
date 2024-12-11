# BOKEH DYNAMIC PLOTS

Welcome to the **Bokeh Dynamic plots** repository! This project leverages Bokeh, a powerful Python library for creating interactive visualizations, to dynamically display parking occupancy data for parking facilities in Lyon, France.

## Overview

This repository demonstrates how Bokeh can be used to visualize parking occupancy data in Lyon. It is divided into two sub-repositories, each focusing on different data sources and deployment methods:

1. dynamic_plots_from_csv_files

- Focus: Visualizing data sourced from **CSV files**
- Deployment: Uses **Flask**

2. realtime_dynamic_plots_from_SQL_database

- Focus: Visualizing **real-time data** sourced from a **PostgreSQL Database**
- Deployment: Utilizes the **Bokeh server**

### Data Sources

All data are sourced from the following website: https://data.grandlyon.com

## Repository Structure

The repository is structured as follows:
```
/bokeh_dynamic_plots
    /dynamic_plots_from_csv_files
        /src
            /data
                - parking_general_information.csv     # General parking info dataset
                - parking_occupancy_history.csv     # Historical occupancy data
            /scripts
                - bokeh_plot.py                     # Bokeh plot creation
            /templates
                - index.html                         # Flask HTML template
            - flask_app.py                         # Flask main application
        - Dockerfile                               # Docker setup files
        - README.md                                 # Documentation for this subrepo
        - requirements.txt                         # Project dependencies

    /realtime_dynamic_plots_from_SQL_database
        /src
            /data
                - parking_general_information.csv     # General parking info dataset
            /scripts
                - bokeh_server.py                   # Bokeh server setup
        - Dockerfile                               # Docker setup files
        - README.md                                 # Documentation for this subrepo
        - requirements.txt                         # Project dependencies

    - README.md                                     # Main documentation file

```

## Getting Started

Each sub-repository contains its own README.md with specific instructions tailored to:

- dynamic_plots_from_csv_files: Instructions to run Flask and visualize data from CSV files.
- realtime_dynamic_plots_from_SQL_database: Instructions to set up the PostgreSQL database, populate it with data, and run the Bokeh server for real-time visualizations.

Make sure to follow the appropriate README.md located in the corresponding subdirectory.
   
## Contributing

Feel free to contribute to the projects by opening issues or submitting pull requests. If you have suggestions or improvements, I welcome your feedback!

## License

This repository is licensed under the MIT License. See the LICENSE file for more details.


