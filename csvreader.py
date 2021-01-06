from worker import (
    Worker,
    WorkerMeta
)
import csv
import trio
from loguru import logger as l


class CSVReader(Worker):
    def __init__(self, src_file: str, data_dest: trio.MemorySendChannel):
        self.__src_file = src_file
        self.__data_dest = data_dest
        self.__csv_src = open(self.__src_file, 'r')
        
        self.__meta__ = WorkerMeta(
            w_id=0, name="CSVReader", entity=self.__src_file)

    def setup_worker(self):
        """Always omit the CSV header line"""
        sample = self.__csv_src.read(2048)
        self.__csv_dialect = csv.Sniffer().sniff(sample)
        l.debug("Detected dialect: ", self.__csv_dialect)
        self.__csv_src.seek(0)
        self.reader = csv.reader(self.__csv_src, self.__csv_dialect)
        self.reader.__next__()  # skip header

    async def run(self):
        """Read the whole file"""
        self.change_status("setting up")
        self.setup_worker()
        self.change_status("running")
        async with self.__data_dest:
            for item in self.reader:
                await self.__data_dest.send(item)
                self.__meta__.items_processed += 1
        self.change_status("done")
