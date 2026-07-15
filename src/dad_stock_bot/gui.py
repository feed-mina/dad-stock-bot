from __future__ import annotations

import calendar
import datetime
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, font, messagebox, ttk
from typing import Callable, Mapping, Sequence, TypeVar

from .config import Settings
from .providers import PublicDataStockPriceProvider
from .storage import SQLiteMarketStore
from .summary import build_summary_rows, write_korean_summary_csv


T = TypeVar("T")

COLUMNS = [
    "name",
    "symbol",
    "close",
    "change",
    "change_rate",
    "volume",
    "amount",
    "market_cap",
    "base_date",
]

HEADINGS = {
    "name": "종목명",
    "symbol": "종목코드",
    "close": "현재가",
    "change": "전일대비",
    "change_rate": "등락률",
    "volume": "거래량",
    "amount": "거래대금",
    "market_cap": "시가총액",
    "base_date": "기준일",
}

COLUMN_WIDTHS = {
    "name": 150,
    "symbol": 95,
    "close": 115,
    "change": 115,
    "change_rate": 100,
    "volume": 130,
    "amount": 170,
    "market_cap": 190,
    "base_date": 105,
}


class StockBotApp:
    def __init__(self, root: tk.Tk, settings: Settings) -> None:
        self.root = root
        self.settings = settings
        self.store = SQLiteMarketStore(settings.database_path)
        self.buttons: list[ttk.Button] = []

        self.root.title("아빠 주식 확인판")
        self.root.geometry("1280x760")
        self.root.minsize(1100, 620)

        self.symbols_var = tk.StringVar(value=",".join(settings.symbols))
        self.base_date_var = tk.StringVar()
        self.status_var = tk.StringVar(value=self._connection_text())
        self.summary_vars = {
            "date": tk.StringVar(value="기준일: -"),
            "count": tk.StringVar(value="관심종목: 0개"),
            "up_down": tk.StringVar(value="상승 0개 / 하락 0개"),
            "top_up": tk.StringVar(value="가장 많이 오른 종목: -"),
            "top_down": tk.StringVar(value="가장 많이 내린 종목: -"),
        }

        self._configure_style()
        self._build_layout()
        self.refresh_table()

    def _configure_style(self) -> None:
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(family="맑은 고딕", size=12)
        text_font = font.nametofont("TkTextFont")
        text_font.configure(family="맑은 고딕", size=12)

        style = ttk.Style(self.root)
        style.configure("TLabel", font=("맑은 고딕", 12))
        style.configure("TButton", font=("맑은 고딕", 12), padding=(12, 8))
        style.configure("Primary.TButton", font=("맑은 고딕", 13, "bold"), padding=(16, 9))
        style.configure("Treeview", font=("맑은 고딕", 13), rowheight=34)
        style.configure("Treeview.Heading", font=("맑은 고딕", 12, "bold"))
        style.configure("Summary.TLabel", font=("맑은 고딕", 13, "bold"), padding=(8, 6))
        style.configure("Status.TLabel", font=("맑은 고딕", 11), padding=(12, 8))

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        toolbar = ttk.Frame(self.root, padding=(14, 12, 14, 8))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(1, weight=1)

        ttk.Label(toolbar, text="관심종목").grid(row=0, column=0, padx=(0, 8), sticky="w")
        ttk.Entry(toolbar, textvariable=self.symbols_var, font=("맑은 고딕", 13)).grid(
            row=0,
            column=1,
            sticky="ew",
            ipady=4,
        )

        ttk.Label(toolbar, text="조회일").grid(row=0, column=2, padx=(14, 8), sticky="w")
        date_box = ttk.Frame(toolbar)
        date_box.grid(row=0, column=3)
        self.base_date_entry = ttk.Entry(
            date_box,
            textvariable=self.base_date_var,
            width=13,
            font=("맑은 고딕", 13),
            state="readonly",
        )
        self.base_date_entry.grid(row=0, column=0, ipady=4)
        self.base_date_entry.bind("<Button-1>", self.open_calendar)
        self._add_button(date_box, "📅", self.open_calendar).grid(row=0, column=1, padx=(4, 0))

        actions = ttk.Frame(toolbar)
        actions.grid(row=0, column=4, padx=(14, 0))

        self._add_button(actions, "시세 업데이트", self.sync_prices, style="Primary.TButton").grid(
            row=0,
            column=0,
            padx=4,
        )
        self._add_button(actions, "화면 새로고침", self.refresh_table).grid(row=0, column=1, padx=4)
        self._add_button(actions, "엑셀로 저장", self.export_summary_csv).grid(row=0, column=2, padx=4)
        self._add_button(actions, "중복 정리", self.dedupe_rows).grid(row=0, column=3, padx=4)

        summary = ttk.Frame(self.root, padding=(14, 0, 14, 10))
        summary.grid(row=1, column=0, sticky="ew")
        for index in range(5):
            summary.columnconfigure(index, weight=1)
        for index, key in enumerate(["date", "count", "up_down", "top_up", "top_down"]):
            ttk.Label(
                summary,
                textvariable=self.summary_vars[key],
                style="Summary.TLabel",
                relief="groove",
                anchor="center",
            ).grid(row=0, column=index, sticky="ew", padx=3)

        table_frame = ttk.Frame(self.root, padding=(14, 0, 14, 8))
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", height=15)
        for column in COLUMNS:
            self.tree.heading(column, text=HEADINGS[column])
            anchor = "e" if column not in {"name", "symbol", "base_date"} else "w"
            self.tree.column(
                column,
                width=COLUMN_WIDTHS[column],
                minwidth=COLUMN_WIDTHS[column],
                anchor=anchor,
                stretch=True,
            )
        self.tree.tag_configure("up", foreground="#c62828")
        self.tree.tag_configure("down", foreground="#1565c0")
        self.tree.tag_configure("flat", foreground="#555555")
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        status = ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            style="Status.TLabel",
        )
        status.grid(row=3, column=0, sticky="ew")

    def _add_button(
        self,
        parent: ttk.Frame,
        text: str,
        command: Callable[[], None],
        style: str = "TButton",
    ) -> ttk.Button:
        button = ttk.Button(parent, text=text, command=command, style=style)
        self.buttons.append(button)
        return button

    def sync_prices(self) -> None:
        symbols = _parse_symbols(self.symbols_var.get())
        base_date = _date_digits(self.base_date_var.get()) or None
        if not symbols:
            messagebox.showwarning("확인", "관심종목을 한 개 이상 입력해주세요.")
            return

        def task() -> int:
            provider = PublicDataStockPriceProvider(self.settings)
            for symbol in symbols:
                price = provider.get_daily_price(symbol, base_date)
                self.store.save_daily_price(price)
            return len(symbols)

        def done(count: int) -> None:
            self.status_var.set(f"{count}개 관심종목을 업데이트했습니다.")
            self.refresh_table()

        self._run_background(task, done)

    def dedupe_rows(self) -> None:
        def task() -> int:
            return self.store.dedupe_ticks()

        def done(deleted: int) -> None:
            self.status_var.set(f"중복 데이터 {deleted}건을 정리했습니다.")
            self.refresh_table()

        self._run_background(task, done)

    def refresh_table(self) -> None:
        all_rows = build_summary_rows(self.store.latest_ticks(limit=1000))
        target = _date_digits(self.base_date_var.get())
        if target:
            rows = [row for row in all_rows if _date_digits(row.get("base_date")) == target]
        else:
            rows = _latest_per_symbol(all_rows)

        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in rows:
            self.tree.insert("", "end", values=_row_values(row), tags=(_row_tag(row),))
        self._update_summary(rows)
        self.status_var.set(f"{len(rows)}개 관심종목을 표시하고 있습니다. | {self._connection_text()}")

    def export_summary_csv(self) -> None:
        rows = build_summary_rows(self.store.latest_ticks(limit=1000))
        default_name = f"아빠_주식_요약_{_latest_base_date(rows)}.csv"
        output = filedialog.asksaveasfilename(
            title="엑셀로 저장",
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not output:
            return
        write_korean_summary_csv(reversed(rows), output)
        self.status_var.set(f"엑셀 파일로 저장했습니다: {output}")

    def _run_background(self, task: Callable[[], T], on_success: Callable[[T], None]) -> None:
        self._set_busy(True)
        self.status_var.set("작업 중입니다. 잠시만 기다려주세요.")

        def worker() -> None:
            try:
                result = task()
            except Exception as exc:  # noqa: BLE001 - GUI should surface friendly errors.
                self.root.after(0, lambda exc=exc: self._show_error(exc))
            else:
                self.root.after(0, lambda result=result: self._finish_success(result, on_success))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_success(self, result: T, on_success: Callable[[T], None]) -> None:
        self._set_busy(False)
        on_success(result)

    def _show_error(self, exc: Exception) -> None:
        self._set_busy(False)
        message = _friendly_error_message(exc)
        self.status_var.set(message)
        messagebox.showerror("오류", message)

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for button in self.buttons:
            button.configure(state=state)

    def _connection_text(self) -> str:
        return "공공데이터 연결됨" if self.settings.public_data_service_key else "공공데이터 키가 없습니다"

    def _update_summary(self, rows: list[Mapping[str, object]]) -> None:
        date = _format_date(_latest_base_date(rows))
        up_rows = [row for row in rows if _numeric(row.get("change")) > 0]
        down_rows = [row for row in rows if _numeric(row.get("change")) < 0]
        top_up = max(up_rows, key=lambda row: _numeric(row.get("change_rate")), default=None)
        top_down = min(down_rows, key=lambda row: _numeric(row.get("change_rate")), default=None)

        self.summary_vars["date"].set(f"기준일: {date}")
        self.summary_vars["count"].set(f"관심종목: {len(rows)}개")
        self.summary_vars["up_down"].set(f"상승 {len(up_rows)}개 / 하락 {len(down_rows)}개")
        self.summary_vars["top_up"].set(f"가장 많이 오른 종목: {_summary_name(top_up)}")
        self.summary_vars["top_down"].set(f"가장 많이 내린 종목: {_summary_name(top_down)}")

    def open_calendar(self, event: object = None) -> None:
        _ = event
        _CalendarPopup(
            self.base_date_entry,
            initial=_parse_date(self.base_date_var.get()),
            on_pick=self._on_date_picked,
            on_clear=self._on_date_cleared,
        )

    def _on_date_picked(self, picked: datetime.date) -> None:
        self.base_date_var.set(picked.strftime("%Y-%m-%d"))
        self.sync_prices()

    def _on_date_cleared(self) -> None:
        self.base_date_var.set("")
        self.refresh_table()


def run_gui(settings: Settings | None = None) -> None:
    root = tk.Tk()
    _app = StockBotApp(root, settings or Settings.from_env_file())
    root.mainloop()


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv
    run_gui()
    return 0


def _parse_symbols(value: str) -> tuple[str, ...]:
    return tuple(symbol.strip() for symbol in value.split(",") if symbol.strip())


def _row_values(row: Mapping[str, object]) -> list[str]:
    return [
        str(row.get("name") or row.get("symbol") or ""),
        str(row.get("symbol") or ""),
        _format_value(row.get("close")),
        _format_change(row.get("change")),
        _format_change_rate(row.get("change_rate")),
        _format_value(row.get("volume")),
        _format_value(row.get("amount")),
        _format_value(row.get("market_cap")),
        _format_date(row.get("base_date")),
    ]


def _row_tag(row: Mapping[str, object]) -> str:
    change = _numeric(row.get("change"))
    if change > 0:
        return "up"
    if change < 0:
        return "down"
    return "flat"


def _format_change(value: object) -> str:
    number = _numeric(value)
    if number > 0:
        return f"▲ {_format_value(int(number))}"
    if number < 0:
        return f"▼ {_format_value(abs(int(number)))}"
    return "-"


def _format_change_rate(value: object) -> str:
    number = _numeric(value)
    if number > 0:
        return f"▲ {number:.2f}%"
    if number < 0:
        return f"▼ {abs(number):.2f}%"
    return "-"


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _numeric(value: object) -> float:
    try:
        if value in (None, ""):
            return 0
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0


def _latest_base_date(rows: list[Mapping[str, object]]) -> str:
    dates = [str(row.get("base_date") or "") for row in rows if row.get("base_date")]
    return max(dates) if dates else "날짜없음"


def _latest_per_symbol(rows: list[Mapping[str, object]]) -> list[Mapping[str, object]]:
    """Keep only the row with the most recent base_date per symbol."""
    best: dict[str, Mapping[str, object]] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "")
        if not symbol:
            continue
        current = best.get(symbol)
        if current is None or _date_digits(row.get("base_date")) > _date_digits(current.get("base_date")):
            best[symbol] = row
    return list(best.values())


