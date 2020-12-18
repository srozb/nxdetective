import trio
from loguru import logger as l
import datetime
from typing import (
    List,
    Union
)

from pydantic import BaseModel


class WorkerMeta(BaseModel):
    w_id: int = 0
    name: str = "AbstractWorker"
    entity: str = ""
    status: str = "initializing"
    start_time: datetime.datetime = datetime.datetime.now()
    stop_time: datetime.datetime = datetime.datetime.now()
    items_processed: int = 0
    item_unit: str = "items"
    current_item: str = ""

    def as_str(self) -> str:
        """Pretty print task identifier"""
        if self.entity != "":
            return "<{name}[{w_id}] {entity}>".format(**dict(self))
        else:
            return "<{name}[{w_id}]>".format(**dict(self))

    def as_str_color(self) -> str:
        """Even prettier print task identifier"""
        if self.name == "DomainResolver":
            return f"[bold magenta]{self.as_str()}"
        return self.as_str()

    def colorful_type(self) -> str:
        """Determine color based on task type"""
        if self.name == "DomainResolver":
            return f"[bold magenta]{self.name}"
        else:
            return f"[yellow]{self.name}"

    def reset_clock(self):
        self.start_time = datetime.datetime.now()

    def stop_clock(self):
        self.stop_time = datetime.datetime.now()

    def items_per_sec(self) -> int:
        if self.status != "running":
            return 0
        try:
            return round(self.items_processed / (datetime.datetime.now() - self.start_time).seconds)
        except ZeroDivisionError:
            return 0

    def colorful_status(self) -> str:
        color = {'running': 'bold green', 'setting up': 'cyan', 'done': 'dim'}
        try:
            return f"[{color[self.status]}]{self.status}"
        except KeyError:
            return self.status


class Worker:
    def __init__(self, data_source: trio.MemoryReceiveChannel, data_dest: trio.MemorySendChannel):
        self.__data_source = data_source.clone()
        self.__data_dest = data_dest.clone()
        self.__master_data_source = data_source
        self.__master_data_dest = data_dest
        self.__meta__ = WorkerMeta()

    def __str__(self) -> str:
        return self.__meta__.as_str()

    def __repr__(self) -> str:
        return self.__str__()

    async def __store_result(self, item):
        await self.__data_dest.send(item)

    def change_status(self, new_status: str):
        """Updates task's metadata with the new status"""
        l.debug(f"{self} changing state to: {new_status}")
        if new_status == "running":
            self.__meta__.reset_clock()
        elif new_status == "terminating":
            self.__meta__.stop_clock()
        self.__meta__.status = new_status

    def is_running(self):
        return self.__meta__.status == "running"

    def setup_worker(self):
        pass

    async def cleanup(self):
        l.debug(
            f"{self} work is done, {self.__meta__.items_processed} items processed. Time to clean up.")
        if self.__master_data_dest.statistics().tasks_waiting_send == 0:
            await trio.sleep(1)
            await self.__master_data_dest.aclose()
            await self.__master_data_source.aclose()

    async def process(self, item: List[Union[str, int]]):
        return item

    async def run_loop(self):
        async with self.__data_source, self.__data_dest:
            async for item in self.__data_source:
                domain = await self.process(item)
                if not domain:
                    continue
                await self.__store_result(domain)
                self.__meta__.items_processed += 1

    async def run(self):
        self.change_status("setting up")
        self.setup_worker()
        self.change_status("running")
        await self.run_loop()
        self.change_status("done")
        await self.cleanup()
