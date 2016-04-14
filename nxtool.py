import argparse
import sys

import urllib3
urllib3.disable_warnings()

from nxapi import filter, statistics
from nxapi.log_providers import elastic, flat_file


def __filter(filters):
    _filter = {}
    for param in filters.split(','):
        try:
            key, value = param.split('=')
        except ValueError:
            print('Parameters should be of the form key=value,key2=value2,...')
            return
        _filter[key] = value
    filter.generate_filter(args.hostname, _filter, source)


def __create_argparser():
    parser = argparse.ArgumentParser(description='Sweet tool to help you managing your naxsi logs.')

    parser.add_argument('hostname', action='store')

    log_sources = parser.add_argument_group('Log sources')
    log_sources.add_argument('--elastic', action='store_true')
    log_sources.add_argument('--flat_file', action='store_true')

    actions = parser.add_argument_group('Actions')
    actions.add_argument('--typing', action='store_true')
    actions.add_argument('--whitelist', action='store_true')
    actions.add_argument('--filter', action='store')
    actions.add_argument('--stats', action='store_true')

    return parser.parse_args()

args = __create_argparser()

source = None  # silent a pycharm warning
if args.elastic is True:
    source = elastic.Elastic()
elif args.flat_file is True:
    source = flat_file
else:
    print('Please give me a source.')
    sys.exit(1)

if args.filter is not None:
    __filter(args.filter)
elif args.stats:
    statistics.generate_statistics(source)
else:
    print('Please five me a valid action to do.')