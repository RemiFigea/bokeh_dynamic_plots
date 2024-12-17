'''
This module creates a Bokeh Document for a Bokeh server to visualize real-time parking data in Lyon.
Logs are stored in a specified file for monitoring.

This module:
- Loads data from the specified PostegreSQL database
- Prepares and processes the data
- Creates Bokeh Figure and DataTable objects
- Builds an interactive Bokeh Layout combining these elements
- Create a Bokeh Documents from the Bokeh Layout and synchronize it with PostgreSQL database at the specified frequency

Dependencies:
- parking_general_information.csv files located in the "data" folder containing general information about parking
- An existing PostgreSQL server with an specific database and table filled with data.
- Module pgqsl_config.py specifying connection details to the PostgreSQL database.

Environment Variables:
- Ensure PGPASSWORD is set to connect to the database.
'''
import ast
from bokeh.layouts import column, row
from bokeh.models import CDSView, ColumnDataSource, CustomJS, DataTable, Div, DatetimeTickFormatter, HTMLTemplateFormatter
from bokeh.models import HoverTool, IndexFilter, RadioButtonGroup, Range1d, TableColumn, TapTool
from bokeh.plotting import curdoc, figure
from bokeh.transform import linear_cmap
from config.pgsql_config import PGSQL_CONFIG_DICT
import logging
import math
import numpy as np
import os
import pandas as pd
from sqlalchemy import create_engine
import time
import xyzservices.providers as xyz

LOGS_OUTPUT_DIR = "./logs"
LOGS_FILENAME = "plot_realtime.log"
LOGS_FILEPATH = os.path.join(LOGS_OUTPUT_DIR, LOGS_FILENAME)
LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s" 

GENERAL_INFO_CSV_FILEPATH = "./data/parking_general_information.csv"

HOMEPAGE_PARKING_ID = 'LPA0740'
REQUIRED_COLUMNS_SET = {"parking_id", "nb_of_available_parking_spaces", "date"}
DATA_TABLE_COLUMNS_FILTER = [
    "parking",
    "heure",
    "nombre_de_places_disponibles",
    "capacité_total",
    "nombre de niveaux",
    "hauteur limite (mètre)",
    "téléphone",
    "tarifs",
    "adresse"
]
LATITUDE_LYON = 45.764043
LONGITUDE_LYON = 4.835659
CIRCLE_SIZE_BOUNDS = (10, 25)
ZOOM_LEVEL = 10000
UPDATE_FREQUENCY = 60000 #10 minutes

os.makedirs(LOGS_OUTPUT_DIR, exist_ok=True)

file_handler = logging.FileHandler(filename=LOGS_FILEPATH, mode='w')  
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))  
logger = logging.getLogger(__name__)  
logger.addHandler(file_handler)  
logger.setLevel(logging.INFO) 

df_general_info = pd.DataFrame()

