from worker import Worker
import trio
from domain import Domain

from dns import asyncresolver
from loguru import logger as l
from typing import (
    List,
    Union,
    Optional
)


class DomainResolver(Worker):
    @property
    def nameserver(self) -> Optional[str]:
        return self.__nameserver

    @nameserver.setter
    def nameserver(self, value: str):
        self.__nameserver = value
        self.__meta__.entity = self.__nameserver

    def __init__(self, data_source: trio.MemoryReceiveChannel, data_dest: trio.MemorySendChannel):
        self.__nameserver = None
        super().__init__(data_source, data_dest)
        self.__meta__.name = "DomainResolver"
        self.__meta__.item_unit = "domains"

    def setup_worker(self):
        """Setup the Async Resolver instance"""
        self.__Resolver = asyncresolver.Resolver()
        self.__Resolver.nameservers = [self.__nameserver]

    async def process(self, item: List[Union[str, int]]) -> Union[Domain, None]:
        """If a domain name is valid, try to resolve it"""
        try:
            domain = Domain(name=item[0], answer=[],
                            outcome="PENDING", popularity=item[1])
            self.__meta__.current_item = item[0]
        except ValueError:
            l.debug(f"Discarding: {item[0]}")
            return
        except IndexError:
            l.debug(f"Skipping line: {item}")
            return
        l.debug(f"[{self.__nameserver}] Resolving: {domain.name}")
        try:
            resolved = await self.__Resolver.resolve(domain.name, "MX")
            domain.answer = resolved.response.answer
            domain.outcome = "OK"
        except Exception as e:
            domain.outcome = e.__class__.__name__
        return domain
