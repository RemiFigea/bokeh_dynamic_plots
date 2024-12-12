"""
Unit tests for functions of module populate_db.py.

This script provides test cases for the `parking_state_has_changed` and 
`collect_changes` functions, ensuring their correctness in detecting and 
updating parking state changes based on new data.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from populate_db import parking_state_has_changed, collect_changes
import sys
import time
import unittest

class TestParkingState(unittest.TestCase):
    """Test cases for the parking_state_has_changed and collect_changes functions."""

    def setUp(self):
        """Initialize test data for the test cases."""
        self.timestamp = int(time.time())
        # Data representing new parking states
        self.df = pd.DataFrame([
            ['ID1', False, 17, self.timestamp],
            ['ID2', False, 12, self.timestamp],
            ['ID3', False, 10, self.timestamp]
        ], columns=['parking_id', 'ferme', 'nb_of_available_parking_spaces', 'date'])

        # Current parking state
        self.df_state = pd.DataFrame([
            ['ID1', False, 15],
            ['ID2', False, 12],
            ['ID3', False, 17]
        ], columns=['parking_id', 'ferme', 'nb_of_available_parking_spaces'])

    def test_parking_state_has_changed(self):
        """
        Test if the function correctly detects changes in parking state.
        """
        row = self.df.iloc[0]
        result = parking_state_has_changed(row, self.df_state)
        self.assertTrue(result, "Should detect a change for parking ID1.")

        row = self.df.iloc[1]
        result = parking_state_has_changed(row, self.df_state)
        self.assertFalse(result, "Should not detect a change for parking ID2.")

        # Test case where a new parking ID does not exist in df_state
        row = pd.Series(['ID4', False, 20, self.timestamp], index=self.df.columns)
        result = parking_state_has_changed(row, self.df_state)
        self.assertTrue(result, "Should detect that parking ID4 does not exist in the previous state.")

    def test_collect_changes(self):
        """
        Test the collect_changes function to detect and update changes in parking state.
        """
        batch_df = self.df
        df_state = self.df_state

        # Target DataFrame representing expected state after collecting changes
        df_state_target = pd.DataFrame([
            ['ID1', False, 17],
            ['ID2', False, 12],
            ['ID3', False, 10]
        ], columns=['parking_id', 'ferme', 'nb_of_available_parking_spaces'])

        # Expected changes detected
        changes_list_target = [
            {'parking_id': 'ID1', 'ferme': False, 'nb_of_available_parking_spaces': 17, 'date': self.timestamp},
            {'parking_id': 'ID3', 'ferme': False, 'nb_of_available_parking_spaces': 10, 'date': self.timestamp}
        ]

        # Collect changes and update the DataFrame state
        changes_list, df_state_updated = collect_changes(batch_df, df_state)

        self.assertListEqual(changes_list, changes_list_target, "Changes list should match the expected target changes.")
        pd.testing.assert_frame_equal(df_state_updated, df_state_target, check_dtype=False)

if __name__ == '__main__':
    unittest.main()
