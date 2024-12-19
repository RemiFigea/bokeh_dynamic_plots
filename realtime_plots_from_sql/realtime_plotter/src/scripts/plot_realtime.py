'''
This module creates a Bokeh Document for a Bokeh server to visualize real-time parking data in Lyon.
Logs are stored in a specified file for monitoring.

This module:
- Loads data from the specified PostegreSQL database
- Prepares and processes the data
- Creates Bokeh Figure and DataTable objects
- Builds an interactive Bokeh Layout combining these elements
- Create a Bokeh Documents from the Bokeh Layout and synchronize it with PostgreSQL database at the specified frequency.

Dependencies:
- parking_general_information.csv files located in the "data" folder containing general information about parking.
- An existing PostgreSQL server with an specific database and table filled with data.
- Module config.py specifying configuration parameters for PostgreSQL database connexion, data handling and visualization.

Environment Variables:
- Ensure PGPASSWORD is set to connect to the database.
'''
import ast
from bokeh.layouts import column, row
from bokeh.models import CDSView, ColumnDataSource, CustomJS, DataTable, Div, DatetimeTickFormatter, HTMLTemplateFormatter
from bokeh.models import HoverTool, IndexFilter, RadioButtonGroup, Range1d, TableColumn, TapTool
from bokeh.plotting import curdoc, figure
from bokeh.transform import linear_cmap
import json
import logging
import math
import numpy as np
import os
import pandas as pd
from config.config import BokehVisualizerConfig, DataHandlerConfig, PgsqlConfig 
from sqlalchemy import create_engine
import time
import xyzservices.providers as xyz

LOGS_OUTPUT_DIR = "./logs"
LOGS_FILENAME = "plot_realtime.log"
LOGS_FILEPATH = os.path.join(LOGS_OUTPUT_DIR, LOGS_FILENAME)
LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s" 

GENERAL_INFO_CSV_FILEPATH = "./data/parking_general_information.csv"

os.makedirs(LOGS_OUTPUT_DIR, exist_ok=True)

file_handler = logging.FileHandler(filename=LOGS_FILEPATH, mode='w')  
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))  
logger = logging.getLogger(__name__)  
logger.addHandler(file_handler)  
logger.setLevel(logging.INFO) 

class DatabaseOperationError(Exception):
    """Custom exception for errors related to database operations."""
    pass

