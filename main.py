#!/usr/bin/env python

from reporter import Reporter
import dns.name
import fire
import sys

from typing import (
    List,
)

import trio
from loguru import logger as l

from domainresolver import DomainResolver
from csvreader import CSVReader
from painter import Painter

Domains = trio.open_memory_channel(65536)
Resolved = trio.open_memory_channel(65536)


def create_resolver_workers(nameservers: str = "", workers_num: int = 1) -> List[object]:
    """Create DomainResolver tasks depending on nameservers configured and desired number of workers"""
    Workers = []
    if nameservers:
        ns_to_use = nameservers.split(',')
    else:
        ns_to_use = dns.asyncresolver.get_default_resolver().nameservers
    for i in range(workers_num):
        for ns in ns_to_use:
            W = DomainResolver(Domains[1], Resolved[0])
            W.nameserver = ns
            W.__meta__.w_id = i
            Workers.append(W)
    return Workers


def create_csvreader_workers(csv_file: str) -> List[object]:
    """Create CSV Reader task"""
    CSV_Worker = CSVReader(csv_file, Domains[0])
    return [CSV_Worker]


def create_reporter_workers(report_file: str) -> List[object]:
    """Create Reporter task (statistics & csv report)"""
    File_Reporter = Reporter(Resolved[1], report_file)
    return [File_Reporter]


def create_painter(workers: List[object]) -> list:
    """Create Painter task (dashboards)"""
    p = Painter(workers=workers)
    return [p]


async def process(domain_file: str, nameservers: str = "",
                  workers_num: int = 1, debug=False):
    """Process given CSV file, resolve domains and create a report.csv"""
    Workers = []  # TODO: Workers should be global so painter task has always accurate data
    Workers += create_resolver_workers(nameservers, workers_num)
    Workers += create_csvreader_workers(domain_file)
    Workers += create_reporter_workers("report.csv")
    if not debug:
        l.remove()
        l.add(sys.stderr, level="INFO")
        Workers += create_painter(Workers)
    

    async with trio.open_nursery() as nursery:
        for Worker in Workers:
            l.debug(f"Starting worker: {Worker}")
            nursery.start_soon(Worker.run)


def main(domain_file: str, nameservers: str = "",
         workers_num: int = 1, debug: bool = False):
    """Run asynchronous tasks"""
    trio.run(process, domain_file, nameservers, workers_num, debug)


if __name__ == "__main__":
    fire.Fire({
        'process': main,
    })
