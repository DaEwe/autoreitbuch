
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

# Import main module (will use real client initially, but we will patch it)
import main

class TestBookingLogic(unittest.TestCase):
    
    @patch('main.ReitbuchClient')
    def test_booking_logic_available(self, MockClient):
        """Test that BOOK_T is used when no waitlist string is present."""
        
        # Setup mock behavior
        mock_instance = MockClient.return_value
        mock_instance.login.return_value = True
        
        # 1. get_weekly_plan returns HTML with a target lesson
        mock_instance.get_weekly_plan.return_value = """
        <html><body>
        <div id="col_2025-12-27">
            <div class="wp_event" onclick="window.location.href='event.php?e=123';">
                <div class="wp_text">Dressur Standard</div>
                <div class="wp_date">09:00</div>
            </div>
        </div>
        </body></html>
        """
        
        # 2. PRE step response (Availability check)
        mock_instance.ajax_request.side_effect = [
            "<div>Möchten Sie buchen? <input id='loginuid' value='555'></div>", 
            "Buchung erfolgreich"
        ]

        test_args = ['program', '--book', '--date', '27.12.2025']
        with patch.object(sys, 'argv', test_args):
            with patch.dict(os.environ, {'REITBUCH_USER': 'u', 'REITBUCH_PASSWORD': 'p'}):
                try:
                    main.main()
                except SystemExit:
                    pass
                    
        calls = mock_instance.ajax_request.call_args_list
        booking_call = None
        for args, kwargs in calls:
             if args[0] == "ax.checkin.showcheckin":
                 p = args[1]
                 if p.get('step') == 'EVBK':
                     booking_call = p
        
        self.assertIsNotNone(booking_call)
        self.assertEqual(booking_call['next'], 'BOOK_T', "Should use BOOK_T when available")
        self.assertEqual(booking_call['eventid'], '123')


    @patch('main.ReitbuchClient')
    def test_booking_logic_waitlist(self, MockClient):
        """Test that BOOK_W is used when waitlist string is present."""
        
        mock_instance = MockClient.return_value
        mock_instance.login.return_value = True
        
        mock_instance.get_weekly_plan.return_value = """
        <html><body>
        <div id="col_2025-12-27">
            <div class="wp_event" onclick="window.location.href='event.php?e=456';">
                <div class="wp_text">Dressur Standard</div>
                <div class="wp_date">09:00</div>
            </div>
        </div>
        </body></html>
        """
        
        mock_instance.ajax_request.side_effect = [
            "<div>Leider voll. Nur Warteliste möglich.</div>", 
            "Buchung auf Warteliste erfolgreich"
        ]

        test_args = ['program', '--book', '--date', '27.12.2025']
        with patch.object(sys, 'argv', test_args):
            with patch.dict(os.environ, {'REITBUCH_USER': 'u', 'REITBUCH_PASSWORD': 'p'}):
                try:
                    main.main()
                except SystemExit:
                    pass

        calls = mock_instance.ajax_request.call_args_list
        booking_call = None
        for args, kwargs in calls:
             if args[0] == "ax.checkin.showcheckin":
                 p = args[1]
                 if p.get('step') == 'EVBK':
                     booking_call = p
        
        self.assertIsNotNone(booking_call)
        self.assertEqual(booking_call['next'], 'BOOK_W', "Should use BOOK_W when Waitlist mentioned")
        self.assertEqual(booking_call['eventid'], '456')

if __name__ == '__main__':
    unittest.main()