class BokehVisualizer:
    """
    Create and manage Bokeh visualizations including figures, maps, and tables.

    It handles data sources for parking availability, visualizes maps and plots (step and line plots), 
    and creates interactive tables for displaying parking information. Supports switching between 
    different plot types and real-time updates of sources for dynamic visualizations.
    """

    def __init__(self, df_global, layout_update_frequency):
        """
        Parameters:
        - df_global (DataFrame): A DataFrame containing global parking data with relevant information.
        - layout_update_frequency (int): The update frequency for the layout in milliseconds.

        Attributes:
        - df_global (DataFrame): Global parking data source.
        - current_parking_id (str): ID of the parking related to the Figure objects displayed on the layout.
        - source_original (ColumnDataSource): Full original dataset for visualizations.
        - source_history (ColumnDataSource): original dataset filtered for parking availability history visualisation.
        - source_map (ColumnDataSource): original dataset filtered for map visualization.
        - source_table (ColumnDataSource): Table data for displaying parking details.
        - p_map (Figure): Interactive map plot.
        - p_line (Figure): Line plot showing parking availability history.
        - p_step (Figure): Step plot showing parking availability history.
        - layout_update_frequency (int): Frequency of layout updates in milliseconds.
        - bokeh_layout (Layout): Main Bokeh layout containing all visual elements.
        """
        self.df_global = df_global
        self.current_parking_id = None
        self.source_original = ColumnDataSource()
        self.source_history = ColumnDataSource()
        self.source_map = ColumnDataSource()
        self.source_table = ColumnDataSource()
        self.p_map = figure()
        self.p_line = figure()
        self.p_step = figure()
        self.data_table = DataTable()
        self.data_table_url = DataTable()
        self.switch_plot_button = RadioButtonGroup()
        self.layout_update_frequency = layout_update_frequency
        self.bokeh_layout = column()

    def initialize_sources(self, homepage_parking_id, data_table_columns_filter):
        """
        Prepares data sources for visualizations.

        Parameters:
        - homepage_parking_id (str): ID of the parking associated to the Figure objects to be displayed on the layout for homepage.
        - data_table_columns_filter (list): List of columns to include in the table.

        Updates Attributes:
        - self.source_original (ColumnDataSource): Contains the full original dataset for visualizations.
        - self.source_history (ColumnDataSource): Contains historical parking availability data for the selected parking.
        - self.source_map (ColumnDataSource): Contains the map visualization data for parking availability.
        - self.source_table (ColumnDataSource): Contains a transposed table view displaying details about the selected parking lot.
        - self.current_parking_id (str): - current_parking_id (str): selected ID of the parking associated to the Figure objects to be displayed on the layout.
        """
        df_global = self.df_global

        df_more_recent_value = df_global.groupby('parking_id').agg({'date': 'max'})

        df_map = df_global.merge(df_more_recent_value , on=['parking_id', 'date'])
        df_history = df_global[df_global['parking_id']==homepage_parking_id]
        df_table = df_map[df_map['parking_id']==homepage_parking_id]

        transposed_data = {
            "Field": data_table_columns_filter,
            "Value": [df_table.iloc[0][col] for col in data_table_columns_filter]
        }

        self.source_original = ColumnDataSource(df_global)
        self.source_history = ColumnDataSource(df_history)
        self.source_map = ColumnDataSource(df_map)
        self.source_table = ColumnDataSource(transposed_data)
        self.current_parking_id = homepage_parking_id

    @staticmethod
    def normalize_number(nb, data_range, expected_range):
        """
        Normalize a number to fit within a target range while preserving its relative position.

        This function maps a given input value (`nb`) from an original data range (`data_range`) 
        to a new expected target range (`expected_range`). The input number is scaled such that 
        its relative position in `data_range` is maintained in `expected_range`.

        Parameters:
        - nb (float): The input number to be normalized.
        - data_range (tuple of float): A tuple containing two floats representing the input's original range (min, max).
            - data_range[0] (float): The lower bound of the input's original range.
            - data_range[1] (float): The upper bound of the input's original range.
        - expected_range (tuple of float): A tuple containing two floats representing the desired target range (min, max).
            - expected_range[0] (float): The lower bound of the desired target range.
            - expected_range[1] (float): The upper bound of the desired target range.

        Returns:
        - float: The normalized value scaled to fit within the `expected_range`.
        """
        result = nb

        if (data_range[1] - data_range[0]) != 0:
            result = expected_range[0] + (nb - data_range[0]) / (data_range[1] - data_range[0]) * (expected_range[1] - expected_range[0])

        return result

    def add_circle_size_to_source_map(self, circle_size_bounds=CIRCLE_SIZE_BOUNDS):
        """
        Adds normalized circle sizes to the "source_map" attribute based on available spaces.

        Updates the "source_map" attribute of the class instance by adding a new 
        "normalized_circle_size" field. This field is calculated by normalizing the 
        "nombre_de_places_disponibless" data according to the provided circle size bounds.

        Parameters:
        - circle_size_bounds (tuple): Min and max bounds for circle sizes 
                                    (default is defined by `CIRCLE_SIZE_BOUNDS`).

        Updates Attributes:
        - self.source_map (ColumnDataSource): Contains the map visualization data for parking availability.
        """
        source_map = self.source_map
        available_spaces_range = (
            min(source_map.data["nombre_de_places_disponibles"]),
            max(source_map.data["nombre_de_places_disponibles"])
            )
        normalized_circle_sizes = [BokehVisualizer.normalize_number(x, available_spaces_range, circle_size_bounds)
                            for x in source_map.data["nombre_de_places_disponibles"]]
        source_map.data['normalized_circle_size'] = normalized_circle_sizes
    
    def create_map_plot(self, latitude, longitude, zoom_level):
        """
        Creates an interactive Bokeh map plot centered on the given latitude and longitude.

        Parameters:
        - latitude (float): Latitude in degrees.
        - longitude (float): Longitude in degrees.
        - zoom_level (float): Zoom level for the map view.

        Updates:
        - self.p_map (Figure): The Bokeh map plot with parking data and interactive tools.
        """
        source_map = self.source_map
        color_mapper = linear_cmap(field_name="nombre_de_places_disponibles",
                                palette="Viridis256",
                                low=min(source_map.data["nombre_de_places_disponibles"]),
                                high=max(source_map.data["nombre_de_places_disponibles"]))

        hover_map = HoverTool(
            tooltips = [
                ('nom', '@parking'),
                ('places disponibles', "@nombre_de_places_disponibles"),
                ('capacité', '@{capacité_total}'),
                ],
        )
        tap_tool = TapTool()

        lyon_x, lyon_y = latlon_to_webmercator(latitude, longitude)

        p_map = figure(
            x_range=(lyon_x - zoom_level, lyon_x + zoom_level),
            y_range=(lyon_y - zoom_level, lyon_y + zoom_level),
            x_axis_type="mercator",
            y_axis_type="mercator",
            tools=[hover_map, 'pan', 'wheel_zoom']
            )
        p_map.add_tools(tap_tool)
        p_map.toolbar.active_tap = tap_tool
        p_map.add_tile(xyz.OpenStreetMap.Mapnik)

        circle_renderer = p_map.scatter(
            x="lon_mercator",
            y="lat_mercator",
            source=source_map,
            size="normalized_circle_size",
            fill_color=color_mapper,
            fill_alpha=1
            )

        circle_renderer.nonselection_glyph = None
        circle_renderer.selection_glyph = None

        self.p_map = p_map

    def get_axis_range(self):
        """
        Computes padded axis ranges for a Bokeh plot based on ColumnDatSource attribute "source_history".

        Returns:
        - tuple: Two "Range1d" objects for the x and y axis ranges.

        Notes:
        - Handles NaN values and converts "date" to timestamps if needed.
        - Adds 10% padding to both axes for better visualization.
        """
        source_history = self.source_history
        x_dates = source_history.data['date']
        y_values = source_history.data['nombre_de_places_disponibles']
        
        if isinstance(x_dates[0], str):
            x_dates = pd.to_datetime(x_dates).astype(int)

        x_min = np.nanmin(x_dates)
        x_max = np.nanmax(x_dates)
        y_min = np.nanmin(y_values)
        y_max = np.nanmax(y_values)
    
        x_pad = 0.1 * (x_max - x_min)
        y_pad = 0.1 * (y_max - y_min)

        x_start = x_min - x_pad
        x_end = x_max + x_pad
        y_start  = y_min - y_pad
        y_end  = y_max + y_pad

        x_range = Range1d(start=x_start, end=x_end)
        y_range = Range1d(start=y_start, end=y_end)

        return x_range, y_range

    def create_step_plot(self):
        """
        Creates a step plot to show the history of available parking spaces.

        Updates Attributes:
        - self.p_step (Figure): Bokeh step plot.
        """
        source_history = self.source_history

        p_step = figure(
            title=f"Historique des places disponibles - STEP PLOT", 
            height = 400,
            width = 700,
            x_axis_type="datetime",
            x_axis_label="Date", 
            y_axis_label="Nombre de places disponibles",
            tools=["crosshair", "pan", "wheel_zoom"],
            name="step_plot"
        )

        p_step.step(
            "date",
            "nombre_de_places_disponibles",
            source=source_history,
            line_width=2,
            mode="before",
            legend_field = "parking",
            )
        
        p_step.x_range, p_step.y_range = self.get_axis_range()
        p_step.legend.location = "top_left"
        p_step.xaxis.formatter = DatetimeTickFormatter(days="%d/%m/%Y")

        self.p_step = p_step

    def create_line_plot(self):
        """
        Creates a line plot to show the history of available parking spaces.

        Updates Attributes:
        - self.line_plot (Figure): Bokeh line plot.
        """
        source_history = self.source_history

        hover_line = HoverTool(
            tooltips = [
                ('Places disponibles', "@nombre_de_places_disponibles"),
                ('Heure', '@date{%a-%H:%M:%S}'),
            ],
            formatters={'@date': 'datetime'},
        )
        
        p_line = figure(
            title=f"Historique des places disponibles - LINE PLOT", 
            height = 400,
            width = 700,
            x_axis_type="datetime",
            x_axis_label="Date", 
            y_axis_label="Nombre de places disponibles",
            tools=[hover_line, "crosshair", "pan", "wheel_zoom"],
            name="line_plot"
        )

        p_line.line(
            "date",
            "nombre_de_places_disponibles",
            source=source_history,
            line_width=2,
            legend_field = "parking",
            )

        p_line.x_range, p_line.y_range = self.get_axis_range()
        p_line.legend.location = "top_left"
        p_line.xaxis.formatter = DatetimeTickFormatter(days="%d/%m/%Y")

        self.p_line = p_line

    def create_data_table(self):
        """
        Creates a data table to display parking information.

        Updates Attributes:
        - self.data_table (DataTable): A Bokeh data table displaying parking details.
        """
        source_table = self.source_table
        columns_tranposed = [
            TableColumn(field="Field", title="Champ"),
            TableColumn(field="Value", title="Valeur"),
        ]

        data_table = DataTable(
            source=source_table,
            columns=columns_tranposed,
            reorderable =False,
            width=1000,
            height=250,
            index_position=None,
            header_row=False,
            )

        self.data_table = data_table
    
    def create_data_table_url(self):
        """
        Creates a data table with clickable URLs for parking websites.

        Updates Attributes:
        - self.data_table_url (DataTable): A Bokeh data table displaying parking website links.
        """
        source_history =self.source_history

        url_cds_view = CDSView()
        url_cds_view.filter = IndexFilter([0])

        column = TableColumn(
            field="site_web",
            title="site web",
            formatter=HTMLTemplateFormatter(template='<a href="<%= site_web %>"><%= site_web %></a>')
            )

        data_table_url = DataTable(
            source=source_history,
            columns=[column],
            reorderable =False,
            width=600,
            height=600,
            index_position=None,
            view=url_cds_view
            )
        
        self.data_table_url = data_table_url

    def create_selection_callback(self):
        """
        Creates a CustomJS callback for updating "ColumnDataSource" and "Figure" object based on user selection.
        
        Updates Attributes:
        - self.selection_callback (CustomJS): The JavaScript callback.
        """
        selection_callback = CustomJS(
            args=dict(
                s_original=self.source_original,
                s_map=self.source_map,
                s_history=self.source_history,
                s_table=self.source_table,
                p_step=self.p_step,
                p_line=self.p_line),
            code=
            """
            var map_data = s_map.data
            var original_data = s_original.data
            var selected_index = cb_obj.indices[0]
                                            
            if (selected_index !== undefined) {
                var parking_id = map_data['identifier'][selected_index]

                // Update s_history
                var history_data = {};
                for (var key in original_data) {
                    history_data[key] = [];
                }

                for (var i = 0; i < original_data['parking_id'].length; i++) {
                    if (original_data['parking_id'][i] === parking_id) {
                        for (var key in original_data) {
                            history_data[key].push(original_data[key][i]);
                        }
                    }
                }

                s_history.data = history_data
                s_history.change.emit()

                // Specify new axis range for the history plots 
                var x_min = Math.min(...history_data['date'].map(d => new Date(d).getTime()));
                var x_max = Math.max(...history_data['date'].map(d => new Date(d).getTime()));
                var y_min = Math.min(...history_data['nombre_de_places_disponibles']);
                var y_max = Math.max(...history_data['nombre_de_places_disponibles']);

                var x_padding = 0.1 * (x_max - x_min);
                var y_padding = 0.1 * (y_max - y_min);

                p_step.x_range.setv({ start: x_min - x_padding, end: x_max + x_padding });
                p_step.y_range.setv({ start: y_min - y_padding, end: y_max + y_padding });
                p_line.x_range.setv({ start: x_min - x_padding, end: x_max + x_padding });
                p_line.y_range.setv({ start: y_min - y_padding, end: y_max + y_padding });
                p_step.change.emit();
                p_line.change.emit();
                
                // Update s_table
                var max_date_index = 0
                var max_date = new Date(Math.max(...history_data['date'].map(d => new Date(d))))

                for (var i = 0; i < history_data['date'].length; i++) {
                    if (new Date(history_data['date'][i]).getTime() === max_date.getTime()) {
                        max_date_index = i;
                        break;
                    }
                }

                var filter_columns = ["parking", "heure", "capacité_total", "nombre_de_places_disponibles", "nombre de niveaux", "hauteur limite (mètre)", "téléphone", "tarifs", "adresse"];
                var table_data = {
                    "Field": [],
                    "Value": []
                };

                for (var key of filter_columns) {
                    var value =history_data[key][max_date_index];

                    table_data["Field"].push(key);
                    table_data["Value"].push(value);
                }

                s_table.data = table_data
            }
            """
            )
        self.selection_callback = selection_callback

    def switch_plot(self, attr, old, new):
        """
        Toggles the visibility between the step plot and line plot based on the selected option.

        Parameters:
        - attr (str): Attribute that triggered the callback (unused in this method).
        - old (int): Previous value of the selected plot.
        - new (int): Current value of the selected plot (0 for step plot, 1 for line plot).

        Updates Attributes:
        - self.p_step (Figure): Bokeh step plot.
        - self.p_line (Figure): Bokeh line plot.
        """
        p_step = self.p_step
        p_line = self.p_line
        selected_plot = new

        if selected_plot == 0:
            p_line.visible, p_step.visible  = False, True
            
        elif selected_plot == 1:
            p_step.visible, p_line.visible = False, True

    def create_swicth_plot_button(self):
        """
        Creates a radio button group to toggle between step and line plots.

        Updates:
        - self.switch_plot_button (RadioButtonGroup): button linked to the switch_plot method.
        """
        button_group = RadioButtonGroup(labels=["STEP PLOT", "LINE PLOT"], active=1)
        button_group.on_change("active", self.switch_plot)
        self.switch_plot_button = button_group

    def get_current_parking_id(self, attr, old, new):
        """
        Updates the current parking ID based on user selection.

        Parameters:
        - attr (str): Attribute triggered by the callback.
        - old: Previous selected value.
        - new: New selected value (index of the selection).

        Updates Attributes:
        - current_parking_id (str): selected ID of the parking associated to the Figure objects to be displayed on the layout.
        """
        if new:
            selected_index = new[0]
            self.current_parking_id = self.source_map.data['parking_id'][selected_index]

    def update_sources(self):
        """
        Updates Bokeh data sources with the latest parking data for visualizations.

        Fetches real-time and general parking data, prepares a global DataFrame, 
        merges relevant information, and updates sources for the map, step plot, and table.

        Updates Attributes:
        - self.df_global (DataFrame): Global parking data source.
        - self.source_original (ColumnDataSource): Contains the full original dataset for visualizations.
        - self.source_history (ColumnDataSource): Contains historical parking availability data for the selected parking.
        - self.source_map (ColumnDataSource): Contains the map visualization data for parking availability.
        - self.source_table (ColumnDataSource): Contains a transposed table view displaying details about the selected parking lot.
        """
        current_parking_id = self.current_parking_id
        df_realtime = get_realtime_dataframe(PGSQL_CONFIG_DICT)
        validate_realtime_df_columns(df_realtime, REQUIRED_COLUMNS_SET)
        df_global = prepare_global_dataframe(df_general_info, df_realtime)
        df_history_plot = df_global[df_global['parking_id']==current_parking_id]

        df_more_recent_value = df_global.groupby('parking_id').agg({'date': 'max'})
        df_map = df_global.merge(df_more_recent_value , on=['parking_id', 'date'])
        df_map["normalized_circle_size"] = CIRCLE_SIZE_BOUNDS[0]
        df_table = df_map[df_map['parking_id']==current_parking_id]

        transposed_data = {
            "Field": DATA_TABLE_COLUMNS_FILTER,
            "Value": [df_table.iloc[0][col] for col in DATA_TABLE_COLUMNS_FILTER]
        }

        self.df_global = df_global 
        self.source_original.data = df_global.to_dict('list')
        self.source_map.data = df_map.to_dict('list')
        self.add_circle_size_to_source_map()
        self.source_history.data = df_history_plot.to_dict('list')
        self.source_table.data = transposed_data

    def get_layout_title(self):
        """
        Create a styled Bokeh Div title for the layout, showing update frequency.

        Returns:
        -------
        - Div: A Bokeh Div with the layout title as HTML.
        """
        update_freq_minute = self.layout_update_frequency // 60000
        
        title = Div(text=f'''
                    <h1 style="text-align:center; color:black; font-size: 48px; margin-bottom: 5px;">
                        Analyse en temps réel de l'occupation des parkings à Lyon
                    </h1>
                    <p style="text-align:center; color:black; font-size: 24px; margin-top: 0; padding-top: 0;">
                        (mise à jour toutes les {update_freq_minute} minutes)
                    </p>
                ''')

        return title

    def create_layout(self):
        """
        Creates and organizes the Bokeh layout for the visualization.

        The layout includes:
        - A title.
        - A map plot and historical plots (step and line) with a toggle button.
        - Data tables for additional information.

        Updates and Returns:
        - self.bokeh_layout: The final Bokeh layout combining all elements.
        """
        title = self.get_layout_title()

        history_plot = column([self.p_step, self.p_line])   
        right_corner = column([history_plot, self.switch_plot_button])
        first_row = row([self.p_map, right_corner])
        bokeh_layout = column([title, first_row, self.data_table, self.data_table_url])
        self.bokeh_layout = bokeh_layout

        return self.bokeh_layout

