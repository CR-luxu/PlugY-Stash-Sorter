import os
import unittest

from plugy_stash.gamewatch import (
    game_running,
    is_pid_running,
    list_windows,
    running_process_names,
    window_alive,
)


class GameWatchTests(unittest.TestCase):
    def test_process_list_is_usable(self):
        names = running_process_names()
        self.assertIsInstance(names, set)
        if "python.exe" in names:
            self.assertTrue(game_running({"python.exe"}))
        self.assertFalse(game_running({"definitely-not-a-real-process-xyz.exe"}))
        self.assertTrue(is_pid_running(os.getpid()))
        self.assertFalse(window_alive(0))

    def test_window_list(self):
        self.assertIsInstance(list_windows(), list)


if __name__ == "__main__":
    unittest.main()
