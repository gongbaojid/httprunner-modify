""" Convert HAR (HTTP Archive) to YAML/JSON testcase for HttpRunner.

Usage:
    # convert to JSON format testcase
    $ hrun har2case demo.har

    # convert to YAML format testcase
    $ hrun har2case demo.har -2y

"""
import os
import sys

from loguru import logger

from httprunner.ext.har2all.core import HarParser


def init_har2all_parser(subparsers):
    """ HAR converter: parse command line options and run commands.
    """
    parser = subparsers.add_parser(
        "har2all", help="Convert HAR(HTTP Archive) to YAML/JSON testcases and api for HttpRunner.")
    parser.add_argument('har_source_file', nargs='?',
                        help="Specify HAR source file")
    parser.add_argument(
        '-pl', '--pre_length',
        dest='pre_length', default=0, type=int,
        help="Specify ignore level, the num of url word will be exclude")

    return parser


def main_har2all(args):
    har_source_file = args.har_source_file
    if not har_source_file or not har_source_file.endswith(".har"):
        logger.error("HAR file not specified.")
        sys.exit(1)

    if not os.path.isfile(har_source_file):
        logger.error(f"HAR file not exists: {har_source_file}")
        sys.exit(1)

    HarParser(
        har_source_file, args.pre_length
    ).gen_all()

    return 0