class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors."""
    pass

def validate_env_password(pgsql_config_dict):
    """
    Validates that the PostgreSQL password is set in the environment configuration.

    Parameters:
    - config_dict (dict): Dictionary containing environment configuration keys and values.

    Raises:
    - EnvironmentError: If the 'password' key is not set in the configuration dictionary.
    """
    if not pgsql_config_dict.get('password'):
        error_msg = (
            f"PGPASSWORD environment variable not set.\n"
            "Set it using the command: export PGPASSWORD='your_password_here'"
        )
        logger.critical(error_msg, exc_info=True)
        raise EnvironmentError(error_msg)

def get_address(string_dict):
    """
    Extract an address from a string representing a dictionary.

    Parameters:
    - string_dict (str): A string containing address information.

    Returns:
    - str: A formatted address string (street, postal code, locality).
    """

    address_keys = ["schema:streetAddress", "schema:postalCode", "schema:addressLocality"]
    string_dict = string_dict.strip('"').replace('"', "'")
    string_dict = string_dict.replace("': ", '": "').replace(", '", '", "').replace("'\"", '"' ).replace("\"'", '"' ).replace("{'", '{"').replace("'}", '"}')
    address_dict = ast.literal_eval(string_dict)
    address = [str(address_dict.get(key)) for key in address_keys]
    adress_string = " ".join(address)

    return adress_string

def get_parking_capacity(capacity_str):
    """
    Parse and retrieve the 'mv:maximumValue' from a string representing a list of dictionaries.

    The input string contains data in a JSON-like format, and this function extracts the 
    'mv:maximumValue' from the last dictionary in the list.

    Parameters:
    - capacity_str (str): A string representation of a list of dictionaries.

    Returns:
    - int or None: The value of the 'mv:maximumValue' key, or None if the key is not present.
    
    Raises:
    - ValueError: If the input string cannot be evaluated as a valid list of dictionaries.
    """

    str_clean = capacity_str.replace("'", '"')
    str_clean = str_clean.replace(": ,", ': None,')
    data_list = eval(str_clean)
    last_dict = data_list[-1]

    return last_dict.get("mv:maximumValue")

def clean_phone_number(phone_number):
    """
    Format a phone number by ensuring it starts with '0' and adding spaces every 2 digits.

    Parameters:
    - phone_number (int or str): The input phone number.

    Returns:
    - str: A formatted phone number (e.g., "01 23 45 67 89").
    """
    if not pd.isna(phone_number): 
        phone_number = "0" + str(int(phone_number))
        phone_number_slices_list = [phone_number[i: i+2] for i in range(0, 10, 2)]
        phone_number = " ".join(phone_number_slices_list)
    return phone_number

def latlon_to_webmercator(lat, lon):
        """
        Convert latitude and longitude to Web Mercator coordinates.
        
        Parameters:
        - lat (float): Latitude in degrees
        - lon (float): Longitude in degrees
        
        Returns:
        - (float, float): Web Mercator x, y coordinates
        """

        R = 6378137  # Radius of the Earth in meters (WGS 84 standard)
        x = R * math.radians(lon)  # Convert longitude to radians and scale
        y = R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))  # Transform latitude

        return x, y

def prepare_general_info_dataframe(csv_filepath):
    """
    Preprocess parking data from a CSV file.

    Reads the file at `csv_filepath`, cleans and formats the data, 
    including address, phone number, capacity, coordinates (in lat/lon and Web Mercator), 
    and fills missing values. Renames columns for clarity.

    Parameters:
    - csv_filepath (str): Path to the CSV file with parking information.

    Returns:
    - pd.DataFrame: A cleaned DataFrame with standardized columns for further processing.
    """
    df_general_info = pd.read_csv(csv_filepath, sep=";")
    df_general_info['adresse'] = df_general_info['address'].apply(get_address)
    df_general_info['capacité_total'] = df_general_info['capacity'].apply(get_parking_capacity)
    df_general_info['téléphone'] = df_general_info['telephone'].apply(clean_phone_number)
    df_general_info['lat'] = df_general_info['lat'].astype(str).str.replace(',', '.').astype(float)
    df_general_info['lon'] = df_general_info['lon'].astype(str).str.replace(',', '.').astype(float)
    df_general_info[["lon_mercator", "lat_mercator"]] = df_general_info.apply(
        lambda row: pd.Series(latlon_to_webmercator(row["lat"], row["lon"])),
        axis=1
    )
    df_general_info["resumetarifshoraires"] = df_general_info["resumetarifshoraires"].fillna(" ")
    df_general_info.rename(
        columns={
            "name": "parking",
            "url": "site_web",
            "numberoflevels": "nombre de niveaux",
            "vehicleheightlimitinm": "hauteur limite (mètre)",
            "resumetarifshoraires": "tarifs",
            },
        inplace=True
    )
    return df_general_info

def get_realtime_dataframe(pqsql_config_dict):
    """
    Fetches a real-time dataframe from a PostgreSQL database table.

    Parameters:
    - pqsql_config_dict (dict): Dictionary containing PostgreSQL connection details 
      (keys: 'user', 'password', 'host', 'port', 'database', 'table').

    Raises:
    - DatabaseConnectionError: If there is an issue connecting to the database or fetching data.

    Returns:
    - pd.DataFrame: A DataFrame containing the data from the specified table.
    """
    user = pqsql_config_dict.get("user")
    password = pqsql_config_dict.get("password")
    host = pqsql_config_dict.get("host")
    port = pqsql_config_dict.get("port")
    database = pqsql_config_dict.get("database")
    table = pqsql_config_dict.get("table")

    try:
        engine = create_engine(
            f"postgresql://{user}:{password}@{host}:{port}/{database}")
        query = f"SELECT * FROM {table};"

        df_realtime = pd.read_sql_query(query, engine)

    except DatabaseConnectionError as e:
        error_msg = "Error attemting to fetch data from PostgreSQL"
        logger.error(error_msg, exc_info=True)
        raise DatabaseConnectionError(error_msg)
 
    return df_realtime

def validate_realtime_df_columns(df_realtime, required_columns_set):
    """
    Validates that the DataFrame contains the required columns.

    Parameters:
    - df_realtime (pd.DataFrame): The DataFrame to validate.
    - required_columns_set (set): A set of column names expected in the DataFrame 
      (default: REQUIRED_COLUMNS_SET).

    Raises:
    - ValueError: If the DataFrame does not contain all required columns.
    """
    if not required_columns_set.issubset(df_realtime.columns):
        error_msg = "DataFrame fetched from PostgreSQL database does not contain expected columns."
        logger.error(error_msg)
        raise ValueError()
    
def prepare_global_dataframe(df_general_info, df_realtime):
    """
    Merges general parking information with real-time data.

    Combines data from `df_general_info` and `df_realtime` into a single DataFrame, 
    enriching real-time data with additional details like parking address, capacity, 
    and coordinates. Formats columns, renames for clarity, and sorts by date.

    Parameters:
    - df_info (pd.DataFrame): DataFrame containing general parking information.
    - df_realtime (pd.DataFrame): DataFrame containing real-time parking data.

    Returns:
    - pd.DataFrame: A merged and formatted DataFrame for further analysis or visualization.
    """
    df_global = pd.merge(
        left=df_realtime,
        right=df_general_info[['identifier',
                            'parking',
                            'site_web',
                            'adresse',
                            'nombre de niveaux',
                            'hauteur limite (mètre)',
                            'téléphone',
                            'tarifs',	
                            'lon_mercator',
                            'lat_mercator',   
                            'capacité_total']],
        how='left', left_on='parking_id',
        right_on='identifier'
        )
    

    df_global['heure'] = df_global['date'].apply(lambda x: x.strftime('%d %B %Y %H:%M:%S'))
    df_global.rename(
    columns={
        "nb_of_available_parking_spaces": "nombre_de_places_disponibles",
        },
    inplace=True
    )
    df_global.dropna(subset=['date', 'nombre_de_places_disponibles'], inplace=True)
    df_global.sort_values('date', inplace=True)

    return df_global

def main():
    """
    Initializes the database connection, prepares data sources, and builds an interactive Bokeh layout 
    with a map, trend chart, and data table.
    It periodically fetches updates from the PostgreSQL database and synchronizes 
    the visualizations.
    Errors are logged, with up to five retries for database connection issues before stopping execution.
    """
    global df_general_info
 
    logger.info("Main process launched!")
    
    database_connection_error_count = 0
    try:
        validate_env_password(PGSQL_CONFIG_DICT)

        df_general_info = prepare_general_info_dataframe(GENERAL_INFO_CSV_FILEPATH)
        df_realtime = get_realtime_dataframe(PGSQL_CONFIG_DICT)
        validate_realtime_df_columns(df_realtime, required_columns_set=REQUIRED_COLUMNS_SET)
        df_global = prepare_global_dataframe(df_general_info, df_realtime)

        visualizer = BokehVisualizer(df_global, UPDATE_FREQUENCY)
        visualizer.initialize_sources(HOMEPAGE_PARKING_ID, DATA_TABLE_COLUMNS_FILTER)
        visualizer.add_circle_size_to_source_map(CIRCLE_SIZE_BOUNDS)
        visualizer.create_map_plot(LATITUDE_LYON, LONGITUDE_LYON, ZOOM_LEVEL)
        visualizer.create_step_plot()
        visualizer.create_line_plot()
        visualizer.p_step.visible = False
        visualizer.create_data_table()
        visualizer.create_data_table_url()

        visualizer.create_selection_callback()
        visualizer.source_map.selected.js_on_change('indices', visualizer.selection_callback)
        visualizer.source_map.selected.on_change('indices', visualizer.get_current_parking_id)
        visualizer.create_swicth_plot_button()

        layout = visualizer.create_layout()
     
        curdoc().add_root(layout)  
        curdoc().add_periodic_callback(visualizer.update_sources, UPDATE_FREQUENCY)

    except DatabaseConnectionError:
        database_connection_error_count += 1
        error_msg = f"Database connection attempt failed. Total failures: {database_connection_error_count}"
        logger.warning(error_msg, exc_info=True)

        if database_connection_error_count > 5:
            logger.critical("Database connection attempt failed over 5 times. Script stopped!")
            raise
        time.sleep(60)

main()