class DataHandler:
    """
    A class responsible for loading, processing data into Bokeh ColumnDataSource.
    
    This class is responsible for:
        - Fetching data from databases or files.
        - Processing the data and converting it into Bokeh ColumnDataSource objects.

    Attributes:
        - csv_filepath(str): Path to the CSV file with parking information.
        - pqsql_config (PgsqlConfig): PostgreSQL connection configuration
            (attributes: 'user', 'password', 'host', 'port', 'database', 'table').
        - required_columns_set (set[str]): Set of required column names expected in "realtime_dataframe".
        - circle_size_bounds (tuple): Min and max bounds for circle sizes.
        - current_parking_id (str): parking ID related to the Figure objects to be displayed on the layout.
        - data_table_columns_filter (list[str]):  Columns to be shown in the DataTable view.
        - df_general_info (pd.DataFrame): DataFrame containing general parking information.
        - df_global (DataFrame): Merged DataFrame with parking real-time and general info.
        - source_original (ColumnDataSource): Full original dataset for visualizations.
        - source_history (ColumnDataSource): Filtered dataset for historical availability visualizations.
        - source_map (ColumnDataSource): Filtered dataset for map-based parking visualization..
        - source_table (ColumnDataSource): Dataset displayed in the parking details table view.
    """

    def __init__(self, csv_filepath, pgsql_config, handler_config):
        """
        Parameters:
        - csv_filepath (str): Path to the CSV file with parking information.
        - pqsql_config (PgsqlConfig): PostgreSQL connection configuration including:
            - PASSWORD, USER, HOST, PORT, DATABASE, TABLE.
        - handler_config(DataHandlerConfig) : Configuration parameters for class DataHandler containing:
            - REQUIRED_COLUMNS_SET (set[str]):  Required columns for data processing.
            - CIRCLE_SIZE_BOUNDS (tuple): Min and max bounds for circle sizes.
            - HOMEPAGE_PARKING_ID: parking ID related to the Figure objects to be displayed on the homepage layout.
            - DATA_TABLE_COLUMNS_FILTER (list[str]):  Columns to be shown in the DataTable view.
        """
        self.csv_filepath = csv_filepath
        self.pgsql_config = pgsql_config
        self.required_columns_set = handler_config.REQUIRED_COLUMNS_SET
        self.circle_size_bounds = handler_config.CIRCLE_SIZE_BOUNDS
        self.current_parking_id = handler_config.HOMEPAGE_PARKING_ID
        self.data_table_columns_filter = handler_config.DATA_TABLE_COLUMNS_FILTER
        self.df_general_info = pd.DataFrame()
        self.df_global = pd.DataFrame()
        self.source_original = ColumnDataSource()
        self.source_history = ColumnDataSource()
        self.source_map = ColumnDataSource()
        self.source_table = ColumnDataSource()

    @staticmethod
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
    
    @staticmethod
    def get_parking_capacity(capacity_str):
        """
        Parse and retrieve the 'mv:maximumValue' from a string representing a list of dictionaries.

        The input string contains data in a JSON-like format, and this function extracts the 
        'mv:maximumValue' from the last dictionary in the list.

        Parameters:
        - capacity_str (str): A string representation of a list of dictionaries.

        Returns:
        - int or "not reported": The value of the 'mv:maximumValue' key, or "not reported" if the key is not present.
        
        Raises:
        - ValueError: If the input string cannot be evaluated as a valid list of dictionaries.
        """
        str_clean = capacity_str.replace("'", '"')
        str_clean = str_clean.replace(": ,", ': "not reported",')
        data_list = json.loads(str_clean)
        last_dict = data_list[-1]

        return last_dict.get("mv:maximumValue")

    @staticmethod
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
            
    def prepare_general_info_dataframe(self):
        """
        Preprocess parking data from a CSV file.

        Reads the file at `csv_filepath`, cleans and formats the data, 
        including address, phone number, capacity, coordinates (in lat/lon and Web Mercator), 
        and fills missing values. Renames columns for clarity.

        Updates Attributs:
        - df_general_info (pd.DataFrame): A cleaned DataFrame with standardized columns for further processing.
        """
        df_general_info = pd.read_csv(self.csv_filepath, sep=";")
        df_general_info['adresse'] = df_general_info['address'].apply(DataHandler.get_address)
        df_general_info['capacité_total'] = df_general_info['capacity'].apply(DataHandler.get_parking_capacity)
        df_general_info['téléphone'] = df_general_info['telephone'].apply(DataHandler.clean_phone_number)
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
        
        self.df_general_info = df_general_info

    def get_realtime_dataframe(self):
        """
        Fetches a real-time dataframe from a PostgreSQL database table.

        Raises:
        - DatabaseConnectionError: If there is an issue connecting to the database or fetching data.

        Returns:
        - pd.DataFrame: A DataFrame containing the data from the specified table.
        """
        password = self.pgsql_config.PASSWORD
        user = self.pgsql_config.USER
        host = self.pgsql_config.HOST
        port = self.pgsql_config.PORT
        database = self.pgsql_config.DATABASE
        table = self.pgsql_config.TABLE
  
        try:
            engine = create_engine(
                f"postgresql://{user}:{password}@{host}:{port}/{database}")
            query = f"SELECT * FROM {table};"

            df_realtime = pd.read_sql_query(query, engine)
        except:
            error_msg = "Error attemting to fetch data from PostgreSQL"
            logger.error(error_msg, exc_info=True)
            raise DatabaseOperationError(error_msg)

        if df_realtime is None:
            error_msg = "Error: Query result returned None instead of a valid dataframe."
            logger.error(error_msg, exc_info=True)
            raise DatabaseOperationError(error_msg)

        if df_realtime.empty:
            error_msg = f"Error: Query executed successfully, but the table '{table}' is empty."
            logger.error(error_msg, exc_info=True)
            raise DatabaseOperationError(error_msg)

        return df_realtime

    def validate_realtime_df_columns(self, df_realtime):
        """
        Validates that the DataFrame contains the required columns.

        Parameters:
        - df_realtime (pd.DataFrame): The DataFrame to validate.

        Raises:
        - ValueError: If the DataFrame does not contain all required columns.
        """
        required_columns_set = self.required_columns_set

        if not required_columns_set.issubset(df_realtime.columns):
            missing_columns = required_columns_set - set(df_realtime.columns)
            error_msg = f"""
            DataFrame fetched from PostgreSQL database does not contain expected columns.\n
            Missing columns: {missing_columns}"""
            logger.error(error_msg)
            raise ValueError(error_msg)

    def prepare_global_dataframe(self, df_realtime):
        """
        Merges general parking information with real-time data.

        Combines data from "self.df_general_info" and "df_realtime" into a single DataFrame, 
        enriching real-time data with additional details like parking address, capacity, 
        and coordinates. Formats columns, renames for clarity, and sorts by date.

        Parameters:
        - df_realtime (pd.DataFrame): DataFrame containing real-time parking data.

        Update Attributs and Returns:
        - df_global (pd.DataFrame): A merged and formatted DataFrame for further analysis or visualization.
        """
        df_general_info = self.df_general_info

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

        self.df_global = df_global

        return self.df_global
    
    @staticmethod
    def normalize_number(nb, data_range, expected_range):
        """
        Normalize a number to fit within a target range while preserving its relative position.

        Maps the input number ("nb") from the original range ("data_range") to a new range ("expected_range).

        Parameters:
        - nb (float): The number to normalize.
        - data_range (tuple of float): The original range (min, max).
        - expected_range (tuple of float): The target range (min, max).

        Returns:
        - float: The normalized number within the "expected_range".
        """
        result =  (expected_range[0] + expected_range[1]) / 2

        if (data_range[1] - data_range[0]) != 0:
            result = expected_range[0] + (nb - data_range[0]) / (data_range[1] - data_range[0]) * (expected_range[1] - expected_range[0])

        return result
    
    def add_circle_size_to_source_map(self):
        """
        Adds normalized circle sizes to the "source_map" attribute based on available spaces.

        Updates the "source_map" attribute of the class instance by adding a new 
        "normalized_circle_size" field. This field is calculated by normalizing the 
        "nombre_de_places_disponibless" data according to the provided circle size bounds.

        Updates Attributes:
        - source_map (ColumnDataSource): Contains the map visualization data for parking availability.
        """
        source_map = self.source_map

        available_spaces_range = (
            min(source_map.data["nombre_de_places_disponibles"]),
            max(source_map.data["nombre_de_places_disponibles"])
            )
        normalized_circle_sizes = [DataHandler.normalize_number(x, available_spaces_range, self.circle_size_bounds)
                            for x in source_map.data["nombre_de_places_disponibles"]]
        source_map.data['normalized_circle_size'] = normalized_circle_sizes


    def update_sources(self):
            """
            Updates Bokeh ColumnDataSource objects with the latest parking data and current selected parking ID.

            Fetches real-time and general parking data, prepares a global DataFrame, 
            merges relevant information, and updates sources for the map, step plot, and table.

            Updates Attributes:
            - df_global (DataFrame): Global DataFrame with parking general information and history occupancy.
            - source_original (ColumnDataSource): Full original dataset for visualizations.
            - source_history (ColumnDataSource): original dataset filtered for parking availability history visualisation.
            - source_map (ColumnDataSource): original dataset filtered for map visualization.
            - source_table (ColumnDataSource): Table data for displaying parking details.
            """
            current_parking_id = self.current_parking_id
            data_table_columns_filter = self.data_table_columns_filter

            df_realtime = self.get_realtime_dataframe()
            self.validate_realtime_df_columns(df_realtime)

            df_global = self.prepare_global_dataframe(df_realtime)
            
            df_history_plot = df_global[df_global['parking_id']==self.current_parking_id]

            df_more_recent_value = df_global.groupby('parking_id').agg({'date': 'max'})
            df_map = df_global.merge(df_more_recent_value , on=['parking_id', 'date'])
            df_map["normalized_circle_size"] = self.circle_size_bounds[0]
            df_table = df_map[df_map['parking_id']==current_parking_id]

            transposed_data = {
                "Field": data_table_columns_filter,
                "Value": [df_table.iloc[0][col] for col in data_table_columns_filter]
            }

            self.df_global = df_global
            self.source_original.data = df_global.to_dict('list')
            self.source_map.data = df_map.to_dict('list')
            self.add_circle_size_to_source_map()
            self.source_history.data = df_history_plot.to_dict('list')
            self.source_table.data = transposed_data

