"""
Unit tests for functions of module plot_realtime.py.

This script provides test cases for the following methods of DataHandler class:
- get_realtime_dataframe,
- validate_realtime_df_columns,
- add_circle_size_to_source_map.
"""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/scripts')))

from bokeh.models import ColumnDataSource
import numpy as np
import pandas as pd
from scripts.plot_realtime import DatabaseOperationError, DataHandler
from scripts.config.config import DataHandlerConfig, PgsqlConfig
import unittest
from unittest.mock import MagicMock, patch


class TestDataHandler(unittest.TestCase):
    def setUp(self):
        """Initialize test data for the test cases."""
        mock_csv_filepath = MagicMock()
        pgsql_config = PgsqlConfig()
        handler_config = DataHandlerConfig()
        self.handler = DataHandler(mock_csv_filepath, pgsql_config, handler_config)   


    @patch("scripts.plot_realtime.create_engine")
    def test_get_realtime_dataframe_connexion_failed(self, mock_create_engine):
        """Test case where connexion to database fail."""
        
        mock_create_engine.side_effect = Exception("Simulated connection error")

        with self.assertRaises(DatabaseOperationError) as context:
            self.handler.get_realtime_dataframe()
        
        expected_msg = "Error attemting to fetch data from PostgreSQL"
        self.assertTrue(
            expected_msg in str(context.exception),
            f"""Error message should be: {expected_msg},
            error message raised: {context.exception}"""
            )
        self.assertTrue(mock_create_engine.called)
    

    @patch("scripts.plot_realtime.pd.read_sql_query")
    @patch("scripts.plot_realtime.create_engine")
    def test_get_realtime_dataframe_none(self, mock_create_engine, mock_read_sql_query):
        """Test case where dataframe is None."""
        
        mock_read_sql_query.side_effect = [None]

        with self.assertRaises(DatabaseOperationError) as context:
            self.handler.get_realtime_dataframe()
        
        expected_msg = "Error: Query result returned None instead of a valid dataframe."
        self.assertTrue(
            expected_msg in str(context.exception),
            f"""Error message should be: {expected_msg},
            error message raised: {context.exception}"""
            )
        self.assertTrue(mock_create_engine.called)
        self.assertTrue(mock_read_sql_query.called)


    @patch("scripts.plot_realtime.pd.read_sql_query")
    @patch("scripts.plot_realtime.create_engine")
    def test_get_realtime_dataframe_empty(self, mock_create_engine, mock_read_sql_query):
        """Test case where dataframe is empty."""
        
        mock_read_sql_query.return_value = pd.DataFrame()

        with self.assertRaises(DatabaseOperationError) as context:
            self.handler.get_realtime_dataframe()
        
        expected_msg = f"Error: Query executed successfully, but the table '{self.handler.pgsql_config.TABLE}' is empty."
        self.assertTrue(
            expected_msg in str(context.exception),
            f"""Error message should be: {expected_msg},
            error message raised: {context.exception}"""
            )
        self.assertTrue(mock_create_engine.called)
        self.assertTrue(mock_read_sql_query.called)


    def test_validate_realtime_df_columns_valid(self):
        """Test case where the dataframe has the required columns."""

        columns = list(self.handler.required_columns_set)
        df_realtime = pd.DataFrame(columns=columns)
        
        result = self.handler.validate_realtime_df_columns(df_realtime)
        
        self.assertIsNone(result, "Should have detected correct columns.")


    def test_validate_realtime_df_columns_missing_columns(self):
        """Test case where some required columns are missing."""

        columns = ['parking', 'date', 'status']
        df_realtime = pd.DataFrame(columns=columns)
        missing_columns_set = self.handler.required_columns_set - set(columns)
        
        with self.assertRaises(ValueError) as context:
            self.handler.validate_realtime_df_columns(df_realtime)
        
        expected_msg = f"Missing columns: {missing_columns_set}"
        self.assertTrue(
            expected_msg in str(context.exception),
            f"""Error message should be: {expected_msg},
            error message raised: {context.exception}"""
            )
        
    def test_add_circle_size_to_source_map_single_value(self):
        """Test case where "nombre_de_places_disponibles" column has a single unique value."""
        
        mock_source_map_list = [10, 10, 10, 10]
        circle_size_target = sum(self.handler.circle_size_bounds)/ 2
        target_circle_size = [circle_size_target] * len(mock_source_map_list)
        
        self.handler.source_map.data["nombre_de_places_disponibles"] = mock_source_map_list
        self.handler.add_circle_size_to_source_map()

        self.assertListEqual(
            self.handler.source_map.data["normalized_circle_size"],
            target_circle_size
            ,
            """The 'normalized_circle_size' values should be equal to the mean of 'circle_size_bounds' attributs."""
        )

    def test_add_circle_size_to_source_map_circle_size_bound_equal(self):
        """Test case where the specified circle size bounds are equal."""
        mock_source_map_list = [0, 1, 2, 3]
        self.handler.circle_size_bounds = 10, 10
        circle_size_target = sum(self.handler.circle_size_bounds)/ 2
        target_circle_size = [circle_size_target] * len(mock_source_map_list)
        
        self.handler.source_map.data["nombre_de_places_disponibles"] = mock_source_map_list
        self.handler.add_circle_size_to_source_map()

        self.assertListEqual(
            self.handler.source_map.data["normalized_circle_size"],
            target_circle_size
            ,
            """The 'normalized_circle_size' values should be equal to the mean of 'circle_size_bounds' attributs."""
        )
    
    def test_add_circle_size_to_source_map_circle_general(self):
        """Test case where the specified circle size bounds are equal."""
        
        mock_source_map_list = [0, 20, 40]
        circle_size_bounds = self.handler.circle_size_bounds
        target_circle_size = [min(circle_size_bounds), sum(circle_size_bounds)/2, max(circle_size_bounds)]
        
        self.handler.source_map.data["nombre_de_places_disponibles"] = mock_source_map_list
        self.handler.add_circle_size_to_source_map()

        self.assertListEqual(
            self.handler.source_map.data["normalized_circle_size"],
            target_circle_size
            ,
            """The 'normalized_circle_size' values are not equal to expectation."""
        )


if __name__ == '__main__':
    unittest.main()