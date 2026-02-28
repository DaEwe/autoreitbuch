import unittest
from unittest.mock import MagicMock, patch
import sys
import os

import sys
from unittest.mock import MagicMock
sys.modules["httpx"] = MagicMock()

# Set environment variables required by main.py
os.environ["REITBUCH_USER"] = "testuser"
os.environ["REITBUCH_PASSWORD"] = "testpass"

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from main import main
from client import ReitbuchClient

class TestBookingParameters(unittest.TestCase):
    @patch('main.ReitbuchClient')
    @patch('main.parse_available_lessons')
    @patch('argparse.ArgumentParser.parse_args')
    def test_booking_parameters(self, mock_args, mock_parser, MockClient):
        # Setup mocks
        mock_client_instance = MockClient.return_value
        mock_client_instance.login.return_value = True
        
        # Mock args to trigger booking
        mock_args.return_value = MagicMock(book=True, date="22.12.2025")
        
        # Mock weekly plan response (irrelevant for this test, but needed)
        mock_client_instance.get_weekly_plan.return_value = "<html>Mock Week Plan</html>"
        
        # Mock parser to return a bookable lesson
        mock_parser.return_value = [{
            'id': '12345',
            'title': 'Dressur Standard',
            'time': '09:00',
            'date_context': '2025-12-22',
            'is_bookable': True
        }]
        
        # Mock regex search for loginuid in main.py
        # We need to patch re.search logic or just ensure get_weekly_plan returns HTML with loginuid
        # But main.py calls client.get_weekly_plan, then parses it.
        # It also does a regex search on the HTML for loginuid.
        mock_client_instance.get_weekly_plan.return_value = '<html><input id="loginuid" name="loginuid" value="3832"></html>'
        
        # Mock pre-check response
        mock_client_instance.ajax_request.side_effect = [
            "AVAILABLE", # First call is PRE check
            "erfolgreich" # Second call is EVBK booking
        ]
        
        # Run main
        try:
            main()
        except SystemExit:
            pass # Expected if main exits
            
        # Verify ajax_request calls
        # We expect two calls. Use filtering to find the EVBK one.
        
        calls = mock_client_instance.ajax_request.call_args_list
        booking_call = None
        for call in calls:
            args, kwargs = call
            if len(args) > 1 and isinstance(args[1], dict) and args[1].get('step') == 'EVBK':
                booking_call = args[1]
                break
                
        self.assertIsNotNone(booking_call, "Booking call (EVBK) not found")
        
        # Verify parameters against curl call expectations
        expected_params = {
            "loginuid": "3832",
            "step": "EVBK",
            "next": "BOOK_W",
            "eventid": "12345",
            "courseid": "0",
            "selanicls": "S",
            "selanimal": "S:0",
            "note": "",
            "selpayopt": "BILL"
        }
        
        # Check that we didn't send extra unwanted params
        unwanted_params = ["agb_ok", "dat_ok", "nutz_ok"]
        for p in unwanted_params:
            self.assertNotIn(p, booking_call, f"Parameter {p} should have been removed")
            
        # Check expected params
        for key, val in expected_params.items():
            self.assertEqual(booking_call.get(key), val, f"Parameter {key} mismatch")

if __name__ == '__main__':
    unittest.main()