def _date_digits(value: object) -> str:
    """Return only the digits of a date, e.g. '2026-07-14' -> '20260714'."""
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if len(digits) == 8 else ""


def _format_date(value: object) -> str:
    """Format a YYYYMMDD (or YYYY-MM-DD) date as 'YYYY-MM-DD'."""
    digits = _date_digits(value)
    if digits:
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    return str(value or "")


def _parse_date(value: object) -> datetime.date | None:
    digits = _date_digits(value)
    if not digits:
        return None
    try:
        return datetime.date(int(digits[0:4]), int(digits[4:6]), int(digits[6:8]))
    except ValueError:
        return None


def _summary_name(row: Mapping[str, object] | None) -> str:
    if not row:
        return "-"
    name = str(row.get("name") or row.get("symbol") or "-")
    rate = _numeric(row.get("change_rate"))
    return f"{name} {rate:.2f}%"


def _friendly_error_message(exc: Exception) -> str:
    text = str(exc)
    lowered = text.lower()
    if "public_data_service_key" in lowered or "missing required public data" in lowered:
        return ".env 파일의 PUBLIC_DATA_SERVICE_KEY를 확인해주세요."
    if "403" in text or "forbidden" in lowered:
        return "공공데이터 인증키가 맞지 않거나 활용신청이 승인되지 않았습니다."
    if "no stock price item" in lowered or "no data" in lowered:
        return "해당 날짜 데이터가 없습니다. 공휴일이거나 아직 데이터가 공개되지 않았을 수 있습니다."
    if "connection" in lowered or "timeout" in lowered or "network" in lowered:
        return "인터넷 연결을 확인한 뒤 다시 시도해주세요."
    return f"오류가 발생했습니다: {text}"


