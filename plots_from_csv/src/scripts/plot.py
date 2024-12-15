'''
Module for creating a Bokeh Layout object to be embedded in HTML templates using Flask.

This module:
- Loads data from the specified CSV files
- Prepares and processes the data
- Creates Bokeh Figure and DataTable objects
- Builds a Bokeh Layout combining these elements

Dependencies:
- CSV files located in the "data" folder
'''

import ast
from bokeh.layouts import column, row
from bokeh.models import CDSView, ColumnDataSource, CustomJS, DataTable, DatetimeTickFormatter
from bokeh.models import HTMLTemplateFormatter, HoverTool, IndexFilter,  RadioButtonGroup, TableColumn, TapTool
from bokeh.plotting import figure, show
from bokeh.transform import linear_cmap
import datetime as dt
import math
import os
import pandas as pd
import xyzservices.providers as xyz

PARKING_HISTORY_CSV_FILEPATH = os.path.join("../data/parking_occupancy_history.csv")
GENERAL_INFO_CSV_FILEPATH = os.path.join("../data/parking_general_information.csv")

PARKING_ID_HOMEPAGE = 'LPA0740'
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

def prepare_global_dataframe(df_general_info, df_parking_history):
    """
    Merges general parking information with parking_history data.

    Combines data from `df_general_info` and `df_parking_history` into a single DataFrame, 
    enriching historical data with additional details like parking address, capacity, 
    and coordinates. Formats columns, renames for clarity, and sorts by date.

    Parameters:
    - df_general_info (pd.DataFrame): DataFrame containing general parking information.
    - df_parking_history (pd.DataFrame): DataFrame containing historical parking data.

    Returns:
    - pd.DataFrame: A merged and formatted DataFrame for further analysis or visualization.
    """
    df_global = pd.merge(
        left=df_parking_history,
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
    df_global.sort_values('date', inplace=True)

    return df_global

def prepare_sources(df_global, initial_parking_id=PARKING_ID_HOMEPAGE, data_table_columns_filter=DATA_TABLE_COLUMNS_FILTER):
    """
    Prepares data sources for visualizations.

    Generates ColumnDataSource objects for the global data, line plot, map, 
    and a transposed table based on the most recent values and selected parking.

    Parameters:
    - df_global (pd.DataFrame): The merged global DataFrame with parking data.
    - initial_parking_id (int): ID of the parking lot to initialize plots.
    - data_table_columns_filter (list): List of columns to include in the table.

    Returns:
    - tuple: Sources for global data, line plot, map, and transposed table.
    """

    df_more_recent_value = df_global.groupby('parking_id').agg({'date': 'max'})

    df_map = df_global.merge(df_more_recent_value , on=['parking_id', 'date'])

    df_line_plot = df_global[df_global['parking_id']==initial_parking_id]
    df_table = df_map[df_map['parking_id']==initial_parking_id]

    transposed_data = {
        "Field": data_table_columns_filter,
        "Value": [df_table.iloc[0][col] for col in data_table_columns_filter]
    }

    source_original = ColumnDataSource(df_global)
    source_line_plot = ColumnDataSource(df_line_plot)
    source_map = ColumnDataSource(df_map)
    source_table = ColumnDataSource(transposed_data)

    return source_original, source_line_plot, source_map, source_table

def add_circle_size_to_source_map(source_map, circle_size_bounds=CIRCLE_SIZE_BOUNDS):
    """
    Adds normalized circle sizes to the source map based on available spaces.

    Parameters:
    - source_map (ColumnDataSource): Map data source with parking availability.
    - circle_size_bounds (tuple): Min and max bounds for circle sizes.

    Returns:
    - None: Updates `source_map` in place with a `normalized_circle_size` field.
    """

    available_spaces_range = (
        min(source_map.data["nombre_de_places_disponibles"]),
        max(source_map.data["nombre_de_places_disponibles"])
        )
    normalized_circle_sizes = [normalize_number(x, available_spaces_range, circle_size_bounds)
                        for x in source_map.data["nombre_de_places_disponibles"]]
    source_map.data['normalized_circle_size'] = normalized_circle_sizes

def generate_map_plot(source_map, lyon_x, lyon_y, zoom_level=ZOOM_LEVEL):
    """
    Creates an interactive map plot with parking data.

    Parameters:
    - source_map (ColumnDataSource): Data source for map visualization.
    - lyon_x, lyon_y (float): Mercator coordinates for map center.
    - zoom_level (float): Zoom level for the map.

    Returns:
    - Figure: Bokeh map plot with hover and selection tools.
    """
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

    

    p_map = figure(
        x_range=(lyon_x - zoom_level, lyon_x + zoom_level),
        y_range=(lyon_y - zoom_level, lyon_y + zoom_level),
        x_axis_type="mercator",
        y_axis_type="mercator",
        tools=[hover_map, 'pan', 'wheel_zoom'],
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
        fill_alpha=1,
        )

    circle_renderer.nonselection_glyph = None
    circle_renderer.selection_glyph = None

    return p_map

def generate_line_plot(source_line_plot):
    """
    Creates a line plot to show the history of available parking spaces.

    Parameters:
    - source_line_plot (ColumnDataSource): Data source for the line plot.

    Returns:
    - Figure: Bokeh line plot with hover and zoom tools.
    """
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
        align = ('center', 'center')
    )

    p_line.line(
        "date",
        "nombre_de_places_disponibles",
        source=source_line_plot,
        line_width=2,
        legend_field = "parking",
        )
    
    p_line.legend.location = "top_left"
    p_line.xaxis.formatter = DatetimeTickFormatter(days="%d/%m/%Y")

    return p_line

