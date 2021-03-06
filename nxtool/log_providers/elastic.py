from __future__ import print_function
import logging
import operator
import collections

try:  # Fuck you guido for removing reduce
    from functools import reduce
except ImportError:
    pass

try:
    from ConfigParser import SafeConfigParser as ConfigParser
except ImportError:  # python3
    from configparser import ConfigParser

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q, MultiSearch

from nxtool.log_providers import LogProvider


class Elastic(LogProvider):
    def __init__(self, config_file='config.cfg'):
        config = ConfigParser({'host': '127.0.0.1', 'use_ssl': True, 'index': 'nxapi', 'version': 2})
        config.read(config_file)

        version = config.getint('elastic', 'version')
        index = config.get('elastic', 'index')
        use_ssl = config.getboolean('elastic', 'use_ssl')
        host = config.get('elastic', 'host')

        self.client = Elasticsearch([host, ], use_ssl=use_ssl, index=index, version=version)
        self.search = Search(using=self.client, index='nxapi', doc_type='events').extra(size=10000)

    def export_search(self):
        return self.search

    def import_search(self, seach):
        self.search = seach

    def add_filters(self, filters):
        # We need to use multi_match, since we get the fields names dynamically.
        for key, value in filters.items():
            if isinstance(value, list):
                self.search = self.search.query(Q('bool', must=[
                    reduce(operator.or_, [Q('multi_match', query=v, fields=[key]) for v in value])])
                )
            else:
                self.search = self.search.query(Q("multi_match", query=value, fields=[key]))

    def get_top(self, field, size=250):
        search = self.search
        ret = dict()
        self.search = self.search.params(search_type="count")
        self.search.aggs.bucket('TEST', 'terms', field=field)
        for hit in self.search.execute(ignore_cache=True).aggregations['TEST']['buckets']:
            ret[hit['key']] = hit['doc_count']
        self.search = search
        return ret

    def get_relevant_ids(self, fields, percentage=10.0):
        """ This function is supposed to return the id that are the reparteed/present on the `fields`.

         :param list of str: fields:
         :return set of int:
         """
        ret = set()
        search = self.search
        ids = set(int(i['id']) for i in self.search.execute())  # get all possible ID
        self.search = search

        for _id in ids:
            search = self.search

            self.add_filters({'id': _id})

            # Get how many different fields there are for a given `id`
            step = 0.0
            data = collections.defaultdict(set)
            for res in self.search.execute():
                step += 1.0
                for field in fields:
                    data[field].add(res[field])

            # Ignore id that are present on less than 10% of different values of each fields
            for field, content in data.items():
                _percentage = len(content) / step * 100.0
                if _percentage > percentage:
                    continue
                logging.debug('Discarding id \033[32m%s\033[0m present in %d%% of different values of the \033[32m%s\033[0m field', _id, _percentage, field)
                break
            else:
                ret.add(_id)
            self.search = search

        return ret

    def reset_filters(self):
        self.search = Search(using=self.client, index='nxapi', doc_type='events').extra(size=10000)

    def get_results(self):
        """
        Return a `Result` object obtained from the execution of the search `self.search`.
        This method has a side effect: it re-initialize `self.search`.
        :return Result: The `Result` object obtained from the execution of the search `self.search`.
        """
        search = self.search
        result = self.search.scan()
        self.search = search
        return result
