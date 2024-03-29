import asyncio
import re
import socket
from typing import TYPE_CHECKING, Any, Optional

import metricq
import psutil
from metricq import IntervalSource, Timedelta, Timestamp, logging, rpc_handler

from .version import version as client_version

logger = logging.get_logger("SysinfoSource")

# Ignore internal nics, especially from docker
_NIC_IGNORE_PATTERN = re.compile(r"^(lo|br|docker|veth)")

if TYPE_CHECKING:
    # Unfortunately there's no public type for it
    from psutil._common import sdiskio, snetio


class SysinfoSource(IntervalSource):
    prev_timestamp: Optional[metricq.Timestamp] = None
    prev_net_io: Optional[dict[str, "snetio"]] = None
    prev_disk_io: Optional[dict[str, "sdiskio"]] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, client_version=client_version, **kwargs)

    @rpc_handler("config")
    async def _on_config(self, **config: Any) -> None:
        logger.info("config: {}", config)
        rate = config["rate"]
        self.period = Timedelta.from_s(1 / rate)
        try:
            self.prefix = config["prefix"]
            if self.prefix != "" and not self.prefix.endswith("."):
                self.prefix = self.prefix + "."
        except KeyError:
            logger.info("No explicit prefix given, using hostname")
            self.prefix = socket.gethostname() + "."

        meta = dict()

        # Initialize CPU usage:
        psutil.cpu_percent(percpu=True)
        meta["cpu.usage"] = {
            "rate": rate,
            "description": "CPU usage (100% = 1 logical CPU busy)",
            "unit": "%",
        }

        # Initialize memory
        for mem_name in psutil.virtual_memory()._fields:
            meta[f"mem.{mem_name}"] = {
                "rate": rate,
                "description": "See https://psutil.readthedocs.io/en/latest/#psutil.virtual_memory",
                "unit": "%" if mem_name == "percent" else "B",
            }

        for swap_name in psutil.swap_memory()._fields:
            meta[f"swap.{swap_name}"] = {
                "rate": rate,
                "description": "See https://psutil.readthedocs.io/en/latest/#psutil.swap_memory",
                "unit": "%" if swap_name == "percent" else "B",
            }

        # Network
        self.prev_net_io = psutil.net_io_counters(pernic=True, nowrap=True)
        self.prev_timestamp = Timestamp.now()
        for nic_name in self.prev_net_io.keys():
            if _NIC_IGNORE_PATTERN.match(nic_name):
                continue
            for sr in "sent", "recv":
                meta[f"net.{nic_name}.{sr}.bytes"] = {
                    "rate": rate,
                    "description": f"Total data {sr} on nic {nic_name}",
                    "unit": "B/s",
                }
                meta[f"net.{nic_name}.{sr}.packets"] = {
                    "rate": rate,
                    "description": f"Number of packets {sr} on nic {nic_name}",
                    "unit": "Hz",
                }

        # Disk
        self.prev_disk_io = psutil.disk_io_counters(perdisk=True, nowrap=True)
        for disk_name in self.prev_disk_io.keys():
            for rw in "read", "written":
                meta[f"disk.{disk_name}.{rw}.count"] = {
                    "rate": rate,
                    "description": f"Number of {rw}s on partition {disk_name}",
                    "unit": "Hz",
                }
                meta[f"disk.{disk_name}.{rw}.bytes"] = {
                    "rate": rate,
                    "description": f"Total data {rw} on partition {disk_name}",
                    "unit": "B/s",
                }

        await self.declare_metrics(
            {self.prefix + key: value for key, value in meta.items()}
        )

    async def send(
        self, metric: str, timestamp: metricq.Timestamp, value: float
    ) -> None:
        await super().send(self.prefix + metric, timestamp, value)

    async def update(self) -> None:
        assert self.prev_timestamp is not None, "update() called before _on_config()"

        now = Timestamp.now()
        send_metrics = list()
        send_metrics.append(
            self.send("cpu.usage", now, sum(psutil.cpu_percent(percpu=True)))
        )

        for mem_name, mem_value in psutil.virtual_memory()._asdict().items():
            send_metrics.append(self.send(f"mem.{mem_name}", now, mem_value))

        for swap_name, swap_value in psutil.swap_memory()._asdict().items():
            send_metrics.append(self.send(f"swap.{swap_name}", now, swap_value))

        net_io = psutil.net_io_counters(pernic=True, nowrap=True)
        duration_s = (now - self.prev_timestamp).s
        assert self.prev_net_io is not None
        for nic_name, net_values in net_io.items():
            if _NIC_IGNORE_PATTERN.match(nic_name):
                continue
            prev_net_values = self.prev_net_io[nic_name]
            send_metrics.extend(
                [
                    self.send(
                        f"net.{nic_name}.sent.bytes",
                        now,
                        (net_values.bytes_sent - prev_net_values.bytes_sent)
                        / duration_s,
                    ),
                    self.send(
                        f"net.{nic_name}.sent.packets",
                        now,
                        (net_values.packets_sent - prev_net_values.packets_sent)
                        / duration_s,
                    ),
                    self.send(
                        f"net.{nic_name}.recv.bytes",
                        now,
                        (net_values.bytes_recv - prev_net_values.bytes_recv)
                        / duration_s,
                    ),
                    self.send(
                        f"net.{nic_name}.recv.packets",
                        now,
                        (net_values.packets_recv - prev_net_values.packets_recv)
                        / duration_s,
                    ),
                ]
            )

        disk_io = psutil.disk_io_counters(perdisk=True, nowrap=True)
        assert self.prev_disk_io is not None
        duration_s = (now - self.prev_timestamp).s
        for disk_name, disk_values in disk_io.items():
            prev_disk_values = self.prev_disk_io[disk_name]
            send_metrics.extend(
                [
                    self.send(
                        f"disk.{disk_name}.written.bytes",
                        now,
                        (disk_values.write_bytes - prev_disk_values.write_bytes)
                        / duration_s,
                    ),
                    self.send(
                        f"disk.{disk_name}.written.count",
                        now,
                        (disk_values.write_count - prev_disk_values.write_count)
                        / duration_s,
                    ),
                    self.send(
                        f"disk.{disk_name}.read.bytes",
                        now,
                        (disk_values.read_bytes - prev_disk_values.read_bytes)
                        / duration_s,
                    ),
                    self.send(
                        f"disk.{disk_name}.read.count",
                        now,
                        (disk_values.read_count - prev_disk_values.read_count)
                        / duration_s,
                    ),
                ]
            )

        self.prev_disk_io = disk_io
        self.prev_net_io = net_io
        self.prev_timestamp = now

        await asyncio.gather(*send_metrics)
