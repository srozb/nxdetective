from pydantic.main import BaseModel
from worker import (
    Worker,
    WorkerMeta
)
from domain import Domain
import csv
import trio
from loguru import logger as l
from typing import Dict


class ReporterMeta(BaseModel):
    outcome: Dict[str, int] = {}

    def colorful_outcome(self, oc: str) -> str:
        colors = {"OK": "green", "NXDOMAIN": "bold magenta",
                  "ValueError": "bold red", "Timeout": "bold red"}
        if oc in colors:
            return f"[{colors[oc]}]{oc}"
        return f"[dim]{oc}"


class Reporter(Worker):
    def __init__(self, data_source: trio.MemoryReceiveChannel, dest_file: str):
        self.__data_source = data_source
        self.__dest_file = dest_file
        self.__csv_dest = open(self.__dest_file, 'w')
        self.writer = csv.writer(self.__csv_dest)
        self.__meta__ = WorkerMeta(
            w_id=0, name="CSVWriter", entity=self.__dest_file)
        self.__stats__ = ReporterMeta()

    def item_filter(self, item: Domain) -> bool:
        """Filters domains to be reported"""
        return item.outcome == "NXDOMAIN"

    def submit_stats(self, item: Domain):
        """Update the domain resolve outcome statistics"""
        if item.outcome in self.__stats__.outcome:
            self.__stats__.outcome[item.outcome] += 1
        else:
            self.__stats__.outcome[item.outcome] = 1

    async def run(self):
        """Writes the CSV report file and updates the statistcs"""
        async with self.__data_source:
            self.change_status("running")
            async for item in self.__data_source:
                self.submit_stats(item)
                if self.item_filter(item):
                    self.writer.writerow([item.name, item.popularity])
                    self.__meta__.items_processed += 1
        self.change_status("done")