class BokehVisualizer:
    """
    Create and manage real-time Bokeh visualizations including figures, maps, and tables.

    This class creates interactive maps, step and line plots, and data tables to display parking 
    information using Bokeh ColumnDataSource objects. It relies on the 'handler' (an instance of the 
    DataHandler class) to load, process, and transform data into sources that Bokeh can visualize.

    Attributes:
        - handler (DataHandler): An instance of DataHandler responsible for:
            - Loading and processing data from CSV files or PostgreSQL sources.
            - Transforming data into Bokeh ColumnDataSource objects.
            - Providing sources like `source_map`, `source_history`, and `source_table`.
        - latitude (float): Latitude in degrees.
        - longitude (float): Longitude in degrees
        - zoom_level (float): Zoom level for the map view.
        - p_map (Figure): Interactive map plot.
        - p_step (Figure): Step plot showing parking availability history.
        - p_line (Figure): Line plot showing parking availability history.
        - data_table (DataTable): A Bokeh data table displaying parking details.
        - data_table_url (DataTable): A Bokeh data table displaying parking website links.
        - switch_plot_button (RadioButtonGroup): button linked to the switch_plot method.
        - selection_callback (CustomJS): The JavaScript callback.
        - update_frequency (int): Frequency of layout updates in milliseconds.
        - bokeh_layout (Layout): Main Bokeh layout containing all visual elements.
    """

    def __init__(self, handler, visualizer_config):
        """
        Parameters:
        - handler (DataHandler): An instance of DataHandler responsible for:
            - Loading and processing data from CSV files or PostgreSQL sources.
            - Transforming data into Bokeh ColumnDataSource objects.
            - Providing sources like `source_map`, `source_history`, and `source_table`.
        - visualizer_config (BokehVisualizerConfig): Defines visualization configuration parameters including:
            - LATITUDE_LYON (float): Latitude in degrees.
            - LONGITUDE_LYON (float): Longitude in degrees.
            - ZOOM_LEVEL (float): Zoom level for the map view.
            - UPDATE_FREQUENCY (int): Frequency of layout updates in milliseconds.
        """
        self.handler = handler
        self.latitude = visualizer_config.LATITUDE_LYON
        self.longitude = visualizer_config.LONGITUDE_LYON
        self.zoom_level = visualizer_config.ZOOM_LEVEL
        self.p_map = figure()
        self.p_step = figure()
        self.p_line = figure()
        self.data_table = DataTable()
        self.data_table_url = DataTable()
        self.selection_callback = None
        self.switch_plot_button = RadioButtonGroup()
        self.update_frequency = visualizer_config.UPDATE_FREQUENCY
        self.bokeh_layout = column()

    def create_map_plot(self):
        """
        Creates an interactive Bokeh map plot bases on instance attributes.

        Updates:
        - p_map (Figure): The Bokeh map plot with parking data and interactive tools.
        """
        source_map = self.handler.source_map
        zoom_level =self.zoom_level

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

        lyon_x, lyon_y = latlon_to_webmercator(self.latitude, self.longitude)

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
        Computes padded axis ranges for a Bokeh plot.

        Returns:
        - tuple: Two Range1d objects representing x and y ranges with padding.
        """
        source_history = self.handler.source_history
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
        - p_step (Figure): Bokeh step plot.
        """
        source_history = self.handler.source_history

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
        - line_plot (Figure): Bokeh line plot.
        """
        source_history = self.handler.source_history

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
        - data_table (DataTable): A Bokeh data table displaying parking details.
        """
        source_table = self.handler.source_table
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
        - data_table_url (DataTable): A Bokeh data table displaying parking website links.
        """
        source_history =self.handler.source_history

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

    def switch_plot(self, attr, old, new):
        """
        Toggles the visibility between the step plot and line plot based on the selected option.

        Parameters:
        - attr (str): Attribute that triggered the callback (unused in this method).
        - old (int): Previous value of the selected plot.
        - new (int): Current value of the selected plot (0 for step plot, 1 for line plot).

        Updates Attributes:
        - p_step (Figure): Bokeh step plot.
        - p_line (Figure): Bokeh line plot.
        """
        p_step = self.p_step
        p_line = self.p_line
        selected_plot = new

        if selected_plot == 0:
            p_line.visible, p_step.visible = False, True
            
        elif selected_plot == 1:
            p_step.visible, p_line.visible = False, True

    def create_switch_plot_button(self):
        """
        Creates a radio button group to toggle between step and line plots.

        Updates:
        - switch_plot_button (RadioButtonGroup): button linked to the switch_plot method.
        """
        button_group = RadioButtonGroup(labels=["STEP PLOT", "LINE PLOT"], active=1)
        button_group.on_change("active", self.switch_plot)

        self.switch_plot_button = button_group

    def create_selection_callback(self):
        """
        Creates a CustomJS callback for updating "ColumnDataSource" and "Figure" object based on user selection.
        
        Updates Attributes:
        - selection_callback (CustomJS): The JavaScript callback.
        """
        selection_callback = CustomJS(
            args=dict(
                s_original=self.handler.source_original,
                s_map=self.handler.source_map,
                s_history=self.handler.source_history,
                s_table=self.handler.source_table,
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

    def get_current_parking_id(self, attr, old, new):
        """
        Updates the current parking ID based on user selection.

        Parameters:
        - attr (str): Attribute triggered by the callback.
        - old: Previous selected value.
        - new (list[int]): New selected value (index of the selection).

        Updates Attributes:
        - handler.current_parking_id (str): The ID of the parking selected by the user, extracted from 
            "self.handler.source_map.data["parking_id"] using the provided index.
        """
        if new:
            selected_index = new[0]
            self.handler.current_parking_id = self.handler.source_map.data['parking_id'][selected_index]

    def get_layout_title(self):
        """
        Create a styled Bokeh Div title for the layout, showing update frequency.

        Returns:
        -------
        - Div: A Bokeh Div with the layout title as HTML.
        """
        update_freq_minute = self.update_frequency // 60000
        
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
        Creates the Bokeh layout for the visualization.

        The layout includes:
        - A title.
        - A map plot and historical plots (step and line) with a toggle button.
        - Data tables for additional information.

        Updates and Returns:
        - bokeh_layout: The final Bokeh layout combining all elements.
        """
        title = self.get_layout_title()

        history_plot = column([self.p_step, self.p_line])   
        right_corner = column([history_plot, self.switch_plot_button])
        first_row = row([self.p_map, right_corner])
        bokeh_layout = column([title, first_row, self.data_table, self.data_table_url])

        self.bokeh_layout = bokeh_layout

        return self.bokeh_layout


