import pytest
from unittest.mock import MagicMock, patch
from src.client import ReitbuchClient
import httpx

@pytest.fixture
def client():
    with patch('src.client.httpx.Client') as mock_httpx:
        # Mock the client instance
        mock_instance = MagicMock()
        mock_httpx.return_value = mock_instance
        
        reitbuch = ReitbuchClient()
        # Bind the mock instance to our client object so we can assert on it
        reitbuch.client = mock_instance 
        yield reitbuch

def test_login_success(client):
    """Test successful login detection."""
    # Setup mock responses
    # 1. First GET to / to get PHPSESSID (handled by client init or explicit call?)
    #    Actually login just does POST usually.
    
    # Mock the POST response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '<html>... <a href="logout.php">abmelden</a> ...</html>'
    client.client.post.return_value = mock_response

    assert client.login("user", "pass") == True
    
def test_login_failure(client):
    """Test failed login detection."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    # Include 'id="loginform"' to trigger failure detection
    mock_response.text = '<html>... <form id="loginform"> ... <div class="alert-danger">Falsch</div> </form> ...</html>'
    client.client.post.return_value = mock_response

    assert client.login("user", "wrongpass") == False

def test_ajax_request(client):
    """Test AJAX request formatting."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "OK"
    client.client.post.return_value = mock_response
    
    params = {"step": "PRE"}
    client.ajax_request("cmd", params)
    
    # Verify the post call
    client.client.post.assert_called_once()
    args, kwargs = client.client.post.call_args
    assert args[0] == "/ajax.php"
    assert "data" in kwargs
    assert kwargs['data']['command'] == "cmd"
    assert "params" in kwargs['data'] # Should be json dumped
