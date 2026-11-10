"""Detect the old Diablo II process or a user-selected game window."""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass

DEFAULT_GAME_PROCESSES = {"game.exe", "diablo ii.exe"}

TH32CS_SNAPPROCESS = 0x00000002
MAX_PATH = 260
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * MAX_PATH),
    ]


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    pid: int
    title: str
    exe: str

    @property
    def label(self) -> str:
        name = self.exe or f"PID {self.pid}"
        return f"{self.title}  ·  {name}  ·  {self.pid}"


def process_map() -> dict[int, str]:
    if os.name != "nt":
        return {}
    found: dict[int, str] = {}
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snapshot == wintypes.HANDLE(-1).value:
            return found
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        try:
            if kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
                while True:
                    found[int(entry.th32ProcessID)] = (entry.szExeFile or "").lower()
                    if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                        break
        finally:
            kernel32.CloseHandle(snapshot)
    except Exception:
        return found
    return found


def running_process_names() -> set[str]:
    return set(process_map().values())


def game_running(names: set[str] | None = None) -> bool:
    wanted = names or DEFAULT_GAME_PROCESSES
    return bool(running_process_names() & wanted)


def is_pid_running(pid: int) -> bool:
    if os.name != "nt" or pid <= 0:
        return False
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return False


def window_alive(hwnd: int) -> bool:
    if os.name != "nt" or not hwnd:
        return False
    try:
        return bool(ctypes.windll.user32.IsWindow(hwnd))
    except Exception:
        return False


def list_windows(exclude_pid: int | None = None) -> list[WindowInfo]:
    """Enumerate visible top-level windows with a non-empty title."""
    if os.name != "nt":
        return []
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    windows: list[WindowInfo] = []
    pmap = process_map()
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _lparam):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value.strip()
            if not title:
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            process_id = int(pid.value)
            if exclude_pid and process_id == exclude_pid:
                return True
            windows.append(
                WindowInfo(
                    hwnd=int(hwnd),
                    pid=process_id,
                    title=title,
                    exe=pmap.get(process_id, ""),
                )
            )
        except Exception:
            pass
        return True

    try:
        user32.EnumWindows(callback_type(callback), 0)
    except Exception:
        return windows
    windows.sort(
        key=lambda w: (
            0 if "diablo" in (w.title + " " + w.exe).lower() else 1,
            w.title.lower(),
        )
    )
    return windows