def validate_env_password(pgsql_config):
    """
    Validates that the PostgreSQL password is set in the environment configuration.

    Parameters:
    - pqsql_config (PgsqlConfig): PostgreSQL connection configuration including:
            - PASSWORD, USER, HOST, PORT, DATABASE, TABLE.
    Raises:
    - EnvironmentError: If the "password" constant is not set in the configuration dictionary.
    """
    if not pgsql_config.PASSWORD:
        error_msg = (
            f"PGPASSWORD environment variable not set.\n"
            "Set it using the command: export PGPASSWORD='your_password_here'"
        )
        logger.critical(error_msg, exc_info=True)
        raise EnvironmentError(error_msg)

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

def main():
    """
    Main fucntion to produce interactive automatically updated Bokeh Layout. 
    
    This funcion:
        - initializes the database connection,
        - fetchs and process data,
        - prepares Bokeh ColumnDataSource objects,
        - builds an interactive Bokeh layout with a map, trend chart, and data table.
        - periodically fetches updates from the PostgreSQL database and synchronizes the visualizations.

    Note: Errors are logged, with up to five retries for database connection issues before stopping execution.
    """
    logger.info("Main process launched!")
    database_connection_error_count = 0
    pgsql_config = PgsqlConfig()
    handler_config = DataHandlerConfig()
    visualizer_config = BokehVisualizerConfig()

    try:
        validate_env_password(pgsql_config)

        handler = DataHandler(GENERAL_INFO_CSV_FILEPATH, pgsql_config, handler_config)
        handler.prepare_general_info_dataframe()
        handler.update_sources()

        visualizer = BokehVisualizer(handler, visualizer_config)
        visualizer.create_map_plot()
        visualizer.create_step_plot()
        visualizer.create_line_plot()
        visualizer.p_step.visible = False
        visualizer.create_data_table()
        visualizer.create_data_table_url()
        visualizer.create_switch_plot_button()

        visualizer.create_selection_callback()

        # Update step, line, data_table, data_url on user selection
        visualizer.handler.source_map.selected.js_on_change('indices', visualizer.selection_callback)
        # Update current_parking_id on user selection
        visualizer.handler.source_map.selected.on_change('indices', visualizer.get_current_parking_id)


        layout = visualizer.create_layout()
     
        curdoc().add_root(layout)  
        curdoc().add_periodic_callback(visualizer.handler.update_sources, visualizer.update_frequency)

    except DatabaseOperationError:
        database_connection_error_count += 1
        error_msg = f"Database connection attempt failed. Total failures: {database_connection_error_count}"
        logger.warning(error_msg, exc_info=True)

        if database_connection_error_count > 5:
            logger.critical("Database connection attempt failed over 5 times. Script stopped!")
            raise
        time.sleep(60)

main()