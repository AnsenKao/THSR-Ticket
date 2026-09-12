import unittest
from typing import List
from thsr_ticket.controller.confirm_train_flow import ConfirmTrainFlow
from thsr_ticket.configs.web.param_schema import Train
from thsr_ticket.model.db import Record

class MockRecord:
    def __init__(self, preferred_trains=None):
        self.preferred_trains = preferred_trains

class TestPreferredTrain(unittest.TestCase):
    def setUp(self):
        # Create some dummy trains
        self.trains = [
            Train(id=101, depart="10:00", arrive="12:00", travel_time="2h", discount_str="", form_value="train_101"),
            Train(id=202, depart="11:00", arrive="13:00", travel_time="2h", discount_str="", form_value="train_202"),
            Train(id=303, depart="12:00", arrive="14:00", travel_time="2h", discount_str="", form_value="train_303"),
        ]
        self.flow = ConfirmTrainFlow(client=None, book_resp=None)

    def test_no_preference(self):
        """Test allowing any train when no preference is set"""
        self.flow.record = MockRecord(preferred_trains=None)
        selected = self.flow.select_available_trains(self.trains)
        self.assertEqual(selected, "train_101", "Should select first train by default")

    def test_preference_match_first(self):
        """Test match matching the first available preference"""
        self.flow.record = MockRecord(preferred_trains=["202"])
        selected = self.flow.select_available_trains(self.trains)
        self.assertEqual(selected, "train_202", "Should select train 202")

    def test_preference_match_second_choice(self):
        """Test matching the second choice if first is not available"""
        self.flow.record = MockRecord(preferred_trains=["999", "303"])
        selected = self.flow.select_available_trains(self.trains)
        self.assertEqual(selected, "train_303", "Should select train 303 as 999 is not available")

    def test_preference_no_match(self):
        """Test raising error when no preference matches"""
        self.flow.record = MockRecord(preferred_trains=["999", "888"])
        with self.assertRaises(ValueError) as cm:
            self.flow.select_available_trains(self.trains)
        self.assertIn("Preferred trains", str(cm.exception))

    def test_preference_leading_zero(self):
        """Test matching four-digit train codes written with a leading zero"""
        self.flow.record = MockRecord(preferred_trains=["0202"])
        selected = self.flow.select_available_trains(self.trains)
        self.assertEqual(selected, "train_202", "Should match 0202 against train 202")

    def test_preference_leading_zero_no_match(self):
        """Test that a leading zero does not create a false match"""
        self.flow.record = MockRecord(preferred_trains=["0999"])
        with self.assertRaises(ValueError):
            self.flow.select_available_trains(self.trains)

    def test_preference_whitespace_handling(self):
        """Test matching with whitespace in input"""
        self.flow.record = MockRecord(preferred_trains=[" 202 "])
        selected = self.flow.select_available_trains(self.trains)
        self.assertEqual(selected, "train_202", "Should handle whitespace in preferences")

if __name__ == '__main__':
    unittest.main()
