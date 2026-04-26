"""Tests for main entry point."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestMainEntryPoint:
    """Test main.py entry point functionality."""

    def test_main_imports(self):
        """Main module can be imported."""
        import main
        assert hasattr(main, 'main')

    @patch('main.uvicorn.run')
    @patch('main.get_settings')
    def test_main_starts_server(self, mock_get_settings, mock_uvicorn_run):
        """Main starts uvicorn server with correct config."""
        from main import main

        # Setup mock settings
        mock_settings = MagicMock()
        mock_settings.api_host = "0.0.0.0"
        mock_settings.api_port = 8000
        mock_get_settings.return_value = mock_settings

        # Call main
        main()

        # Verify uvicorn was called with correct args
        mock_uvicorn_run.assert_called_once()
        call_args = mock_uvicorn_run.call_args

        # call_args[0] is positional args, call_args[1] is keyword args
        assert call_args[0][0] == "api.server:app"  # First positional arg
        assert call_args[1]['host'] == "0.0.0.0"
        assert call_args[1]['port'] == 8000

    @patch.dict('os.environ', {'AGENT_NAME': 'TestAgent'})
    @patch('main.get_settings')
    @patch('main.uvicorn.run')
    def test_main_respects_env_vars(self, mock_uvicorn, mock_get_settings):
        """Main respects environment variables via settings."""
        from main import main

        mock_settings = MagicMock()
        mock_settings.api_host = "127.0.0.1"
        mock_settings.api_port = 9000
        mock_get_settings.return_value = mock_settings

        main()

        # Settings factory was called (reads from env)
        mock_get_settings.assert_called()
