import collections
import fileinput
import mimetypes
import zipfile
import tarfile
import logging

from nxapi.nxlog import parse_nxlog

from nxtool.log_providers import LogProvider


class FlatFile(LogProvider):
    def __init__(self, fname='./tests/data/logs.txt'):
        self.logs = list()
        self.filters = collections.defaultdict(list)

        try:
            ftype = mimetypes.guess_all_extensions(fname)[0]
        except AttributeError:  # `fname` is None
            self.__transform_logs(fileinput.input(fname))
        except IndexError:  # `fname` has no guessable mimtype
            self.__transform_logs(fileinput.input(fname))
        else:
            if ftype == 'application/zip':  # zip file!
                with zipfile.ZipFile(fname) as f:
                    for name in f.namelist():
                        self.__transform_logs(f.read(name))
            elif ftype == 'application/tar':  # tar file!
                with tarfile.open(fname) as f:
                    for name in f.namelist():
                        self.__transform_logs(f.read(name))

    def __transform_logs(self, it):
        for line in it:
            _, log = parse_nxlog(line)
            if log:
                self.logs.append(log)

    def get_top(self, field, size=250):
        ret = dict()
        if field == 'zone':
            field = 'zone0'
        values = (log[field] for log in self.__get_filtered_logs())
        for key, value in collections.Counter(values).most_common(10):
            ret[key] = value
        return ret

    def __get_filtered_logs(self):
        """
        yield the loglines accordingly to the filtering policy defined in `self.filters`
        """
        if not self.filters:  # we don't filter, give everything!
            for log in self.logs:
                yield log
        else:
            for log in self.logs:
                for key, value in log.items():
                    if key in self.filters:  # are we filtering on this `key`?
                        if value in self.filters[key]:  # is the current `value` in the filtering list?
                            yield log

    def get_results(self):
        return self.__get_filtered_logs()

    def add_filters(self, filters):
        for key, value in filters.items():
            if key == 'zone':
                key = 'zone0'
            elif key == 'var_name':
                key = 'var_name0'
            self.filters[key].append(value)

    def get_relevant_ids(self, fields):
        """
         We want to keep alerts that are spread over a vast number of different`fields`

            To measure the spreading, we're using this metric: https://en.wikipedia.org/wiki/Coefficient_of_variation
        :param list of str fields:
        :return:
        """
        id_blacklist = set()
        ret = set()
        for field in fields:
            stats = collections.defaultdict(int)
            size = 0
            for logline in self.get_results():
                if logline['id0'] not in id_blacklist:
                    stats[logline['id0']] += 1
                size += 1

            for k, v in stats.items():
                if v < size / 10.0:
                    logging.debug('The id %s is present in less than 10%% (%d) of %s : non-significant.', k, v, field)
                    id_blacklist.add(k)
                else:
                    ret.add(k)

        return list(ret)
