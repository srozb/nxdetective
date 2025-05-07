from pydantic import BaseModel
from worker import Worker
from typing import (
    List,
    Union
)

import trio

from loguru import logger as l

from rich.console import (
    ConsoleRenderable,
    RichCast
)

from rich.live import Live
from rich.table import Table
from rich.progress import (
    Progress,
    TaskID,
    TextColumn,
    BarColumn,
    TimeRemainingColumn
)
from rich.panel import Panel
from rich.columns import Columns


class Painter(BaseModel):
    workers: List[Worker]

    class Config:
        arbitrary_types_allowed = True

    def tasks_running(self) -> bool:
        """Returns true as long as at least one task is not finished"""
        for w in self.workers:
            if w.is_running():
                return True
        return False

    async def generate_tasks_table(self) -> Table:
        """Returns the tasks table"""
        table = Table(width=110, padding=(0, 2),
                      show_edge=False, border_style="dim")
        table.add_column("Task Type")
        table.add_column("Task ID")
        table.add_column("Entity", justify="center")
        table.add_column("Status", justify="center")
        table.add_column("Current domain", style="bold cyan", min_width=30)
        table.add_column("Speed (dom./s)", justify="right")
        for w in self.workers:
            m = w.__meta__
            table.add_row(m.colorful_type(), f"{m.w_id}", m.entity, m.colorful_status(
            ), m.current_item, f"{m.items_per_sec()}")
        return table

    def generate_progress(self, progress: Progress, task: TaskID) -> Union[ConsoleRenderable, RichCast, str]:
        """Returns the updated progress bar"""
        total = 0
        completed = 0
        for w in self.workers:
            if w.__meta__.name == "CSVReader":
                total += w.__meta__.items_processed
            elif w.__meta__.name == "DomainResolver":
                completed += w.__meta__.items_processed
        progress.update(task, total=total, completed=completed)
        return progress.get_renderable()

    def generate_statistics(self) -> Table:
        """Returns the table pupulated with resolve outcome statistics"""

        def get_writer_worker(self) -> Worker:
            for w in self.workers:
                if w.__meta__.name == "CSVWriter":
                    return w

        table = Table(width=60, padding=(0, 2),
                      show_edge=False, border_style="dim")
        table.add_column("Outcome")
        table.add_column("Count")
        w = get_writer_worker(self)
        for k in w.__stats__.outcome:
            table.add_row(w.__stats__.colorful_outcome(k),
                          str(w.__stats__.outcome[k]))
        return table

    def create_progress_bar(self) -> Progress:
        return Progress(
            TextColumn("[bold blue]Resolving...", justify="center"),
            "•",
            BarColumn(bar_width=None),
            "• [yellow]done: "
            # "[progress.nx_len]{task.fields[nx_len]}",
            # "•",
            "[progress.percentage]{task.percentage:>3.1f}%",
            # "• ETA:",
            # TimeRemainingColumn(), transient=True
        )

    async def run(self):
        """Create and refresh the dashboard every n seconds"""
        while not self.tasks_running():
            await trio.sleep(0.5)

        progress = self.create_progress_bar()
        task = progress.add_task("resolving")

        with Live(progress, transient=True, refresh_per_second=1) as live:
            while self.tasks_running():
                table = await self.generate_tasks_table()
                self.generate_progress(progress, task)
                statistics = self.generate_statistics()

                panel_group = Columns(
                    [
                        Panel(table, title="Tasks"),
                        Panel(progress.get_renderable(), title="Progress"),
                        Panel(statistics, title="Query statistics")
                    ]
                )

                live.update(panel_group)
                await trio.sleep(1)
