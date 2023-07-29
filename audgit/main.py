import argparse
import logging

from audgit.monitor import Monitor

def parse_args():
    parser = argparse.ArgumentParser(description='Audgit monitor')

    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--one', action='store_true', help='Pick one job and process it')
    parser.add_argument('--list', action='store_true', help='Show job list')
    parser.add_argument('--start', action='store_true', help='Start processing jobs')

    return parser.parse_args()


log = logging.getLogger()

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
    )


def main():
    args = parse_args()
    if args.debug:
        log.setLevel(logging.DEBUG)

    conn = supabase_conn()

    mon = create_monitor(conn, args.debug)

    if args.start:
        mon.start()
    if args.list:
        mon.list()
    if args.one:
        mon.one()


def create_monitor(conn: AugmentedClient, debug: bool):
    mon = Monitor(conn=conn, debug=debug)
    return mon


if __name__ == "__main__":
    main()
