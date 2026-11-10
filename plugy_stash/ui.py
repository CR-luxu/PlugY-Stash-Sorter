"""Tkinter desktop UI for the PlugY stash organizer."""
from __future__ import annotations

import ctypes
import os
import shutil
import sys
import time
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .gamewatch import game_running, game_window_running, is_pid_running, list_windows, window_alive
from .backups import prune_backups
from .gems import apply_gem_plan, plan_gem_upgrade
from .naming import name_pages
from .paths import find_stash_files, load_config, save_config
from .props import formatter
from .sorter import apply_plan, plan_sort
from .stash import Item, StashError, StashFile, parse_stash_bytes
from .zh import (
    CATEGORY_COLORS,
    CATEGORY_ORDER,
    GEM_GRADES,
    GEMS,
    POTION_SHORT,
    RUNE_NAMES,
    category,
    is_rune,
    rune_number,
)

BG = "#121212"
PANEL = "#1c1c1c"
PANEL_2 = "#242424"
BORDER = "#3a342b"
TEXT = "#e9e1d1"
MUTED = "#9b9386"
ACCENT = "#c9a45c"
ACCENT_DARK = "#8a6c34"
RED = "#c05a52"
GREEN = "#6f9e68"

SORT_MODES = [
    ("type", "按类型分页", "每个分类从新的一页开始，分类之间不会混在一起"),
    ("type_compact", "按类型连续填充", "分类顺序整理，但连续填满每一页，最省空间"),
    ("quality", "按品质分页", "暗金 / 套装 / 符文之语 / 稀有 / 魔法 …… 各占新页"),
    ("compact", "仅压缩空格", "保留物品原来的先后顺序，只把空隙压紧"),
]


def _font_family() -> str:
    families = set(tkfont.families())
    for name in ("Microsoft YaHei UI", "Microsoft YaHei", "微软雅黑", "SimHei", "Segoe UI"):
        if name in families:
            return name
    return "TkDefaultFont"


def _mix(color: str, factor: float) -> str:
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    if factor >= 1:
        r = int(r + (255 - r) * (factor - 1))
        g = int(g + (255 - g) * (factor - 1))
        b = int(b + (255 - b) * (factor - 1))
    else:
        r, g, b = int(r * factor), int(g * factor), int(b * factor)
    return f"#{min(255, r):02x}{min(255, g):02x}{min(255, b):02x}"


def _shorten(text: str, limit: int) -> str:
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[: max(1, limit - 1)] + "…"


def _round_rect(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float, radius: float, **kwargs):
    radius = max(1, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=12, **kwargs)


class StashApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        _set_window_icon(root)
        self.font_family = _font_family()
        self.config = load_config()
        self.stash: StashFile | None = None
        self.base_raw: bytes | None = None
        self.current_page = 0
        self.selected: Item | None = None
        self.dirty = False
        self.sort_mode = tk.StringVar(value=self.config.get("sort_mode", "type_compact"))
        self.reserve_pages = tk.StringVar(value=str(self.config.get("reserve_pages", 0)))
        self.auto_name_pages = tk.BooleanVar(
            value=bool(self.config.get("auto_name_pages", True))
        )
        self.auto_gems = tk.BooleanVar(value=bool(self.config.get("auto_gems", False)))
        self.auto_after_game = tk.BooleanVar(value=False)
        self._auto_waiting = False
        self._auto_game_seen = False
        self._selected_game_window = None
        self._auto_save_baseline: dict[Path, int] = {}
        self._auto_armed_at = 0.0
        self._auto_ignore_process_exit = False
        self.page_buttons: list[tk.Widget] = []

        self._setup_window()
        self._setup_style()
        self._build()
        self._bind_keys()
        self._set_empty_state()

    # ------------------------------------------------------------------ setup
    def _setup_window(self) -> None:
        self.root.title("PlugY 大箱子整理器")
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        # With per-monitor DPI awareness enabled, Tk reports physical pixels and
        # renders fonts at native resolution.  Keep a design-space 1220x760
        # layout and scale its pixel dimensions, which is crisper than letting
        # Windows bitmap-stretch a DPI-unaware window.
        try:
            dpi_scale = max(1.0, self.root.winfo_fpixels("1i") / 96.0)
        except tk.TclError:
            dpi_scale = 1.0
        self.scale = dpi_scale
        logical_w = screen_w / dpi_scale
        logical_h = screen_h / dpi_scale
        width = int(min(1220, max(1000, logical_w - 24)))
        height = int(min(760, max(650, logical_h - 40)))
        x = max(0, int((logical_w - width) / 2))
        y = max(0, int((logical_h - height) / 2 - 8))
        self.root.geometry(
            f"{int(width * dpi_scale)}x{int(height * dpi_scale)}+"
            f"{int(x * dpi_scale)}+{int(y * dpi_scale)}"
        )
        self.root.minsize(int(1080 * dpi_scale), int(680 * dpi_scale))
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        base_cell = 42 if height < 720 else (46 if height < 800 else 52)
        self.cell = int(base_cell * dpi_scale)
        self.offset = int(20 * dpi_scale)
        self.board_px = self.cell * 10
        self.canvas_px = self.board_px + self.offset * 2

    def _s(self, value: float) -> int:
        """Scale a design-space pixel value for the current display DPI."""
        return max(1, int(round(value * getattr(self, "scale", 1.0))))

    def _setup_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Vertical.TScrollbar",
            background=PANEL_2,
            troughcolor=BG,
            bordercolor=BG,
            arrowcolor=MUTED,
            darkcolor=PANEL_2,
            lightcolor=PANEL_2,
        )
        style.configure(
            "TRadiobutton",
            background=PANEL,
            foreground=TEXT,
            font=(self.font_family, 9),
            indicatorcolor=PANEL_2,
            focuscolor=PANEL,
        )
        style.map(
            "TRadiobutton",
            background=[("active", PANEL)],
            foreground=[("active", ACCENT)],
            indicatorcolor=[("selected", ACCENT)],
        )

    def _button(self, parent: tk.Widget, text: str, command, primary: bool = False, **kwargs) -> tk.Button:
        bg = ACCENT if primary else PANEL_2
        fg = "#15110b" if primary else TEXT
        active_bg = _mix(ACCENT, 1.15) if primary else "#303030"
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            relief="flat",
            bd=0,
            padx=13,
            pady=7,
            cursor="hand2",
            font=(self.font_family, 9, "bold" if primary else "normal"),
            **kwargs,
        )
        btn.bind("<Enter>", lambda _e: btn.configure(bg=active_bg))
        btn.bind("<Leave>", lambda _e: btn.configure(bg=bg))
        return btn

    def _card(self, parent: tk.Widget, **kwargs) -> tk.Frame:
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, **kwargs)
        return frame

    def _label(self, parent: tk.Widget, text: str, size: int = 9, color: str = TEXT, **kwargs) -> tk.Label:
        padx = kwargs.pop("padx", 0)
        pady = kwargs.pop("pady", 0)
        if isinstance(padx, tuple):
            padx = padx[0]
        if isinstance(pady, tuple):
            pady = pady[0]
        return tk.Label(
            parent,
            text=text,
            bg=kwargs.pop("bg", PANEL),
            fg=color,
            font=(self.font_family, size, kwargs.pop("weight", "normal")),
            anchor="w",
            justify="left",
            padx=padx,
            pady=pady,
            **kwargs,
        )

    def _build(self) -> None:
        header = tk.Frame(self.root, bg=BG, height=self._s(108))
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        title_box = tk.Frame(header, bg=BG)
        brand_size = self._s(48)
        brand = tk.Canvas(header, width=brand_size, height=brand_size, bg=BG, highlightthickness=0)
        brand.pack(side="left", padx=(self._s(20), self._s(10)), pady=(self._s(16), 0))
        brand.create_rectangle(1, 1, brand_size - 1, brand_size - 1, fill=PANEL, outline=ACCENT_DARK, width=2)
        for i in range(1, 3):
            brand.create_line(self._s(12 + i * 12), self._s(9), self._s(12 + i * 12), self._s(39), fill="#4b4234")
            brand.create_line(self._s(9), self._s(12 + i * 12), self._s(39), self._s(12 + i * 12), fill="#4b4234")
        for (x1, y1, x2, y2, color) in (
            (12, 12, 23, 23, "#c47a35"),
            (25, 12, 36, 20, "#8257b5"),
            (12, 25, 20, 36, "#2f8f8a"),
            (23, 23, 36, 36, "#466c9e"),
        ):
            brand.create_rectangle(self._s(x1), self._s(y1), self._s(x2), self._s(y2), fill=color, outline="")
        title_box.pack(side="left", padx=(0, 0), pady=(13, 0))
        tk.Label(
            title_box,
            text="PLUGY STASH",
            bg=BG,
            fg=ACCENT,
            font=(self.font_family, 8, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            title_box,
            text="大箱子整理器",
            bg=BG,
            fg=TEXT,
            font=(self.font_family, 18, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            title_box,
            text="暗黑破坏神 II · 老版 PlugY 共享仓库 / 个人仓库",
            bg=BG,
            fg=MUTED,
            font=(self.font_family, 8),
            anchor="w",
        ).pack(anchor="w", pady=(1, 0))

        actions = tk.Frame(header, bg=BG)
        actions.pack(side="right", padx=self._s(20), pady=self._s(18))
        self._button(actions, "打开", self.open_dialog).pack(side="left", padx=3)
        self._button(actions, "刷新", self.refresh).pack(side="left", padx=3)
        self._button(actions, "查找", self.auto_find).pack(side="left", padx=3)
        self._button(actions, "另存", self.save_as).pack(side="left", padx=3)
        self._button(actions, "保存", self.save, primary=True).pack(side="left", padx=(3, 8))
        self._button(actions, "撤销", self.undo).pack(side="left", padx=3)
        self._button(actions, "帮助", self.show_help).pack(side="left", padx=3)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 0))

        # left ---------------------------------------------------------------
        left = tk.Frame(body, bg=BG, width=self._s(238))
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        file_card = self._card(left)
        file_card.pack(fill="x", pady=(0, 9))
        self.file_name_label = self._label(
            file_card, "尚未打开存档", size=10, weight="bold", padx=12, pady=(10, 0)
        )
        self.file_name_label.pack(fill="x")
        self.file_meta_label = self._label(
            file_card,
            "请打开 .sss 或 .d2x 文件",
            size=8,
            color=MUTED,
            padx=12,
            pady=(2, 10),
            wraplength=self._s(210),
        )
        self.file_meta_label.pack(fill="x")

        page_card = self._card(left)
        page_card.pack(fill="both", expand=True)
        page_head = tk.Frame(page_card, bg=PANEL)
        page_head.pack(fill="x", padx=12, pady=(9, 4))
        self._label(page_head, "仓库页面", size=9, weight="bold", bg=PANEL).pack(side="left")
        self.page_count_label = self._label(page_head, "", size=8, color=MUTED, bg=PANEL)
        self.page_count_label.pack(side="right")

        list_wrap = tk.Frame(page_card, bg=PANEL)
        list_wrap.pack(fill="both", expand=True, padx=(10, 6), pady=(0, 10))
        scrollbar = ttk.Scrollbar(list_wrap, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        self.page_canvas = tk.Canvas(
            list_wrap,
            bg=PANEL,
            bd=0,
            highlightthickness=0,
            yscrollcommand=scrollbar.set,
            cursor="hand2",
        )
        self.page_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.page_canvas.yview)
        self.page_canvas.bind("<Button-1>", self.on_page_canvas_click)
        self.page_canvas.bind("<MouseWheel>", self.on_page_wheel)
        self.page_canvas.bind("<Configure>", lambda _e: self._draw_page_list())

        # center -------------------------------------------------------------
        center = tk.Frame(body, bg=BG)
        center.pack(side="left", fill="both", expand=True)

        nav = tk.Frame(center, bg=BG)
        nav.pack(fill="x", pady=(0, 7))
        self.page_title = tk.Label(
            nav,
            text="第 1 页",
            bg=BG,
            fg=TEXT,
            font=(self.font_family, 12, "bold"),
            anchor="w",
        )
        self.page_title.pack(side="left")
        self.page_summary = tk.Label(
            nav,
            text="",
            bg=BG,
            fg=MUTED,
            font=(self.font_family, 8),
            anchor="w",
        )
        self.page_summary.pack(side="left", padx=12)
        self._button(nav, "下一页", lambda: self.step_page(1)).pack(side="right", padx=3)
        self._button(nav, "上一页", lambda: self.step_page(-1)).pack(side="right", padx=3)

        board_frame = tk.Frame(center, bg=BG)
        board_frame.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(
            board_frame,
            width=self.canvas_px,
            height=self.canvas_px,
            bg="#0d0d0d",
            highlightthickness=1,
            highlightbackground="#443b2d",
            cursor="hand2",
        )
        self.canvas.pack(anchor="center", pady=(0, 5))
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)

        self.legend_frame = tk.Frame(center, bg=BG)
        self.legend_frame.pack(fill="x", pady=(2, 4))
        for name in CATEGORY_ORDER:
            chip = tk.Frame(self.legend_frame, bg=BG)
            chip.pack(side="left", padx=(0, 9))
            tk.Frame(chip, bg=CATEGORY_COLORS[name], width=8, height=8).pack(side="left", padx=(0, 3))
            tk.Label(
                chip,
                text=name,
                bg=BG,
                fg=MUTED,
                font=(self.font_family, 7),
            ).pack(side="left")

        # right --------------------------------------------------------------
        right = tk.Frame(body, bg=BG, width=self._s(292))
        right.pack(side="left", fill="y", padx=(10, 0))
        right.pack_propagate(False)

        sort_card = self._card(right)
        sort_card.pack(fill="x", pady=(0, 9))
        sort_head = tk.Frame(sort_card, bg=PANEL)
        sort_head.pack(fill="x", padx=12, pady=(9, 2))
        self._label(sort_head, "整理方式", size=9, weight="bold", bg=PANEL).pack(side="left")
        self._label(sort_head, "10 × 10", size=8, color=ACCENT, bg=PANEL).pack(side="right")
        mode_grid = tk.Frame(sort_card, bg=PANEL)
        mode_grid.pack(fill="x", padx=10, pady=(3, 0))
        for index, (value, title, _desc) in enumerate(SORT_MODES):
            rb = ttk.Radiobutton(
                mode_grid,
                text=title,
                variable=self.sort_mode,
                value=value,
                command=self._remember_sort_mode,
            )
            rb.grid(row=index // 2, column=index % 2, sticky="w", padx=(2, 8), pady=2)
        self._label(
            sort_card,
            "分页模式每类从新页开始；连续填充最省空间。",
            size=7,
            color=MUTED,
            bg=PANEL,
            wraplength=250,
            pady=(5, 0),
        ).pack(anchor="w", padx=12)
        check_row = tk.Frame(sort_card, bg=PANEL)
        check_row.pack(fill="x", padx=8, pady=(3, 0))
        tk.Checkbutton(
            check_row,
            text="自动命名页面",
            variable=self.auto_name_pages,
            command=self._remember_auto_name,
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL,
            activeforeground=ACCENT,
            selectcolor=PANEL_2,
            bd=0,
            highlightthickness=0,
            font=(self.font_family, 8),
            anchor="w",
        ).pack(side="left")
        tk.Checkbutton(
            check_row,
            text="自动合成宝石",
            variable=self.auto_gems,
            command=self._remember_auto_gems,
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL,
            activeforeground=ACCENT,
            selectcolor=PANEL_2,
            bd=0,
            highlightthickness=0,
            font=(self.font_family, 8),
            anchor="w",
        ).pack(side="left", padx=(10, 0))
        tk.Checkbutton(
            sort_card,
            text="每次退出/回主菜单后自动整理并保存",
            variable=self.auto_after_game,
            command=self._toggle_auto_after_game,
            bg=PANEL,
            fg=ACCENT,
            activebackground=PANEL,
            activeforeground=ACCENT,
            selectcolor=PANEL_2,
            bd=0,
            highlightthickness=0,
            font=(self.font_family, 8),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(3, 0))
        window_row = tk.Frame(sort_card, bg=PANEL)
        window_row.pack(fill="x", padx=10, pady=(1, 0))
        self.game_window_label = self._label(
            window_row,
            "窗口：自动检测游戏窗口",
            size=7,
            color=MUTED,
            bg=PANEL,
            wraplength=self._s(250),
        )
        self.game_window_label.pack(side="left", fill="x", expand=True)
        tk.Button(
            window_row,
            text="选择窗口",
            command=self.choose_game_window,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#303030",
            activeforeground=ACCENT,
            relief="flat",
            bd=0,
            padx=self._s(6),
            pady=self._s(2),
            cursor="hand2",
            font=(self.font_family, 7),
        ).pack(side="right", padx=(4, 0))
        reserve_row = tk.Frame(sort_card, bg=PANEL)
        reserve_row.pack(fill="x", padx=12, pady=(7, 0))
        self._label(reserve_row, "留空前", size=8, color=TEXT, bg=PANEL).pack(side="left")
        self.reserve_spin = tk.Spinbox(
            reserve_row,
            from_=0,
            to=99,
            width=4,
            textvariable=self.reserve_pages,
            bg=PANEL_2,
            fg=TEXT,
            buttonbackground=PANEL_2,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            font=(self.font_family, 8),
            justify="center",
        )
        self.reserve_spin.pack(side="left", padx=5)
        self._label(reserve_row, "页（从下一页开始整理）", size=8, color=MUTED, bg=PANEL).pack(
            side="left"
        )
        button_row = tk.Frame(sort_card, bg=PANEL)
        button_row.pack(fill="x", padx=12, pady=(7, 10))
        self._button(button_row, "开始整理", self.do_sort, primary=True).pack(
            side="left", fill="x", expand=True, padx=(0, 3)
        )
        self._button(button_row, "合成完美宝石", self.craft_gems).pack(
            side="left", fill="x", expand=True, padx=(3, 0)
        )

        detail_card = self._card(right)
        detail_card.pack(fill="both", expand=True, pady=(0, 9))
        detail_head = tk.Frame(detail_card, bg=PANEL)
        detail_head.pack(fill="x", padx=12, pady=(9, 2))
        self._label(detail_head, "物品详情", size=9, weight="bold", bg=PANEL).pack(side="left")
        self._label(detail_head, "双击看大图", size=7, color=MUTED, bg=PANEL).pack(side="right")
        detail_body = tk.Frame(detail_card, bg=PANEL)
        detail_body.pack(fill="both", expand=True, padx=(4, 4), pady=(0, 8))
        detail_scroll = ttk.Scrollbar(detail_body, orient="vertical")
        detail_scroll.pack(side="right", fill="y")
        self.detail_text = tk.Text(
            detail_body,
            bg=PANEL,
            fg=TEXT,
            bd=0,
            highlightthickness=0,
            font=(self.font_family, 8),
            wrap="word",
            padx=8,
            pady=4,
            height=12,
            cursor="arrow",
            yscrollcommand=detail_scroll.set,
        )
        self.detail_text.pack(side="left", fill="both", expand=True)
        detail_scroll.config(command=self.detail_text.yview)
        self.detail_text.tag_configure("title", font=(self.font_family, 10, "bold"), foreground=TEXT)
        self.detail_text.tag_configure("sub", foreground=MUTED, font=(self.font_family, 8))
        self.detail_text.tag_configure("accent", foreground=ACCENT)
        self.detail_text.tag_configure("section", foreground=ACCENT, font=(self.font_family, 8, "bold"))
        self.detail_text.tag_configure("muted", foreground=MUTED)
        self.detail_text.tag_configure("warn", foreground=RED)
        self.detail_text.config(state="disabled")

        tip_card = self._card(right)
        tip_card.pack(fill="x")
        self.warn_label = self._label(
            tip_card,
            "提示：整理前请先完全退出游戏",
            size=8,
            color=MUTED,
            padx=12,
            pady=9,
            wraplength=260,
            cursor="hand2",
        )
        self.warn_label.pack(fill="x")
        self.warn_label.bind("<Button-1>", lambda _e: self.show_warnings())

        # footer -------------------------------------------------------------
        footer = tk.Frame(self.root, bg="#0c0c0c", height=self._s(28))
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        self.status_label = tk.Label(
            footer,
            text="就绪",
            bg="#0c0c0c",
            fg=MUTED,
            font=(self.font_family, 8),
            anchor="w",
        )
        self.status_label.pack(side="left", padx=16)
        self.dirty_label = tk.Label(
            footer,
            text="",
            bg="#0c0c0c",
            fg=ACCENT,
            font=(self.font_family, 8, "bold"),
            anchor="e",
        )
        self.dirty_label.pack(side="right", padx=16)
        tk.Label(
            footer,
            text="F5 整理   ·   Ctrl+R 刷新   ·   Ctrl+S 保存   ·   Ctrl+Z 撤销   ·   双击物品查看详情",
            bg="#0c0c0c",
            fg="#5d564a",
            font=(self.font_family, 7),
            anchor="e",
        ).pack(side="right", padx=10)

    def _bind_keys(self) -> None:
        self.root.bind("<Control-o>", lambda _e: self.open_dialog())
        self.root.bind("<Control-r>", lambda _e: self.refresh())
        self.root.bind("<Control-s>", lambda _e: self.save())
        self.root.bind("<Control-Shift-S>", lambda _e: self.save_as())
        self.root.bind("<Control-z>", lambda _e: self.undo())
        self.root.bind("<F5>", lambda _e: self.do_sort())
        self.root.bind("<Prior>", lambda _e: self.step_page(-1))
        self.root.bind("<Next>", lambda _e: self.step_page(1))

    # --------------------------------------------------------------- helpers
    def _remember_sort_mode(self) -> None:
        self.config["sort_mode"] = self.sort_mode.get()
        save_config(self.config)

    def _remember_auto_name(self) -> None:
        self.config["auto_name_pages"] = bool(self.auto_name_pages.get())
        save_config(self.config)

    def _remember_auto_gems(self) -> None:
        self.config["auto_gems"] = bool(self.auto_gems.get())
        save_config(self.config)

    def _character_saves(self) -> list[Path]:
        if not self.stash or not self.stash.path:
            return []
        try:
            return [
                p
                for p in self.stash.path.parent.iterdir()
                if p.is_file() and p.suffix.lower() == ".d2s"
            ]
        except OSError:
            return []

    def _session_save_changed(self) -> bool:
        if not self._auto_save_baseline:
            return False
        for path, old_mtime in self._auto_save_baseline.items():
            try:
                if path.stat().st_mtime_ns != old_mtime:
                    return True
            except OSError:
                continue
        return False

    def _refresh_save_baseline(self) -> None:
        self._auto_save_baseline = {}
        for save in self._character_saves():
            try:
                self._auto_save_baseline[save] = save.stat().st_mtime_ns
            except OSError:
                continue

    def _auto_trigger(self, reason: str, menu: bool = False) -> None:
        self._auto_waiting = False
        self._auto_ignore_process_exit = bool(menu)
        self._set_status(f"{reason}，1 秒后自动整理并保存…")
        self.root.after(1000, self._auto_run)

    def _rearm_auto_watch(self) -> None:
        if not self.auto_after_game.get():
            return
        selected = self._selected_game_window
        if selected is not None and not window_alive(selected.hwnd):
            self._selected_game_window = None
            self._update_game_window_label()
        self._refresh_save_baseline()
        self._auto_armed_at = time.monotonic()
        self._auto_game_seen = False
        self._auto_waiting = True
        self._set_status("自动整理完成，已继续等待下一局回主菜单/退出…")
        self.root.after(2000, self._auto_poll)

    def _toggle_auto_after_game(self) -> None:
        if not self.auto_after_game.get():
            self._auto_waiting = False
            self._set_status("已取消本局游戏后自动整理")
            return
        if not self.stash or not self.stash.path:
            self.auto_after_game.set(False)
            messagebox.showinfo("尚未打开存档", "请先打开一个 PlugY 仓库文件。", parent=self.root)
            return
        if self.dirty:
            answer = messagebox.askyesnocancel(
                "当前有未保存整理",
                "自动整理会重新读取游戏退出后的存档，当前未保存的整理结果会丢失。\n\n"
                "要先保存当前结果吗？",
                parent=self.root,
            )
            if answer is None:
                self.auto_after_game.set(False)
                return
            if answer:
                self.save()
                if self.dirty:
                    self.auto_after_game.set(False)
                    return
        selected = self._selected_game_window
        if selected is not None:
            if not (window_alive(selected.hwnd) and is_pid_running(selected.pid)):
                self.auto_after_game.set(False)
                messagebox.showwarning(
                    "所选游戏窗口已关闭",
                    "之前选择的游戏窗口已经不在了，请重新点「选择窗口」。",
                    parent=self.root,
                )
                return
            running = True
        else:
            running = self._game_in_use()
        target = (
            f"所选窗口：{selected.title}（{selected.exe or selected.pid}）\n\n"
            if selected is not None
            else ""
        )
        saves = self._character_saves()
        save_hint = (
            "会监测角色存档 .d2s 的更新；回到主菜单只确认本局结束，真正写盘会等游戏完全退出。"
            if saves
            else "未找到角色存档 .d2s，只能等游戏进程退出时触发。"
        )
        msg = (
            "程序需要保持运行。\n\n"
            + target
            + save_hint
            + "\n\n"
            + (
                "检测到游戏正在运行：回到主菜单后先等待，完全退出游戏后等待 1 秒，"
                "重新读取存档，自动整理并保存，同时生成 .bak 备份（每个存档保留最近 5 个）。\n\n"
                if running
                else "当前没有检测到游戏进程：程序会等待下一次游戏启动，"
                "再重新读取最终存档，自动整理并保存，同时生成 .bak 备份（每个存档保留最近 5 个）。\n\n"
            )
            + "自动整理会使用当前选择的整理方式、留空页数、自动命名和自动合成宝石设置。\n"
            "启用后会持续监听：每一局回到主菜单/退出都会自动整理一次，直到手动取消勾选。\n\n"
            "确认启用吗？"
        )
        if not messagebox.askyesno("本局游戏后自动整理", msg, parent=self.root):
            self.auto_after_game.set(False)
            return
        self._refresh_save_baseline()
        self._auto_armed_at = time.monotonic()
        self._auto_ignore_process_exit = False
        self._auto_waiting = True
        self._auto_game_seen = running
        self._set_status(
            "已启用：回到主菜单或游戏退出后自动整理…"
            if running
            else "已启用：等待游戏启动，回主菜单/退出后自动整理…"
        )
        self.root.after(1000, self._auto_poll)

    def _auto_poll(self) -> None:
        if not self._auto_waiting:
            return
        selected = self._selected_game_window
        try:
            if selected is not None:
                running = window_alive(selected.hwnd) and is_pid_running(selected.pid)
            else:
                running = self._game_in_use()
        except Exception:
            running = False
        if self._session_save_changed():
            elapsed = time.monotonic() - self._auto_armed_at
            if elapsed < 6:
                # Entering the game can rewrite a character file; ignore that
                # first change and use the new mtime as the baseline.
                for path in list(self._auto_save_baseline):
                    try:
                        self._auto_save_baseline[path] = path.stat().st_mtime_ns
                    except OSError:
                        pass
            elif running or self._auto_game_seen:
                self._auto_trigger("检测到角色存档更新（已回到主菜单）", menu=True)
                return
        if running:
            if not self._auto_ignore_process_exit:
                self._auto_game_seen = True
            self.root.after(1200, self._auto_poll)
            return
        if self._auto_ignore_process_exit:
            # The process that produced the menu save has now exited.  Do not
            # treat that exit as another session; wait for a new process.
            self._auto_ignore_process_exit = False
            self._auto_game_seen = False
            self.root.after(1200, self._auto_poll)
            return
        if self._auto_game_seen:
            self._auto_trigger("游戏已退出")
            return
        self.root.after(1200, self._auto_poll)

    def choose_game_window(self) -> None:
        windows = list_windows(exclude_pid=os.getpid())
        if not windows:
            messagebox.showinfo("没有找到窗口", "当前没有可选择的可见窗口。", parent=self.root)
            return
        win = tk.Toplevel(self.root)
        win.title("选择游戏窗口")
        win.configure(bg=BG)
        win.geometry(f"{self._s(720)}x{self._s(500)}")
        win.transient(self.root)
        win.grab_set()
        tk.Label(
            win,
            text="请选择暗黑破坏神 II 的游戏窗口",
            bg=BG,
            fg=TEXT,
            font=(self.font_family, 12, "bold"),
            anchor="w",
        ).pack(fill="x", padx=self._s(16), pady=(self._s(14), self._s(2)))
        tk.Label(
            win,
            text="如果自动检测不到游戏窗口，可以在这里手动指定；选择后只监控这个窗口。",
            bg=BG,
            fg=MUTED,
            font=(self.font_family, 8),
            anchor="w",
        ).pack(fill="x", padx=self._s(16), pady=(0, self._s(8)))
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=self._s(14), pady=(0, self._s(8)))
        scroll = ttk.Scrollbar(body, orient="vertical")
        scroll.pack(side="right", fill="y")
        lb = tk.Listbox(
            body,
            bg=PANEL,
            fg=TEXT,
            selectbackground=ACCENT,
            selectforeground="#17120a",
            bd=0,
            highlightthickness=0,
            font=(self.font_family, 8),
            yscrollcommand=scroll.set,
        )
        lb.pack(side="left", fill="both", expand=True)
        scroll.config(command=lb.yview)
        for info in windows:
            lb.insert("end", info.label)
        lb.selection_set(0)

        def use_selected() -> None:
            sel = lb.curselection()
            if not sel:
                return
            self._selected_game_window = windows[int(sel[0])]
            if self._auto_waiting:
                self._auto_waiting = False
                self.auto_after_game.set(False)
                self._set_status("已切换游戏窗口，请重新勾选自动整理")
            self._update_game_window_label()
            win.destroy()

        def use_auto() -> None:
            self._selected_game_window = None
            if self._auto_waiting:
                self._auto_waiting = False
                self.auto_after_game.set(False)
            self._update_game_window_label()
            self._set_status("已恢复自动检测游戏窗口")
            win.destroy()

        lb.bind("<Double-Button-1>", lambda _e: use_selected())
        buttons = tk.Frame(win, bg=BG)
        buttons.pack(fill="x", padx=self._s(16), pady=(0, self._s(12)))
        self._button(buttons, "使用此窗口", use_selected, primary=True).pack(side="right")
        self._button(buttons, "自动检测", use_auto).pack(side="right", padx=self._s(6))
        self._button(buttons, "取消", win.destroy).pack(side="right", padx=self._s(6))

    def _update_game_window_label(self) -> None:
        selected = self._selected_game_window
        if selected is None:
            self.game_window_label.config(text="窗口：自动检测游戏窗口", fg=MUTED)
            return
        title = selected.title
        if len(title) > 22:
            title = title[:21] + "…"
        self.game_window_label.config(
            text=f"窗口：{title}（{selected.exe or selected.pid}）",
            fg=ACCENT,
        )

    def _auto_run(self) -> None:
        if not self.auto_after_game.get():
            self._set_status("已取消本局游戏后自动整理")
            return
        if not self.stash or not self.stash.path:
            return
        if self._game_in_use():
            self._refresh_save_baseline()
            self._auto_armed_at = time.monotonic()
            self._auto_game_seen = True
            self._auto_ignore_process_exit = False
            self._auto_waiting = True
            self._set_status("检测到游戏仍在运行；为避免损坏，等完全退出后自动整理…")
            self.root.after(1500, self._auto_poll)
            return
        path = self.stash.path
        try:
            raw = path.read_bytes()
            stash = parse_stash_bytes(raw, path)
        except (OSError, StashError, ValueError) as exc:
            self.auto_after_game.set(False)
            messagebox.showerror("自动整理失败", f"无法读取存档：\n{exc}", parent=self.root)
            self._set_status("自动整理失败：无法读取存档", error=True)
            return

        self.stash = stash
        self.base_raw = raw
        self._mark_dirty()
        mode = self.sort_mode.get()
        try:
            reserve = int(self.reserve_pages.get())
        except ValueError:
            reserve = 0
        reserve = max(0, min(reserve, max(0, len(stash.pages) - 1)))
        self.reserve_pages.set(str(reserve))
        gem_plan = None
        try:
            if self.auto_gems.get():
                gem_plan = plan_gem_upgrade(stash)
                if gem_plan.has_changes:
                    apply_gem_plan(stash, gem_plan)
            plan = plan_sort(stash, mode, reserve_pages=reserve)
            apply_plan(stash, plan)
            names = name_pages(stash, mode) if self.auto_name_pages.get() else []
        except (StashError, ValueError) as exc:
            self.auto_after_game.set(False)
            self._refresh_all()
            messagebox.showerror("自动整理失败", str(exc), parent=self.root)
            self._set_status("自动整理失败", error=True)
            return

        self.current_page = min(reserve, len(stash.pages) - 1)
        self.selected = None
        self._mark_dirty()
        self._refresh_all()
        if not self._write_to(path, silent=True):
            self._set_status("自动整理完成，但保存失败", error=True)
            self.auto_after_game.set(False)
            return
        gain = gem_plan.perfect_gained if gem_plan and gem_plan.has_changes else 0
        self._set_status(
            f"自动整理完成：{plan.item_count} 件物品"
            + (f"，完美宝石 +{gain}" if gain else "")
            + (f"，命名 {len(names)} 页" if names else "")
        )
        self._rearm_auto_watch()

    def _set_empty_state(self) -> None:
        self.page_title.config(text="尚未打开存档")
        self.page_summary.config(text="")
        self.canvas.delete("all")
        cx = self.canvas_px / 2
        self.canvas.create_text(
            cx,
            self.canvas_px / 2 - 34,
            text="打开 PlugY 大箱子存档",
            fill=TEXT,
            font=(self.font_family, 18, "bold"),
        )
        self.canvas.create_text(
            cx,
            self.canvas_px / 2,
            text="支持 _LOD_SharedStashSave.sss / 角色名.d2x",
            fill=MUTED,
            font=(self.font_family, 9),
        )
        self.canvas.create_text(
            cx,
            self.canvas_px / 2 + 36,
            text="建议先退出游戏，并在整理后保存备份",
            fill=ACCENT_DARK,
            font=(self.font_family, 8),
        )
        self._set_details(None)
        self.legend_frame.pack_forget()
        self.legend_frame.pack(fill="x", pady=(2, 4))

    def _name_color(self, item: Item) -> str:
        if item.unique_name:
            return "#e0bd63"
        if item.set_item_name:
            return "#7fb878"
        if item.is_runeword:
            return "#d98d4d"
        if item.quality in (6, 8, 9):
            return "#e2cf72"
        if item.quality == 4:
            return "#7fa7e8"
        return TEXT

    def _render_item_detail(self, widget: tk.Text, item: Item | None, big: bool = False) -> None:
        widget.config(state="normal")
        widget.delete("1.0", "end")
        if item is None:
            widget.insert("end", "点击网格中的物品查看详细信息。\n\n双击物品可以打开完整属性窗口。", "muted")
            widget.config(state="disabled")
            return

        f = formatter()
        size = 11 if big else 10
        body_size = 9 if big else 8
        widget.tag_configure(
            "name",
            font=(self.font_family, size, "bold"),
            foreground=self._name_color(item),
        )
        widget.tag_configure("sub", foreground=MUTED, font=(self.font_family, body_size))
        widget.tag_configure("accent", foreground=ACCENT, font=(self.font_family, body_size, "bold"))
        widget.tag_configure("section", foreground=ACCENT, font=(self.font_family, body_size, "bold"))
        widget.tag_configure("muted", foreground=MUTED, font=(self.font_family, body_size))
        widget.tag_configure("warn", foreground=RED, font=(self.font_family, body_size, "bold"))
        widget.tag_configure("body", font=(self.font_family, body_size), foreground=TEXT)

        name_cn = f.item_name(item)
        name_en = f.item_name(item, english=True)
        widget.insert("end", name_cn + "\n", "name")
        if name_en and name_en != name_cn:
            widget.insert("end", name_en + "\n", "sub")

        quality = f.quality_name(item)
        base_cn = f.base_name(item)
        head = " · ".join(part for part in (quality, base_cn, item.type_name) if part)
        widget.insert("end", head + "\n", "accent")
        widget.insert("end", "─" * (36 if big else 26) + "\n", "muted")

        lines = [
            ("物品等级", str(item.ilvl or "-")),
            ("尺寸", f"{item.width} × {item.height}"),
            ("位置", f"第 {self.current_page + 1} 页  ({item.x}, {item.y})"),
            ("代码", item.code),
        ]
        for key, value in lines:
            widget.insert("end", f"{key}　", "muted")
            widget.insert("end", value + "\n", "body")

        all_sections = f.sections(item)
        if all_sections:
            for section in all_sections:
                widget.insert("end", "\n" + section.title + "\n", "section")
                for line in section.lines:
                    widget.insert("end", "  · " + line + "\n", "body")
        else:
            widget.insert("end", "\n无附加属性\n", "muted")

        socketed = f.socketed_lines(item)
        if socketed:
            widget.insert("end", "\n镶嵌物\n", "section")
            for line in socketed:
                widget.insert("end", "  · " + line + "\n", "body")
        if item.warning:
            widget.insert("end", "\n⚠ " + item.warning + "\n", "warn")
        widget.config(state="disabled")

    def _set_details(self, item: Item | None) -> None:
        self._render_item_detail(self.detail_text, item, big=False)

    def show_item_window(self, item: Item) -> None:
        win = tk.Toplevel(self.root)
        win.title("物品详情")
        win.configure(bg=BG)
        win.geometry("620x680")
        win.transient(self.root)
        win.grab_set()
        header = tk.Frame(win, bg=BG)
        header.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(
            header,
            text="物品完整属性",
            bg=BG,
            fg=TEXT,
            font=(self.font_family, 13, "bold"),
            anchor="w",
        ).pack(side="left")
        self._button(header, "关闭", win.destroy).pack(side="right")
        body = tk.Frame(win, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        scroll = ttk.Scrollbar(body, orient="vertical")
        scroll.pack(side="right", fill="y")
        text = tk.Text(
            body,
            bg=PANEL,
            fg=TEXT,
            bd=0,
            highlightthickness=0,
            font=(self.font_family, 9),
            wrap="word",
            padx=16,
            pady=12,
            yscrollcommand=scroll.set,
        )
        text.pack(side="left", fill="both", expand=True)
        scroll.config(command=text.yview)
        self._render_item_detail(text, item, big=True)

    def _set_status(self, text: str, error: bool = False) -> None:
        self.status_label.config(text=text, fg=RED if error else MUTED)

    def _mark_dirty(self) -> None:
        self.dirty = True
        self.dirty_label.config(text="● 未保存")

    def _mark_clean(self) -> None:
        self.dirty = False
        self.dirty_label.config(text="")

    # ----------------------------------------------------------------- open
    def open_dialog(self) -> None:
        initial = self.config.get("last_dir") or ""
        if not initial or not Path(initial).is_dir():
            initial = str(Path.home())
        path = filedialog.askopenfilename(
            parent=self.root,
            title="打开 PlugY 大箱子存档",
            initialdir=initial,
            filetypes=[
                ("PlugY 仓库", "*.sss *.d2x"),
                ("共享仓库", "*.sss"),
                ("个人仓库", "*.d2x"),
                ("所有文件", "*.*"),
            ],
        )
        if path:
            self.load_path(Path(path))

    def load_path(self, path: Path, quiet: bool = False) -> None:
        try:
            raw = path.read_bytes()
            stash = parse_stash_bytes(raw, path)
        except (OSError, StashError, ValueError) as exc:
            messagebox.showerror("无法打开存档", str(exc), parent=self.root)
            self._set_status(str(exc), error=True)
            return
        self.stash = stash
        self.base_raw = raw
        self.current_page = 0
        self.selected = None
        self._mark_clean()
        self.config["last_dir"] = str(path.parent)
        save_config(self.config)
        self._refresh_all()
        self._set_status(f"已打开：{path.name}")
        if stash.warnings and not quiet:
            self.show_warnings()

    def refresh(self) -> None:
        if not self.stash or not self.stash.path:
            messagebox.showinfo("尚未打开存档", "请先打开一个 PlugY 仓库文件。", parent=self.root)
            return
        if self.dirty and not messagebox.askyesno(
            "刷新存档",
            "重新读取会丢弃当前未保存的整理结果。\n\n确定要刷新吗？",
            parent=self.root,
        ):
            return
        path = self.stash.path
        try:
            raw = path.read_bytes()
            stash = parse_stash_bytes(raw, path)
        except (OSError, StashError, ValueError) as exc:
            messagebox.showerror("刷新失败", f"无法重新读取存档：\n{exc}", parent=self.root)
            self._set_status("刷新失败", error=True)
            return
        self.stash = stash
        self.base_raw = raw
        self.current_page = min(self.current_page, max(0, len(stash.pages) - 1))
        self.selected = None
        self._mark_clean()
        self._set_details(None)
        self._refresh_all()
        self._set_status(f"已重新读取：{path.name} · {len(stash.pages)} 页")

    def auto_find(self) -> None:
        self._set_status("正在查找常见存档目录…")
        self.root.update_idletasks()
        files = find_stash_files()
        if not files:
            messagebox.showinfo(
                "没有找到存档",
                "没有在常见目录中找到 .sss / .d2x 文件。\n\n请点击「打开存档」手动选择，\n"
                "通常位于：\n文档\\Diablo II\\save\n或 用户\\Saved Games\\Diablo II",
                parent=self.root,
            )
            self._set_status("未找到存档")
            return
        if len(files) == 1:
            self.load_path(files[0])
            return
        self._choose_found_file(files)

    def _choose_found_file(self, files: list[Path]) -> None:
        win = tk.Toplevel(self.root)
        win.title("选择要打开的存档")
        win.configure(bg=BG)
        win.geometry("620x420")
        win.transient(self.root)
        win.grab_set()
        tk.Label(
            win,
            text="找到以下 PlugY 存档",
            bg=BG,
            fg=TEXT,
            font=(self.font_family, 12, "bold"),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(16, 6))
        tk.Label(
            win,
            text="共享仓库文件一般叫 _LOD_SharedStashSave.sss；个人仓库是角色名.d2x。",
            bg=BG,
            fg=MUTED,
            font=(self.font_family, 8),
            anchor="w",
        ).pack(fill="x", padx=18)
        frame = tk.Frame(win, bg=BG)
        frame.pack(fill="both", expand=True, padx=16, pady=10)
        sb = ttk.Scrollbar(frame, orient="vertical")
        sb.pack(side="right", fill="y")
        lb = tk.Listbox(
            frame,
            bg=PANEL,
            fg=TEXT,
            selectbackground=ACCENT,
            selectforeground="#17120a",
            bd=0,
            highlightthickness=0,
            font=(self.font_family, 9),
            yscrollcommand=sb.set,
        )
        lb.pack(side="left", fill="both", expand=True)
        sb.config(command=lb.yview)
        for f in files:
            lb.insert("end", f"{f.name}    —    {f.parent}")
        lb.selection_set(0)

        def choose() -> None:
            sel = lb.curselection()
            if not sel:
                return
            win.destroy()
            self.load_path(files[sel[0]])

        lb.bind("<Double-Button-1>", lambda _e: choose())
        btn = self._button(win, "打开选中的存档", choose, primary=True)
        btn.pack(side="right", padx=18, pady=(0, 14))
        self._button(win, "取消", win.destroy).pack(side="right", padx=6, pady=(0, 14))

    # --------------------------------------------------------------- refresh
    def _refresh_all(self) -> None:
        self._refresh_file_info()
        self._refresh_page_list()
        self._draw_page()

    def _refresh_file_info(self) -> None:
        if not self.stash:
            return
        s = self.stash
        self.file_name_label.config(text=s.path.name if s.path else "未命名仓库")
        items = sum(len(p.items) for p in s.pages)
        kind = "共享仓库" if s.is_shared else "个人仓库"
        extra = f"\n共享金币 {s.shared_gold:,}" if s.is_shared and s.shared_gold else ""
        self.file_meta_label.config(
            text=f"{kind} v{s.version} · {s.page_count} 页 · {items} 件物品{extra}"
        )
        self.page_count_label.config(text=f"{len(s.pages)} 页")
        if s.warnings:
            self.warn_label.config(
                text=f"⚠ {len(s.warnings)} 条检查警告，点击查看",
                fg=ACCENT,
            )
        else:
            self.warn_label.config(text="提示：整理前请先完全退出游戏", fg=MUTED)
        max_reserve = max(0, s.page_count - 1)
        self.reserve_spin.config(to=max_reserve)
        try:
            current_reserve = int(self.reserve_pages.get())
        except ValueError:
            current_reserve = 0
        if current_reserve > max_reserve:
            self.reserve_pages.set(str(max_reserve))
        elif current_reserve < 0:
            self.reserve_pages.set("0")
        self.root.title(f"PlugY 大箱子整理器 — {s.path.name}" if s.path else "PlugY 大箱子整理器")

    def _refresh_page_list(self) -> None:
        self._draw_page_list()
        self._scroll_page_into_view()

    def _draw_page_list(self) -> None:
        canvas = getattr(self, "page_canvas", None)
        if canvas is None:
            return
        canvas.delete("all")
        if not self.stash:
            return
        width = max(self._s(210), canvas.winfo_width())
        row_h = self._s(48)
        pages = self.stash.pages
        canvas.configure(scrollregion=(0, 0, width, max(1, len(pages) * row_h)))
        for index, page in enumerate(pages):
            top = index * row_h
            selected = index == self.current_page
            row_bg = "#2c2518" if selected else ("#1f1f1f" if index % 2 else PANEL)
            canvas.create_rectangle(0, top, width, top + row_h, fill=row_bg, outline="")
            if selected:
                canvas.create_rectangle(0, top, 3, top + row_h, fill=ACCENT, outline="")
            number_color = ACCENT if selected else "#756b5a"
            canvas.create_text(
                self._s(12),
                top + self._s(9),
                text=f"{index + 1:02d}",
                anchor="nw",
                fill=number_color,
                font=(self.font_family, 9, "bold"),
            )
            name = page.name.strip() if page.name else ("未命名" if page.items else "空页")
            if len(name) > 11:
                name = name[:10] + "…"
            canvas.create_text(
                self._s(44),
                top + self._s(8),
                text=name,
                anchor="nw",
                fill=TEXT if selected else "#d7cfbf",
                font=(self.font_family, 8, "bold" if selected else "normal"),
            )
            fill = round(page.fill_cells() / 100 * 100)
            canvas.create_text(
                width - self._s(10),
                top + self._s(9),
                text=f"{fill}%",
                anchor="ne",
                fill=ACCENT if selected else MUTED,
                font=(self.font_family, 7),
            )
            canvas.create_text(
                self._s(44),
                top + self._s(26),
                text=f"{len(page.items)} 件物品" if page.items else "",
                anchor="nw",
                fill=MUTED,
                font=(self.font_family, 7),
            )
            categories = []
            for item in page.items:
                cat = category(item)
                if cat not in categories:
                    categories.append(cat)
            dot_x = width - self._s(58)
            for cat in categories[:4]:
                canvas.create_oval(
                    dot_x,
                    top + self._s(28),
                    dot_x + self._s(6),
                    top + self._s(34),
                    fill=CATEGORY_COLORS.get(cat, "#555555"),
                    outline="",
                )
                dot_x += self._s(10)
            bar_left = self._s(44)
            bar_right = width - self._s(10)
            canvas.create_rectangle(
                bar_left, top + self._s(40), bar_right, top + self._s(42), fill="#303030", outline=""
            )
            if fill:
                canvas.create_rectangle(
                    bar_left,
                    top + self._s(40),
                    bar_left + (bar_right - bar_left) * min(fill, 100) / 100,
                    top + self._s(42),
                    fill=ACCENT if selected else ACCENT_DARK,
                    outline="",
                )

    def _scroll_page_into_view(self) -> None:
        if not self.stash or not hasattr(self, "page_canvas"):
            return
        canvas = self.page_canvas
        row_h = self._s(48)
        top = self.current_page * row_h
        total = max(1, len(self.stash.pages) * row_h)
        view_top = canvas.canvasy(0)
        view_bottom = view_top + max(1, canvas.winfo_height())
        if top < view_top or top + row_h > view_bottom:
            canvas.yview_moveto(max(0.0, (top - self._s(80)) / total))

    def on_page_canvas_click(self, event: tk.Event) -> None:
        if not self.stash:
            return
        index = int(self.page_canvas.canvasy(event.y) // self._s(48))
        if 0 <= index < len(self.stash.pages):
            self.select_page(index)

    def on_page_wheel(self, event: tk.Event) -> None:
        self.page_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def select_page(self, index: int) -> None:
        if not self.stash:
            return
        index = max(0, min(index, len(self.stash.pages) - 1))
        if index == self.current_page:
            return
        self.current_page = index
        self.selected = None
        self._set_details(None)
        self._refresh_page_list()
        self._draw_page()

    def on_page_select(self, _event=None) -> None:
        # Kept for compatibility with older bindings.
        self._refresh_page_list()

    def _draw_page(self) -> None:
        self.canvas.delete("all")
        if not self.stash:
            self._set_empty_state()
            return
        page = self.stash.pages[self.current_page]
        self.page_title.config(text=f"第 {page.index + 1} 页 / {len(self.stash.pages)}")
        counts: dict[str, int] = {}
        for item in page.items:
            cat = category(item)
            counts[cat] = counts.get(cat, 0) + 1
        summary = " · ".join(f"{k} {v}" for k, v in counts.items()) or "空页"
        self.page_summary.config(text=f"{len(page.items)} 件 · {summary}")

        left = self.offset
        top = self.offset
        cell = self.cell
        board = self.board_px
        _round_rect(
            self.canvas,
            left - 8,
            top - 8,
            left + board + 8,
            top + board + 8,
            10,
            fill="#0b0b0c",
            outline="#3b3327",
            width=1,
        )
        for yy in range(10):
            for xx in range(10):
                self.canvas.create_rectangle(
                    left + xx * cell,
                    top + yy * cell,
                    left + (xx + 1) * cell,
                    top + (yy + 1) * cell,
                    fill="#111111" if (xx + yy) % 2 == 0 else "#0e0e0e",
                    outline="",
                )
        for i in range(11):
            x = left + i * cell
            y = top + i * cell
            self.canvas.create_line(x, top, x, top + board, fill="#282828")
            self.canvas.create_line(left, y, left + board, y, fill="#282828")
        for i in range(10):
            self.canvas.create_text(
                left + i * cell + cell / 2,
                top - 13,
                text=str(i),
                fill="#62594b",
                font=(self.font_family, 6),
            )
            self.canvas.create_text(
                left - 13,
                top + i * cell + cell / 2,
                text=str(i),
                fill="#62594b",
                font=(self.font_family, 6),
            )

        for item in page.items:
            self._draw_item(item, left, top, cell)
        if not page.items:
            self.canvas.create_text(
                left + board / 2,
                top + board / 2 - 12,
                text="这一页是空的",
                fill="#4d473d",
                font=(self.font_family, 13, "bold"),
            )
            self.canvas.create_text(
                left + board / 2,
                top + board / 2 + 12,
                text="可以从其他页面拖入物品，或直接开始整理",
                fill="#39352f",
                font=(self.font_family, 7),
            )

    def _draw_item(self, item: Item, left: int, top: int, cell: int) -> None:
        x1 = left + item.x * cell
        y1 = top + item.y * cell
        x2 = x1 + item.width * cell
        y2 = y1 + item.height * cell
        cat = category(item)
        base = CATEGORY_COLORS.get(cat, "#555555")
        fill = _mix(base, 0.52)
        outline = _mix(base, 1.25)
        strip = outline
        if item.unique_name:
            outline = strip = "#d8b45a"
        elif item.set_item_name:
            outline = strip = "#6fa36b"
        elif item.is_runeword:
            outline = strip = "#d58a4a"
        elif item.quality in (6, 8, 9):
            outline = strip = "#d8c45c"
        elif item.quality == 4:
            outline = strip = "#6f8fd8"
        selected = item is self.selected

        # A small offset shadow makes the grid tiles feel layered.
        _round_rect(
            self.canvas,
            x1 + 3,
            y1 + 3,
            x2 + 1,
            y2 + 1,
            6,
            fill="#070707",
            outline="",
        )
        _round_rect(
            self.canvas,
            x1 + 1,
            y1 + 1,
            x2 - 1,
            y2 - 1,
            6,
            fill=fill,
            outline="#ffe08a" if selected else outline,
            width=3 if selected else 1,
            tags=("item",),
        )
        if strip and (item.unique_name or item.set_item_name or item.is_runeword or item.quality >= 4):
            self.canvas.create_line(
                x1 + 5,
                y1 + 3,
                x2 - 5,
                y1 + 3,
                fill=strip,
                width=2,
            )
        self.canvas.create_line(
            x1 + 5, y1 + 5, x2 - 5, y1 + 5, fill=_mix(base, 1.6), stipple="gray50"
        )
        label = self._item_label(item)
        font_size = 8 if item.area >= 2 else 7
        # A dark shadow keeps labels readable on bright gem and unique tiles.
        self.canvas.create_text(
            (x1 + x2) / 2 + 1,
            (y1 + y2) / 2 + 1,
            text=label,
            fill="#080808",
            width=max(20, (x2 - x1) - 10),
            justify="center",
            font=(self.font_family, font_size, "bold" if item.unique_name or item.quality >= 6 else "normal"),
        )
        self.canvas.create_text(
            (x1 + x2) / 2,
            (y1 + y2) / 2,
            text=label,
            fill="#fbf5e8",
            width=max(20, (x2 - x1) - 8),
            justify="center",
            font=(self.font_family, font_size, "bold" if item.unique_name or item.quality >= 6 else "normal"),
        )
        if item.quantity and item.quantity > 1:
            self.canvas.create_text(
                x2 - 6,
                y2 - 5,
                text=str(item.quantity),
                fill="#f6efdf",
                anchor="se",
                font=(self.font_family, 7, "bold"),
            )
        if item.warning:
            self.canvas.create_oval(
                x2 - 10, y1 + 7, x2 - 4, y1 + 13, fill=RED, outline=""
            )

    def _item_label(self, item: Item) -> str:
        f = formatter()
        code = item.code
        if is_rune(code):
            n = rune_number(code)
            return f"{RUNE_NAMES[n]}\n{n:02d}"
        if code in GEMS:
            gem, grade = GEMS[code]
            return f"{GEM_GRADES[grade][:2]}\n{gem[:2]}"
        if code == "cm1":
            return "小符"
        if code == "cm2":
            return "中符"
        if code == "cm3":
            return "火炬" if item.unique_name else "大符"
        if code == "tch":
            return "火炬"
        if code == "rin":
            return "戒指"
        if code == "amu":
            return "项链"
        if code in POTION_SHORT:
            return POTION_SHORT[code]
        if item.area >= 4:
            return _shorten(f.item_name(item), 16)
        name = f.short_name(item)
        name = _shorten(name, 5 if item.width == 1 else 9)
        q = ""
        if item.quality in (3, 4, 6, 8, 9) and not (
            item.unique_name or item.set_item_name or item.is_runeword
        ):
            q = f.quality_name(item)[:1]
        if q:
            return f"{q}\n{name}"
        return name

    # ---------------------------------------------------------------- pages
    def step_page(self, delta: int) -> None:
        if not self.stash:
            return
        new = max(0, min(len(self.stash.pages) - 1, self.current_page + delta))
        if new == self.current_page:
            return
        self.current_page = new
        self.selected = None
        self._set_details(None)
        self._refresh_page_list()
        self._draw_page()

    def _item_at_event(self, event: tk.Event) -> Item | None:
        if not self.stash:
            return None
        left, top, cell = self.offset, self.offset, self.cell
        x = int((event.x - left) // cell)
        y = int((event.y - top) // cell)
        if not (0 <= x < 10 and 0 <= y < 10):
            return None
        page = self.stash.pages[self.current_page]
        for item in page.items:
            if item.x <= x < item.x + item.width and item.y <= y < item.y + item.height:
                return item
        return None

    def on_canvas_click(self, event: tk.Event) -> None:
        found = self._item_at_event(event)
        self.selected = found
        self._set_details(found)
        self._draw_page()

    def on_canvas_double_click(self, event: tk.Event) -> None:
        found = self._item_at_event(event)
        if found is not None:
            self.selected = found
            self._set_details(found)
            self._draw_page()
            self.show_item_window(found)

    # ----------------------------------------------------------------- sort
    def craft_gems(self) -> None:
        if not self.stash:
            messagebox.showinfo("尚未打开存档", "请先打开一个 PlugY 仓库文件。", parent=self.root)
            return
        try:
            plan = plan_gem_upgrade(self.stash)
        except (StashError, ValueError) as exc:
            messagebox.showerror("无法合成宝石", str(exc), parent=self.root)
            return
        if not plan.has_changes:
            messagebox.showinfo(
                "没有可合成的宝石",
                "仓库里没有足够的同级同色宝石。\n\n"
                "原版公式：3 颗同级同色宝石 → 1 颗高一级宝石。",
                parent=self.root,
            )
            return
        details = "\n".join(plan.summary_lines())
        note = ""
        if plan.skipped:
            note = "\n\n已跳过：" + "、".join(plan.skipped[:8])
        msg = (
            "将按原版公式连续升级：3 颗同级同色宝石 → 1 颗高一级宝石。\n\n"
            f"{details}{note}\n\n"
            "合成会删除被消耗的低级宝石，并保留每组合成后的宝石位置。\n"
            "合成后物品之间可能留下空格，可再点「开始整理」。\n\n"
            "合成结果尚未保存，保存前可以点「撤销」恢复。"
        )
        if not messagebox.askyesno("确认合成完美宝石", msg, parent=self.root):
            return
        try:
            apply_gem_plan(self.stash, plan)
        except (StashError, ValueError) as exc:
            messagebox.showerror("合成失败", str(exc), parent=self.root)
            return
        self.selected = None
        self._mark_dirty()
        self._refresh_all()
        self._set_status(
            f"宝石合成完成：获得 {plan.perfect_gained} 颗完美宝石，尚未保存"
        )
        messagebox.showinfo(
            "合成完成",
            f"获得 {plan.perfect_gained} 颗完美宝石。\n\n"
            f"{details}\n\n"
            "结果尚未保存，请检查后点「保存」。",
            parent=self.root,
        )

    def do_sort(self) -> None:
        if not self.stash:
            messagebox.showinfo("尚未打开存档", "请先打开一个 PlugY 仓库文件。", parent=self.root)
            return
        if not any(page.items for page in self.stash.pages):
            messagebox.showinfo("仓库是空的", "当前仓库没有任何物品。", parent=self.root)
            return
        try:
            reserve = int(self.reserve_pages.get())
        except ValueError:
            reserve = 0
        max_reserve = max(0, len(self.stash.pages) - 1)
        if reserve < 0 or reserve > max_reserve:
            messagebox.showerror(
                "留空页数无效",
                f"留空页数必须在 0～{max_reserve} 之间。\n\n"
                "至少要保留一页用来放置物品。",
                parent=self.root,
            )
            return
        self.config["reserve_pages"] = reserve
        save_config(self.config)
        mode = self.sort_mode.get()
        auto_gems = bool(self.auto_gems.get())
        try:
            gem_plan = plan_gem_upgrade(self.stash) if auto_gems else None
        except (StashError, ValueError) as exc:
            messagebox.showerror("无法检查宝石", str(exc), parent=self.root)
            return
        try:
            plan = plan_sort(self.stash, mode, reserve_pages=reserve)
        except (StashError, ValueError) as exc:
            messagebox.showerror("无法整理", str(exc), parent=self.root)
            return
        mode_title = next((m[1] for m in SORT_MODES if m[0] == mode), mode)
        groups = "\n".join(f"  {k}：{v} 件" for k, v in plan.group_counts.items())
        added = f"\n需要新增 {plan.added_pages} 页。" if plan.added_pages else ""
        reserve_text = (
            f"留空：前 {reserve} 页\n"
            f"放置起始页：第 {reserve + 1} 页\n"
            if reserve
            else "放置起始页：第 1 页\n"
        )
        auto_text = "自动命名：开启（只命名空白页/旧的自动页名）\n" if self.auto_name_pages.get() else ""
        gem_text = ""
        if auto_gems:
            if gem_plan and gem_plan.has_changes:
                gem_text = (
                    f"自动合成宝石：获得 {gem_plan.perfect_gained} 颗完美宝石，"
                    f"消耗 {gem_plan.consumed} 颗低级宝石\n"
                    + "\n".join("  " + line for line in gem_plan.summary_lines())
                    + "\n"
                )
            else:
                gem_text = "自动合成宝石：没有可合成的宝石\n"
        final_count = plan.item_count - (gem_plan.consumed if gem_plan else 0)
        msg = (
            f"整理方式：{mode_title}\n\n"
            f"物品总数：{final_count}\n"
            f"将使用：{plan.used_pages} 页（原有 {len(self.stash.pages)} 页）{added}\n"
            f"{reserve_text}{auto_text}{gem_text}\n"
            f"分类统计：\n{groups}\n\n"
            "整理只会改变物品在格子中的位置和所在页面，不会修改物品属性"
            + ("；勾选的宝石合成会删除被消耗的低级宝石" if gem_plan and gem_plan.has_changes else "")
            + "。\n整理后需要点击「保存」才会写入文件；保存前可以点「撤销」恢复。"
        )
        if not messagebox.askyesno("确认整理仓库", msg, parent=self.root):
            return
        if gem_plan and gem_plan.has_changes:
            try:
                apply_gem_plan(self.stash, gem_plan)
                plan = plan_sort(self.stash, mode, reserve_pages=reserve)
            except (StashError, ValueError) as exc:
                self._mark_dirty()
                self._refresh_all()
                messagebox.showerror(
                    "宝石合成后整理失败",
                    f"宝石已经合成，但重新整理失败：\n{exc}\n\n可以点「撤销」恢复。",
                    parent=self.root,
                )
                return
        apply_plan(self.stash, plan)
        applied_names = name_pages(self.stash, mode) if self.auto_name_pages.get() else []
        self.current_page = min(reserve, len(self.stash.pages) - 1)
        self.selected = None
        self._mark_dirty()
        self._refresh_all()
        name_status = f"，自动命名 {len(applied_names)} 页" if applied_names else ""
        gem_status = (
            f"，合成 {gem_plan.perfect_gained} 颗完美宝石"
            if gem_plan and gem_plan.has_changes
            else ""
        )
        self._set_status(
            f"整理完成：{plan.item_count} 件物品，使用 {plan.used_pages} 页"
            + (f"，前 {reserve} 页留空" if reserve else "")
            + gem_status
            + name_status
            + "，尚未保存"
        )

    # ----------------------------------------------------------------- save
    def _backup(self, path: Path) -> Path | None:
        if not path.exists():
            return None
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.name}.{stamp}.bak")
        try:
            shutil.copy2(path, backup)
            prune_backups(path)
            return backup
        except OSError as exc:
            messagebox.showwarning(
                "备份失败",
                f"无法创建备份：\n{exc}\n\n仍要继续保存吗？",
                parent=self.root,
            )
            return None

    def save(self) -> None:
        if not self.stash:
            messagebox.showinfo("尚未打开存档", "请先打开一个 PlugY 仓库文件。", parent=self.root)
            return
        if not self.stash.path:
            self.save_as()
            return
        if not messagebox.askyesno(
            "保存到原文件",
            "请确认暗黑破坏神 II 已完全退出。\n\n"
            "游戏运行时保存会被游戏重新覆盖，甚至导致物品丢失。\n\n"
            "继续保存吗？",
            parent=self.root,
        ):
            return
        self._write_to(self.stash.path)

    def save_as(self) -> None:
        if not self.stash:
            messagebox.showinfo("尚未打开存档", "请先打开一个 PlugY 仓库文件。", parent=self.root)
            return
        initial = self.stash.path.parent if self.stash.path else Path(self.config.get("last_dir", Path.home()))
        default = self.stash.path.name if self.stash.path else "stash.sss"
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="另存为 PlugY 仓库",
            initialdir=str(initial),
            initialfile=default,
            defaultextension=".sss",
            filetypes=[("PlugY 共享仓库", "*.sss"), ("PlugY 个人仓库", "*.d2x"), ("所有文件", "*.*")],
        )
        if path:
            self._write_to(Path(path))

    def _game_in_use(self) -> bool:
        selected = self._selected_game_window
        if selected is not None and window_alive(selected.hwnd) and is_pid_running(selected.pid):
            return True
        try:
            return game_running() or game_window_running(exclude_pid=os.getpid())
        except Exception:
            return False

    def _write_to(self, path: Path, silent: bool = False) -> bool:
        assert self.stash is not None
        if self._game_in_use():
            if not silent:
                messagebox.showwarning(
                    "游戏仍在运行",
                    "检测到游戏仍在运行，已取消保存。\n\n"
                    "请完全退出游戏后再保存，避免游戏回写导致仓库损坏。",
                    parent=self.root,
                )
            self._set_status("检测到游戏仍在运行，已取消保存", error=True)
            return False
        try:
            data = self.stash.to_bytes()
            # Verify before touching the real save file.
            checked = parse_stash_bytes(data)
            layout_errors = [
                w for w in checked.warnings if "重叠" in w or "超出" in w
            ]
            if layout_errors:
                raise StashError("\n".join(layout_errors[:5]))
        except (StashError, ValueError) as exc:
            messagebox.showerror(
                "存档校验失败",
                f"整理后的数据无法重新解析或物品位置异常，已取消保存：\n{exc}",
                parent=self.root,
            )
            return False

        backup = self._backup(path) if path.exists() else None
        tmp = path.with_name(path.name + ".tmp")
        try:
            tmp.write_bytes(data)
            os.replace(tmp, path)
        except OSError as exc:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
            if not silent:
                messagebox.showerror("保存失败", f"无法写入文件：\n{exc}", parent=self.root)
            self._set_status("保存失败", error=True)
            return False

        self.stash.path = path
        self.stash.raw = data
        self.base_raw = data
        self._mark_clean()
        self.config["last_dir"] = str(path.parent)
        save_config(self.config)
        self._refresh_file_info()
        backup_text = f"\n\n原文件备份：\n{backup.name}" if backup else ""
        if not silent:
            messagebox.showinfo(
                "保存成功",
                f"已保存 {path.name}\n\n{len(data)} 字节{backup_text}",
                parent=self.root,
            )
        self._set_status(f"已保存：{path.name}")
        return True

    def undo(self) -> None:
        if not self.stash or self.base_raw is None:
            return
        if not self.dirty:
            self._set_status("没有未保存的更改")
            return
        if not messagebox.askyesno(
            "撤销整理",
            "放弃当前未保存的整理结果，恢复到上次打开/保存时的状态？",
            parent=self.root,
        ):
            return
        try:
            stash = parse_stash_bytes(self.base_raw, self.stash.path)
        except (StashError, ValueError) as exc:
            messagebox.showerror("撤销失败", str(exc), parent=self.root)
            return
        self.stash = stash
        self.current_page = min(self.current_page, len(stash.pages) - 1)
        self.selected = None
        self._mark_clean()
        self._refresh_all()
        self._set_status("已撤销未保存的整理")

    # ---------------------------------------------------------------- misc
    def show_warnings(self) -> None:
        if not self.stash or not self.stash.warnings:
            return
        text = "\n".join(f"· {w}" for w in self.stash.warnings[:60])
        if len(self.stash.warnings) > 60:
            text += f"\n… 还有 {len(self.stash.warnings) - 60} 条"
        messagebox.showwarning(
            "存档检查警告",
            "工具可以继续使用，但请留意以下内容：\n\n" + text,
            parent=self.root,
        )

    def show_help(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("使用说明")
        win.configure(bg=BG)
        win.geometry("660x560")
        win.transient(self.root)
        help_body = tk.Frame(win, bg=BG)
        help_body.pack(fill="both", expand=True, padx=12, pady=12)
        help_scroll = ttk.Scrollbar(help_body, orient="vertical")
        help_scroll.pack(side="right", fill="y")
        text = tk.Text(
            help_body,
            bg=PANEL,
            fg=TEXT,
            bd=0,
            padx=18,
            pady=16,
            wrap="word",
            font=(self.font_family, 9),
            spacing1=2,
            spacing3=6,
            yscrollcommand=help_scroll.set,
        )
        text.pack(side="left", fill="both", expand=True)
        help_scroll.config(command=text.yview)
        text.tag_configure("h", foreground=ACCENT, font=(self.font_family, 12, "bold"))
        text.tag_configure("m", foreground=MUTED)
        text.insert("end", "使用步骤\n", "h")
        text.insert(
            "end",
            "1. 完全退出暗黑破坏神 II（包括 PlugY 启动器）。\n"
            "2. 点击「打开存档」，选择 _LOD_SharedStashSave.sss。\n"
            "   游戏保存或外部修改后，可点「刷新」（Ctrl+R）重新读取磁盘文件。\n"
            "3. 选择整理方式，点击「开始整理」。\n"
            "4. 检查各页结果，确认无误后点击「保存」。\n"
            "5. 保存时会在原文件旁生成带时间戳的 .bak 备份，每个存档只保留最近 5 个。\n\n",
        )
        text.insert("end", "文件位置\n", "h")
        text.insert(
            "end",
            "共享仓库通常位于存档目录，文件名类似：\n"
            "  _LOD_SharedStashSave.sss\n"
            "  _LOD_HC_SharedStashSave.sss（专家模式）\n"
            "个人仓库是角色名.d2x（CSTM 格式）。\n\n"
            "界面中的「自动查找」会检查注册表和常见目录。\n\n",
            "m",
        )
        text.insert("end", "物品详情\n", "h")
        text.insert(
            "end",
            "单击格子里的物品，右侧会显示中文名/英文名、底材、品质、基础伤害或防御、"
            "需求、孔数、魔法属性、套装分段加成、符文之语属性和镶嵌物。\n"
            "双击物品可以打开更大的完整属性窗口。\n\n",
            "m",
        )
        text.insert("end", "合成完美宝石\n", "h")
        text.insert(
            "end",
            "点击「合成完美宝石」会按原版公式连续升级：3 颗同级同色宝石 → "
            "1 颗高一级宝石，直到每种宝石都不足 3 颗为止。\n"
            "勾选「自动合成宝石」后，点击「开始整理」会先合成宝石，再整理仓库。\n"
            "合成只改写宝石的物品代码，不会改变物品 id；被消耗的宝石会删除。\n\n",
            "m",
        )
        text.insert("end", "本局游戏退出后自动整理\n", "h")
        text.insert(
            "end",
            "勾选「每次退出/回主菜单后自动整理并保存」后，程序会检测游戏进程和游戏窗口（包括自定义登录器），"
            "并监测存档目录下 .d2s 的更新；回到主菜单只记录本局结束，不会在游戏运行时写盘。\n"
            "如果检测不到，可以点「选择窗口」手动指定游戏窗口。\n"
            "游戏完全退出后等待 1 秒重新读取存档，按当前设置整理并自动保存，同时生成 .bak 备份。\n"
            "启用后会持续监听，每一局都会触发；手动取消勾选才停止。\n\n",
            "m",
        )
        text.insert("end", "整理方式\n", "h")
        text.insert(
            "end",
            "右侧「留空前 N 页」可以保留仓库最前面的 N 页不放物品；"
            "原本在这几页的物品会被移到后面的页面。\n"
            "例如留空 3 页，整理会从第 4 页开始摆放。\n\n"
            "「整理后自动命名页面」会按内容给空白页命名，例如「符文 1」「武器/防具」；"
            "已有的自定义页名不会被覆盖。\n\n",
            "m",
        )
        for _, title, desc in SORT_MODES:
            text.insert("end", f"· {title}：", "accent" if False else "h")
            text.insert("end", desc + "\n")
        text.insert(
            "end",
            "\n按类型分页会把符文、宝石、珠宝、护身符、首饰、武器、防具、"
            "药剂、任务/钥匙和其他物品分别放在连续页面中。\n\n",
            "m",
        )
        text.insert("end", "安全说明\n", "h")
        text.insert(
            "end",
            "工具只修改物品的格子坐标和页面归属，物品的完整二进制数据"
            "（属性、孔、镶嵌物、个人化、任务标记等）原样保留。\n\n"
            "首次使用前仍建议手动复制一份存档。若整理后游戏提示"
            "「无法进入游戏 / Bad inventory data」，请用同目录下的 .bak 备份恢复。\n\n"
            "支持 PlugY 共享仓库 v1/v2 和个人仓库 CSTM v1；"
            "不修改共享金币、页名和文件末尾的自定义数据。\n",
            "m",
        )
        text.config(state="disabled")
        self._button(win, "知道了", win.destroy, primary=True).pack(pady=(0, 14))

    def on_close(self) -> None:
        if self.dirty:
            answer = messagebox.askyesnocancel(
                "有未保存的更改",
                "仓库有未保存的整理结果。\n\n要保存后退出吗？",
                parent=self.root,
            )
            if answer is None:
                return
            if answer:
                self.save()
                if self.dirty:
                    return
        self.root.destroy()


def _asset_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" / name


def _set_window_icon(root: tk.Tk) -> None:
    """Use the project icon for the title bar, taskbar and dialogs."""
    ico = _asset_path("icon.ico")
    png = _asset_path("icon.png")
    try:
        if ico.is_file():
            root.iconbitmap(default=str(ico))
    except tk.TclError:
        pass
    try:
        if png.is_file():
            image = tk.PhotoImage(file=str(png))
            root.iconphoto(True, image)
            root._app_icon = image  # keep a reference, otherwise Tk drops it
    except tk.TclError:
        pass


def _enable_high_dpi() -> None:
    """Make Tk render at native DPI instead of being bitmap-stretched by Windows."""
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PlugY.StashSorter")
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass


def run() -> None:
    _enable_high_dpi()
    root = tk.Tk()
    app = StashApp(root)
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1])
        if candidate.is_file():
            app.load_path(candidate, quiet=True)
    root.mainloop()
