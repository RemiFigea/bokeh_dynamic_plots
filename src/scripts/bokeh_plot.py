import ast
from bokeh.layouts import column, row
from bokeh.models import CDSView, ColumnDataSource, CustomJS, DataTable, DateFormatter, DatetimeTickFormatter
from bokeh.models import HTMLTemplateFormatter, HoverTool, IndexFilter, TableColumn, TapTool
from bokeh.plotting import curdoc, figure, show
from bokeh.transform import linear_cmap
import datetime as dt
import math
import os
import pandas as pd
#from sqlalchemy import create_engine
import xyzservices.providers as xyz

# GENERAL_INFO_URL = "https://data.grandlyon.com/fr/datapusher/ws/rdata/lpa_mobilite.parking_lpa_2_0_0/all.csv?maxfeatures=-1&filename=parkings-lyon-parc-auto-metropole-lyon-v2"
DIRNAME = os.path.dirname(__file__)
REALTIME_CSV_FILEPATH = os.path.join(DIRNAME, "../data/parking_occupancy_history.csv")
GENERAL_INFO_CSV_FILEPATH = os.path.join(DIRNAME, "../data/parking_general_information.csv")

LATITUDE_LYON = 45.764043
LONGITUDE_LYON = 4.835659
PARKING_ID_HOMEPAGE = 'LPA0740'

# # Congigurate PostgreSQL connexion
# HOST = "localhost"
# PORT = "5432"
# DATABASE = "parking_data"
# USER = "postgres"
# PASSWORD = "****"
# TABLE_REALTIME = "parking_data"


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

df_general_info = prepare_general_info_dataframe(GENERAL_INFO_CSV_FILEPATH)

# engine = create_engine(f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}")
# query = f"SELECT * FROM {TABLE_REALTIME};"
 
# df_realtime = pd.read_sql_query(query, engine)

df_realtime = pd.read_csv(REALTIME_CSV_FILEPATH, index_col='id', parse_dates=[4])
df_realtime.rename(
    columns={
        "nb_of_available_parking_spaces": "nombre_de_places_disponibles",
        },
    inplace=True
    )

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
df_global.sort_values('date', inplace=True)

df_more_recent_value = df_global.groupby('parking_id').agg({'date': 'max'})

df_map = df_global.merge(df_more_recent_value , on=['parking_id', 'date'])

# Select an arbitrary parking to initialize lineplot and table_plot for homepage template
df_homepage_line_plot = df_global[df_global['parking_id']==PARKING_ID_HOMEPAGE]
df_homepage_table = df_map[df_map['parking_id']==PARKING_ID_HOMEPAGE]

# Filter and transpose data for Bokeh Data Table display
filter_columns = [
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
transposed_data = {
    "Field": filter_columns,
    "Value": [df_homepage_table.iloc[0][col] for col in filter_columns]
}

# PREPARE SOURCE FOR BOKEH PLOTTING
# ---------------------------------
source_original = ColumnDataSource(df_global)
source_line_plot = ColumnDataSource(df_homepage_line_plot)
source_map = ColumnDataSource(df_map)
source_table = ColumnDataSource(transposed_data)

# PREPARE MAP PLOTTING
# --------------------
circle_size_bounds = (10, 25)
available_spaces_range = (
    min(source_map.data["nombre_de_places_disponibles"]),
    max(source_map.data["nombre_de_places_disponibles"])
    )
color_mapper = linear_cmap(field_name="nombre_de_places_disponibles",
                        palette="Viridis256",
                        low=available_spaces_range[0],
                        high=available_spaces_range[1])

normalized_circle_sizes = [normalize_number(x, available_spaces_range, circle_size_bounds)
                    for x in source_map.data["nombre_de_places_disponibles"]]

source_map.data['normalized_circle_size'] = normalized_circle_sizes


hover_map = HoverTool(
    tooltips = [
        ('nom', '@parking'),
        ('places disponibles', "@nombre_de_places_disponibles"),
        ('capacité', '@{capacité_total}'),
        ],
)

lyon_x, lyon_y = latlon_to_webmercator(LATITUDE_LYON, LONGITUDE_LYON)
zoom_level = 10000

p_map = figure(
    x_range=(lyon_x - zoom_level, lyon_x + zoom_level),
    y_range=(lyon_y - zoom_level, lyon_y + zoom_level),
    x_axis_type="mercator",
    y_axis_type="mercator",
    tools=[hover_map, 'pan', 'wheel_zoom']
    )

tap_tool = TapTool()
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

# PREPARE LINE PLOTTING
# ---------------------
hover_line_plot = HoverTool(
    tooltips = [
        ('Places disponibles', "@nombre_de_places_disponibles"),
        ('Heure', '@date{%a-%H:%M:%S}'),
    ],
    formatters={'@date': 'datetime'},
)

p_line_plot = figure(
    title=f"Historique des places disponibles", 
    height = 400,
    width = 700,
    x_axis_type="datetime",
    x_axis_label="Date", 
    y_axis_label="Nombre de places disponibles",
    tools=[hover_line_plot, "crosshair", "pan", "wheel_zoom"],
    
)
p_line_plot.line(
    "date",
    "nombre_de_places_disponibles",
    source=source_line_plot,
    line_width=2,
    legend_field = "parking"
    )

p_line_plot.xaxis.formatter = DatetimeTickFormatter(days="%d/%m/%Y")


# PREPARE DATA TABLE
# ------------------
columns_tranposed = [
    TableColumn(field="Field", title="Champ"),
    TableColumn(field="Value", title="Valeur"),
]

data_table = DataTable(
    source=source_table,
    columns=columns_tranposed,
    editable=True,
    width=1000,
    height=250,
    index_position=None,
    header_row=False,
    )

cds_view = CDSView()
cds_view.filter = IndexFilter([0])

data_url = DataTable(
    source=source_line_plot,
    columns=[TableColumn(field="site_web", title="site web", formatter=HTMLTemplateFormatter(template='<a href="<%= site_web %>"><%= site_web %></a>'))],
    editable=True,
    width=600,
    height=600,
    index_position=None,
    view=cds_view
    )

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

        // Assurez-vous que `line_plot_data` contient les valeurs requises
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

source_map.selected.js_on_change('indices', callback)

first_row = row([p_map, p_line_plot])

bokeh_layout = column([first_row, data_table, data_url])
show(bokeh_layout)