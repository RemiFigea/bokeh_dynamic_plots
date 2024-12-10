# BOKEH DYNAMIC PLOTS

Welcome to the **Bokeh Dynamic plots** repository! This project leverages Bokeh, a powerful Python library for creating interactive visualizations, to dynamically display parking occupancy data for parking facilities in Lyon, France.

## Overview

This repository demonstrates the use of Bokeh for visualization of data related to parking occupancy in Lyon.

### Data Sources
site web: https://data.grandlyon.com/fr/datapusher/ws/rdata/lpa_mobilite.parking_lpa_2_0_0/all.csv?maxfeatures=-1&filename=parkings-lyon-parc-auto-metropole-lyon-v2

- **Parking general information**:
Lyon Parking Data (CSV)
Saved locally as parking_general_information.csv.

- **Parking occupancy history**:
Real-time data collected over a short period using API requests, saved as parking_occupancy_history.csv.

## Repository Structure

The repository is structured as follows:
```
/bokeh_dynamic_plots
    /src
        /data
            - parking_general_information.csv
            - parking_occupancy_history.csv
        /scripts
            - bokeh_plot.py
        /templates
            - index.html
        - flask_app.py
    - Dockerfiles
    - README.md
    - requirements.txt

- **`parking_general_information.csv`**: dataset with general information about parking in Lyon.
- **`parking_occupancy_history.csv`**: datatset with history of available parking spaces in the parking.
- **`bokeh_plot.py`**: create Bokeh plots of the data.
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
   
2. **Navigate to the repository folder:**
   ```bash
   cd /bokeh_dynamic_plots

3. **Run the application using Docker:**
   ```bash
   docker build -t bokeh_dynamic_plots .
   docker run -p 7860:7860 bokeh_dynamic_plots

4. **Access the Application:**
   - Open your web browser and navigate to http://localhost:7860.

   - The graphs will be displayed. You can interact with it.
   
## Contributing

Feel free to contribute to the projects by opening issues or submitting pull requests. If you have suggestions or improvements, I welcome your feedback!

## License

This repository is licensed under the MIT License. See the LICENSE file for more details.