def generate_data_table(source_table):
    """
    Creates a data table to display parking information.

    Parameters:
    - source_table (ColumnDataSource): Data source for the table.

    Returns:
    - DataTable: A Bokeh data table displaying parking details.
    """
    columns_tranposed = [
        TableColumn(field="Field", title="Champ"),
        TableColumn(field="Value", title="Valeur"),
    ]

    data_table = DataTable(
        source=source_table,
        columns=columns_tranposed,
        editable=True,
        width=1000,
        height=200,
        index_position=None,
        header_row=False,
        fit_columns = True,
        )

    return data_table

def generate_data_table_url(source_line_plot):
    """
    Creates a data table with clickable URLs for parking websites.

    Parameters:
    - source_line_plot (ColumnDataSource): Data source for the table.

    Returns:
    - DataTable: A Bokeh data table displaying parking website links.
    """
    cds_view = CDSView()
    cds_view.filter = IndexFilter([0])

    column = TableColumn(
        field="site_web",
        title="site web",
        formatter=HTMLTemplateFormatter(template='<a href="<%= site_web %>"><%= site_web %></a>')
        )

    data_url = DataTable(
        source=source_line_plot,
        columns=[column],
        editable=True,
        width=600,
        height=50,
        index_position=None,
        view=cds_view
        )
    
    return data_url

def create_selection_callback(source_map, source_line_plot, source_table, source_original):
    """
    Creates a CustomJS callback for updating data source based on user selection.
    
    Args:
        source_map (ColumnDataSource): The source for the map data.
        source_line_plot (ColumnDataSource): The source for the line plot data.
        source_table (ColumnDataSource): The source for the data table.
        source_original (ColumnDataSource): The source for the original dataset.
    
    Returns:
        CustomJS: The JavaScript callback.
    """
    callback = CustomJS(
        args=dict(s1=source_map, s2=source_line_plot, s3=source_table, s4=source_original),
        code=
        """
        var data_map = s1.data
        var data_original = s4.data
        var selected_index = cb_obj.indices[0]
                                        
        if (selected_index !== undefined) {
            var parking_id = data_map['identifier'][selected_index]

            var line_plot_data = {};
            for (var key in data_original) {
                line_plot_data[key] = [];
            }

            for (var i = 0; i < data_original['parking_id'].length; i++) {
                if (data_original['parking_id'][i] === parking_id) {
                    for (var key in data_original) {
                        line_plot_data[key].push(data_original[key][i]);
                    }
                }
            }

            s2.data = line_plot_data
        
            var max_date_index = 0
            var max_date = new Date(Math.max(...line_plot_data['date'].map(d => new Date(d))))

            for (var i = 0; i < line_plot_data['date'].length; i++) {
                if (new Date(line_plot_data['date'][i]).getTime() === max_date.getTime()) {
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
                var value = line_plot_data[key][max_date_index];

                table_data["Field"].push(key);
                table_data["Value"].push(value);
            }

            s3.data = table_data
        }
        """
    )
    return callback

def main():
    """
    Main function:  
    - Loads and processes data from CSV files.  
    - Prepares data sources for Bokeh visualizations.  
    - Creates interactive map, line plot, and data table components.  
    - Builds and returns a cohesive Bokeh layout.
    """
    df_general_info = prepare_general_info_dataframe(GENERAL_INFO_CSV_FILEPATH)
    df_parking_history = pd.read_csv(PARKING_HISTORY_CSV_FILEPATH, index_col='id', parse_dates=[4])
    df_global = prepare_global_dataframe(df_general_info, df_parking_history)
    source_original, source_line_plot, source_map, source_table = prepare_sources(df_global)
    add_circle_size_to_source_map(source_map, circle_size_bounds=CIRCLE_SIZE_BOUNDS)
    lyon_x, lyon_y = latlon_to_webmercator(LATITUDE_LYON, LONGITUDE_LYON)
    p_map = generate_map_plot(source_map, lyon_x, lyon_y, zoom_level=ZOOM_LEVEL)
    p_line_plot = generate_line_plot(source_line_plot)
    data_table = generate_data_table(source_table)
    data_table_url = generate_data_table_url(source_line_plot)
    callback = create_selection_callback(source_map, source_line_plot, source_table, source_original)
    source_map.selected.js_on_change('indices', callback)

    first_row_layout = row([p_map, p_line_plot])
    bokeh_general_layout = column([first_row_layout, data_table, data_table_url])
    return bokeh_general_layout

bokeh_general_layout = main()


