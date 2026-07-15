from __future__ import annotations

from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Sequence, TypeVar

from .config import Settings
from .providers import PublicDataStockPriceProvider
from .storage import SQLiteMarketStore
from .summary import build_summary_rows, write_summary_csv


T = TypeVar("T")

COLUMNS = [
    "symbol",
    "name",
    "base_date",
    "market",
    "close",
    "change",
    "change_rate",
    "volume",
    "amount",
    "market_cap",
]

HEADINGS = {
    "symbol": "Symbol",
    "name": "Name",
    "base_date": "Date",
    "market": "Market",
    "close": "Close",
    "change": "Change",
    "change_rate": "Change %",
    "volume": "Volume",
    "amount": "Amount",
    "market_cap": "Market Cap",
}


class StockBotApp:
    def __init__(self, root: tk.Tk, settings: Settings) -> None:
        self.root = root
        self.settings = settings
        self.store = SQLiteMarketStore(settings.database_path)
        self.buttons: list[ttk.Button] = []

        self.root.title("Dad Stock Bot")
        self.root.geometry("1180x640")
        self.root.minsize(980, 520)

        self.symbols_var = tk.StringVar(value=",".join(settings.symbols))
        self.base_date_var = tk.StringVar()
        self.status_var = tk.StringVar(value=self._status_text())

        self._build_layout()
        self.refresh_table()

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self.root, padding=(12, 10, 12, 8))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(1, weight=1)

        ttk.Label(toolbar, text="Symbols").grid(row=0, column=0, padx=(0, 6), sticky="w")
        ttk.Entry(toolbar, textvariable=self.symbols_var).grid(row=0, column=1, sticky="ew")

        ttk.Label(toolbar, text="Date").grid(row=0, column=2, padx=(12, 6), sticky="w")
        ttk.Entry(toolbar, textvariable=self.base_date_var, width=12).grid(row=0, column=3)

        actions = ttk.Frame(toolbar)
        actions.grid(row=0, column=4, padx=(12, 0))

        self._add_button(actions, "Sync", self.sync_prices).grid(row=0, column=0, padx=3)
        self._add_button(actions, "Refresh", self.refresh_table).grid(row=0, column=1, padx=3)
        self._add_button(actions, "Save CSV", self.export_summary_csv).grid(row=0, column=2, padx=3)
        self._add_button(actions, "Dedupe", self.dedupe_rows).grid(row=0, column=3, padx=3)

        table_frame = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", height=18)
        for column in COLUMNS:
            self.tree.heading(column, text=HEADINGS[column])
            anchor = "e" if column not in {"symbol", "name", "base_date", "market"} else "w"
            width = 95 if column not in {"name", "amount", "market_cap"} else 130
            self.tree.column(column, width=width, minwidth=70, anchor=anchor, stretch=True)
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        status = ttk.Label(self.root, textvariable=self.status_var, anchor="w", padding=(12, 6))
        status.grid(row=2, column=0, sticky="ew")

    def _add_button(
        self,
        parent: ttk.Frame,
        text: str,
        command: Callable[[], None],
    ) -> ttk.Button:
        button = ttk.Button(parent, text=text, command=command)
        self.buttons.append(button)
        return button

    def sync_prices(self) -> None:
        symbols = _parse_symbols(self.symbols_var.get())
        base_date = self.base_date_var.get().strip() or None
        if not symbols:
            messagebox.showwarning("Check", "Enter at least one symbol.")
            return

        def task() -> int:
            provider = PublicDataStockPriceProvider(self.settings)
            for symbol in symbols:
                price = provider.get_daily_price(symbol, base_date)
                self.store.save_daily_price(price)
            return len(symbols)

        def done(count: int) -> None:
            self.status_var.set(f"Synced {count} symbols")
            self.refresh_table()

        self._run_background(task, done)

    def dedupe_rows(self) -> None:
        def task() -> int:
            return self.store.dedupe_ticks()

        def done(deleted: int) -> None:
            self.status_var.set(f"Removed {deleted} duplicate rows")
            self.refresh_table()

        self._run_background(task, done)

    def refresh_table(self) -> None:
        rows = build_summary_rows(self.store.latest_ticks(limit=500))
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in rows:
            values = [_format_value(row.get(column)) for column in COLUMNS]
            self.tree.insert("", "end", values=values)
        self.status_var.set(f"Showing {len(rows)} rows | {self._status_text()}")

    def export_summary_csv(self) -> None:
        initial = Path("data") / "stock_summary.csv"
        output = filedialog.asksaveasfilename(
            title="Save CSV",
            initialfile=initial.name,
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not output:
            return
        rows = build_summary_rows(self.store.latest_ticks(limit=1000))
        write_summary_csv(reversed(rows), output)
        self.status_var.set(f"Saved CSV: {output}")

    def _run_background(self, task: Callable[[], T], on_success: Callable[[T], None]) -> None:
        self._set_busy(True)
        self.status_var.set("Working...")

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
        self.status_var.set("Error")
        messagebox.showerror("Error", str(exc))

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for button in self.buttons:
            button.configure(state=state)

    def _status_text(self) -> str:
        key_state = "key set" if self.settings.public_data_service_key else "no key"
        return f"DB: {self.settings.database_path} | public data {key_state}"


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


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)
