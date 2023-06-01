import logging

import click

import click_completion
import click_log
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
@click_log.simple_verbosity_option(logger)
def run(management_url, token):
    src = SysinfoSource(management_url=management_url, token=token)
    src.run()
