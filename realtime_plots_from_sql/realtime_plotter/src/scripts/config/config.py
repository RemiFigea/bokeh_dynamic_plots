"""
This module defines configuration classes for PostgreSQL database connection, data handling, and data visualization.

It contains the following classes:
    - PgsqlConfig: Configuration for PostgreSQL connection parameters (user, password, host, port, database, table).
    - DataHandlerConfig: Configuration constants for data handling, including required columns and display settings.
    - BokehVisualizerConfig: Configuration parameters for Bokeh visualization, such as location, zoom level, and update frequency.

IMPORTANT: Customize the values in PgsqlConfig to match your environment and database setup.
"""
import os

PGPASSWORD = os.environ.get('PGPASSWORD')

class PgsqlConfig:
    """
    Defines PostgreSQL database connection parameters.

    Constants:
        - PASSWORD (str): Password for PostgreSQL connection (retrieved from environment variable).
        - USER (str): Username for PostgreSQL authentication.
        - HOST (str): Host address of the PostgreSQL server.
        - PORT (str): Port on which PostgreSQL is running.
        - DATABASE (str): Name of the PostgreSQL database.
        - TABLE (str): Table containing parking information.
        
    IMPORTANT: Customize these values to match your environment and database setup.
    """    
    PASSWORD = PGPASSWORD
    USER = "postgres"              
    HOST = "172.17.0.1"
    # HOST = "172.31.4.218"      
    PORT = "5432"
    DATABASE = "parking_lyon_db"
    TABLE =  "parking_table"

class DataHandlerConfig:
    """
    Defines configuration parameters for class DataHandler.

    Constants:
        - REQUIRED_COLUMNS_SET (set[str]):  Required columns for data processing.
        - CIRCLE_SIZE_BOUNDS (tuple): Min and max bounds for circle sizes.
        - HOMEPAGE_PARKING_ID: parking ID related to the Figure objects to be displayed on the homepage layout.
        - DATA_TABLE_COLUMNS_FILTER (list[str]):  Columns to be shown in the DataTable view.
    """
    REQUIRED_COLUMNS_SET = {"parking_id", "nb_of_available_parking_spaces", "date"}
    CIRCLE_SIZE_BOUNDS = (10, 25)
    HOMEPAGE_PARKING_ID = 'LPA0740'
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

class BokehVisualizerConfig:
    """
    Defines configuration parameters for class BokehVisualizerConfig.

    Constants:
        - LATITUDE_LYON (float): Latitude in degrees.
        - LONGITUDE_LYON (float): Longitude in degrees.
        - ZOOM_LEVEL (float): Zoom level for the map view.
        - UPDATE_FREQUENCY (int): Frequency of layout updates in milliseconds.
    """
    LATITUDE_LYON = 45.764043
    LONGITUDE_LYON = 4.835659
    ZOOM_LEVEL = 10000
    UPDATE_FREQUENCY = 60000 #1 minutes