class _CalendarPopup:
    """A lightweight, dependency-free calendar for picking the query date.

    Future dates (after today) cannot be selected, so the user can only look at
    today or earlier trading days.
    """

    WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"]

    def __init__(
        self,
        anchor: tk.Widget,
        initial: datetime.date | None,
        on_pick: Callable[[datetime.date], None],
        on_clear: Callable[[], None] | None = None,
    ) -> None:
        self.on_pick = on_pick
        self.on_clear = on_clear
        self.today = datetime.date.today()
        self.max_date = self.today
        start = initial or self.today
        if start > self.max_date:
            start = self.max_date
        self.year = start.year
        self.month = start.month

        self.top = tk.Toplevel(anchor)
        self.top.title("조회일 선택")
        self.top.resizable(False, False)
        try:
            self.top.transient(anchor.winfo_toplevel())
            self.top.geometry(
                f"+{anchor.winfo_rootx()}"
                f"+{anchor.winfo_rooty() + anchor.winfo_height() + 4}"
            )
        except tk.TclError:
            pass

        self.header_var = tk.StringVar()
        self._build()
        self._render()
        try:
            self.top.grab_set()
        except tk.TclError:
            pass

    def _build(self) -> None:
        header = ttk.Frame(self.top, padding=(8, 8, 8, 4))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Button(header, text="◀", width=3, command=self._prev_month).grid(row=0, column=0)
        ttk.Label(
            header,
            textvariable=self.header_var,
            anchor="center",
            font=("맑은 고딕", 13, "bold"),
        ).grid(row=0, column=1, sticky="ew")
        self.next_button = ttk.Button(header, text="▶", width=3, command=self._next_month)
        self.next_button.grid(row=0, column=2)

        self.grid_frame = ttk.Frame(self.top, padding=(8, 0, 8, 4))
        self.grid_frame.grid(row=1, column=0)

        footer = ttk.Frame(self.top, padding=(8, 0, 8, 8))
        footer.grid(row=2, column=0, sticky="ew")
        ttk.Button(footer, text="오늘", command=lambda: self._pick(self.today)).grid(
            row=0, column=0, padx=2
        )
        if self.on_clear is not None:
            ttk.Button(footer, text="전체(최신)", command=self._clear).grid(row=0, column=1, padx=2)

    def _render(self) -> None:
        self.header_var.set(f"{self.year}년 {self.month}월")
        for child in self.grid_frame.winfo_children():
            child.destroy()

        for col, name in enumerate(self.WEEKDAYS):
            color = "#c62828" if col == 0 else ("#1565c0" if col == 6 else "#000000")
            ttk.Label(
                self.grid_frame, text=name, width=4, anchor="center", foreground=color
            ).grid(row=0, column=col, padx=1, pady=1)

        weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(self.year, self.month)
        for row_index, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                if day == 0:
                    continue
                date = datetime.date(self.year, self.month, day)
                button = ttk.Button(
                    self.grid_frame,
                    text=str(day),
                    width=4,
                    command=lambda picked=date: self._pick(picked),
                )
                button.grid(row=row_index, column=col, padx=1, pady=1)
                if date > self.max_date:
                    button.state(["disabled"])

        if (self.year, self.month) >= (self.max_date.year, self.max_date.month):
            self.next_button.state(["disabled"])
        else:
            self.next_button.state(["!disabled"])

    def _prev_month(self) -> None:
        if self.month == 1:
            self.year, self.month = self.year - 1, 12
        else:
            self.month -= 1
        self._render()

    def _next_month(self) -> None:
        if (self.year, self.month) >= (self.max_date.year, self.max_date.month):
            return
        if self.month == 12:
            self.year, self.month = self.year + 1, 1
        else:
            self.month += 1
        self._render()

    def _pick(self, date: datetime.date) -> None:
        if date > self.max_date:
            return
        self._close()
        self.on_pick(date)

    def _clear(self) -> None:
        self._close()
        if self.on_clear is not None:
            self.on_clear()

    def _close(self) -> None:
        try:
            self.top.grab_release()
        except tk.TclError:
            pass
        self.top.destroy()
