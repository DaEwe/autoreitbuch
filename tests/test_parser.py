import pytest
from src.parser import parse_available_lessons

HTML_SAMPLE = """
<div class="col-md-2" id="col_2025-12-13"> 
    <div class="wp_event " onclick="window.location.href='event.php?e=12345';">
        <div class="wp_time">09:00 - 10:00</div>
        <div class="wp_text">Dressur Standard</div>
        <div class="wp_date">Some Date Info</div>
    </div>
    <div class="wp_event wp_event_past" onclick="window.location.href='event.php?e=67890';">
        <div class="wp_time">08:00 - 09:00</div>
        <div class="wp_text">Past Lesson</div>
    </div>
</div>
"""

def test_parse_simple_lessons():
    """Test parsing of a simple HTML structure."""
    lessons = parse_available_lessons(HTML_SAMPLE)
    
    assert len(lessons) == 2
    
    # Check first lesson (Bookable)
    l1 = lessons[0]
    assert l1['id'] == '12345'
    assert l1['title'] == 'Dressur Standard'
    assert l1['is_bookable'] == True
    
    # Check second lesson (Past)
    l2 = lessons[1]
    assert l2['id'] == '67890'
    assert l2['is_bookable'] == False

def test_parse_empty():
    """Test parsing empty/invalid HTML."""
    lessons = parse_available_lessons("<div>Nothing here</div>")
    assert len(lessons) == 0
