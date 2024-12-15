# PLOTS FROM CSV FILES

Welcome to the "**plots from csv files**" sub-repository!

This sub-repository is part of the main  "**bokeh dynamic plots**" repository. The main repository uses Bokeh, a powerful Python library for creating interactive visualizations, to dynamically display parking occupancy data for parking facilities in Lyon, France.

In this subsection, we focus on visualizing data sourced specifically from **CSV files** and use **Flask** for deployement.


## Overview

This repository demonstrates how Bokeh can be used to visualize parking occupancy data in Lyon, focusing on data provided in CSV format.

### Data Sources

All data are sourced from the following website: https://data.grandlyon.com

1. **Parking general information**:
- **File**: parking_general_information.csv
- Contains general information about parking facilities in Lyon.
- **Download link**: https://data.grandlyon.com/fr/datapusher/ws/rdata/lpa_mobilite.parking_lpa_2_0_0/all.csv?maxfeatures=-1&filename=parkings-lyon-parc-auto-metropole-lyon-v2

2. **Parking occupancy history**:
- **File**: parking_occupancy_history.csv
- Contains historical data on available parking spaces.
- **API URL**: "https://download.data.grandlyon.com/files/rdata/lpa_mobilite.donnees/parking_temps_reel.json"


## Repository Structure

The sub-repository is structured as follows:
```
/plots_from_csv
    /src
        /data
            - parking_general_information.csv
            - parking_occupancy_history.csv
        /scripts
            - plot.py
        /templates
            - index.html
        - flask_app.py
    - Dockerfile
    - README.md
    - requirements.txt

- **`parking_general_information.csv`**: dataset with general information about parking in Lyon.
- **`parking_occupancy_history.csv`**: datatset with history of available parking spaces in the parking.
- **`plot.py`**: create a Bokeh Layout from Bokeh Figure objects of the data.
- **`index.html`**: templates served by Flask.
- **`flask_app.py`**: main script of the Flask App.
- **`README.md`**: This documentation file.
- **`requirements.txt`**
```


## Access the Deployed App

You can find the deployed application on Hugging Face at the following address:
https://huggingface.co/spaces/Figea/bokeh_dynamic_plots


## Getting Started

To run the Flask application, you only need the contents of the docker_image folder and Docker installed on your computer. Follow the steps below to get started:

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/RemiFigea/bokeh_dynamic_plots.git
   
2. **Navigate to the folder dynamic_plots_from_csv_files:**
   ```bash
   cd bokeh_dynamic_plots/plots_from_csv

3. **Run the application using Docker:**
   ```bash
   docker build -t plot_from_csv_image .
   docker run -p 7860:7860 plot_from_csv_image

4. **Access the Application:**
   - Open your web browser and navigate to http://localhost:7860.

   - The graphs will be displayed. You can interact with it.
   

## Contributing

Feel free to contribute to the projects by opening issues or submitting pull requests. If you have suggestions or improvements, I welcome your feedback!


## License

This repository is licensed under the MIT License. See the LICENSE file for more details.


