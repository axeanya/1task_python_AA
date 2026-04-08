import unittest
from unittest.mock import patch, MagicMock
from main import workDB

# python -m unittest tests/test_connection.py


class TestWorkDB(unittest.TestCase):

    # instead of psycopg2 using mock
    @patch("main.psycopg2.connect")
    def test_connect_success(self, mock_psycopg_connect):
        # Test that connection is successful and stored
        # Setup: Create a fake connection object
        mock_conn = MagicMock()  # MagicMock() can pretend anything
        mock_conn.closed = False
        mock_psycopg_connect.return_value = mock_conn

        db = workDB()

        # Try to connect
        db.connect()

        # Check if the connection was assigned
        self.assertEqual(db.conn, mock_conn)
        mock_psycopg_connect.assert_called_once()
        print("Test passed: Success logic works!")

    @patch("main.psycopg2.connect")
    def test_connect_failure(self, mock_psycopg_connect):
        # Test that an error is handled if connection fails
        # Setup: Make the mock throw an error
        mock_psycopg_connect.side_effect = Exception("Connection timeout")

        db = workDB()

        # Check if the exception is raised
        with self.assertRaises(Exception) as context:
            db.connect()

        self.assertTrue("Connection timeout" in str(context.exception))
        print("Test passed: Failure logic works!")
