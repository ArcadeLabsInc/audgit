import argparse
import logging

from audgit.code_review import code_review
from audgit.monitor import Monitor


def parse_args():
    parser = argparse.ArgumentParser(description="Audgit monitor")

    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--one", action="store_true", help="Pick one job and process it"
    )
    parser.add_argument("--list", action="store_true", help="Show job list")
    parser.add_argument("--start", action="store_true", help="Start processing jobs")
    parser.add_argument("--review", help="Review a single github issue")

    return parser.parse_args()


log = logging.getLogger()


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
    )


def main():
    args = parse_args()
    if args.debug:
        log.setLevel(logging.DEBUG)

    mon = Monitor(debug=args.debug)

    mon.add_handler("code-review", code_review)

    if args.start:
        mon.start()
    if args.list:
        mon.list()
    if args.one:
        mon.one()
    if args.review:
        mon.cli_review(args.review)


if __name__ == "__main__":
    main()
