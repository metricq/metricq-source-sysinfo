import logging

import click
import click_log  # type: ignore
from metricq.logging import get_logger

from .sysinfo_source import SysinfoSource

logger = get_logger()

click_log.basic_config(logger)
logger.setLevel("INFO")
logger.handlers[0].formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-8s] [%(name)-20s] %(message)s"
)


@click.command()
@click.argument("management-url", default="amqp://localhost/")
@click.option("--token", default="source-sysinfo")
@click_log.simple_verbosity_option(logger)  # type: ignore
def run(management_url: str, token: str) -> None:
    src = SysinfoSource(management_url=management_url, token=token)
    src.run()
