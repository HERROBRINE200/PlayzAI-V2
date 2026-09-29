import os
import platform
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

AGENT_DIR = Path(__file__).parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

import agent


class TestWindowsAgent(unittest.TestCase):

    def test_telemetry_gathering(self):
        telemetry = agent.get_system_telemetry()
        self.assertIn("platform", telemetry)
        self.assertIn("network_status", telemetry)
        self.assertEqual(telemetry["network_status"], "online")
        self.assertIn("storage_percent", telemetry)

    def test_safe_diagnostics_action(self):
        res = agent.execute_action("get_status", {})
        self.assertTrue(res["ok"])
        self.assertIn("telemetry", res)

    def test_file_create_read_delete_cycle(self):
        import tempfile
        test_dir = tempfile.mkdtemp()
        test_file = os.path.join(test_dir, "playzai_agent_test.txt")

        # Write
        write_res = agent.execute_action("write_file", {"path": test_file, "content": "Hello Agent!"})
        self.assertTrue(write_res["ok"])

        # Read
        read_res = agent.execute_action("read_file", {"path": test_file})
        self.assertTrue(read_res["ok"])
        self.assertEqual(read_res["content"], "Hello Agent!")

        # List
        list_res = agent.execute_action("list_dir", {"path": test_dir})
        self.assertTrue(list_res["ok"])
        self.assertTrue(any(item["name"] == "playzai_agent_test.txt" for item in list_res["items"]))

        # Delete
        del_res = agent.execute_action("delete_file", {"path": test_dir})
        self.assertTrue(del_res["ok"])
        self.assertFalse(os.path.exists(test_dir))

    def test_file_boundary_protection(self):
        # Refusal on root path
        res = agent.execute_action("delete_file", {"path": "/"})
        self.assertFalse(res["ok"])
        self.assertIn("Refusing", res["error"])

    def test_command_runner(self):
        # Safe echo command
        res = agent.execute_action("run_command", {"command": "echo HelloPlayzAI"})
        self.assertTrue(res["ok"])
        self.assertEqual(res["exit_code"], 0)
        self.assertIn("HelloPlayzAI", res["stdout"])
        self.assertIn("execution_time_ms", res)
        self.assertFalse(res["truncated"])

    def test_obs_action_handling_and_status(self):
        # When OBS is not running, status should report real process/ws status honestly
        res = agent.execute_action("obs_status", {})
        self.assertTrue(res["ok"])
        self.assertIn("obs_process_running", res)
        self.assertIn("websocket_connected", res)
        self.assertIn("recording", res)

    def test_obs_mocked_ws_command(self):
        with patch("agent.send_obs_ws_request") as mock_obs_ws:
            mock_obs_ws.return_value = {
                "ok": True,
                "request_type": "StartRecord",
                "status": {"result": True},
                "response_data": {},
            }
            res = agent.execute_action("obs_record_start", {})
            self.assertTrue(res["ok"])
            self.assertEqual(res["action"], "obs_record_start")
            self.assertIn("OBS recording started", res["message"])

    def test_minecraft_action_handling_and_status(self):
        res = agent.execute_action("minecraft_status", {})
        self.assertTrue(res["ok"])
        self.assertIn("process_status", res)
        self.assertIn("rcon_connected", res)

    def test_minecraft_mocked_rcon_command(self):
        with patch("agent.send_minecraft_rcon_command") as mock_rcon:
            mock_rcon.return_value = {
                "ok": True,
                "command": "say PlayzAI Server Active",
                "output": "[Server] PlayzAI Server Active",
                "server": "127.0.0.1:25575",
            }
            res = agent.execute_action("minecraft_command", {"command": "say PlayzAI Server Active", "password": "secret_rcon"})
            self.assertTrue(res["ok"])
            self.assertEqual(res["command"], "say PlayzAI Server Active")
            self.assertIn("[Server]", res["output"])

    def test_unsupported_action(self):
        res = agent.execute_action("non_existent_dangerous_action", {})
        self.assertFalse(res["ok"])
        self.assertIn("Unsupported", res["error"])


if __name__ == "__main__":
    unittest.main()
