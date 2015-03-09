from django.core.cache.backends.memcached import MemcachedCache


class Nonpickler(object):
    def __init__(self, file, protocol=None):
        self.file = file

    def dump(self, val):
        self.file.write(val)


class Nonunpickler(object):
    def __init__(self, file):
        self.file = file

    def load(self, val):
        self.file.read()


class CacheMessage(object):
    def __init__(self, dict, prefix):
        self.dict = dict
        self.prefix = prefix

    def __len__(self):
        return len(self.dict)

    def __getitem__(self, name):
        return self.dict[self.prefix + name]

    def __setitem__(self, name, value):
        self.dict[self.prefix + name] = value

    def get(self, name):
        return self.dict.get(self.prefix + name)

    def iterkeys(self):
        i = len(self.prefix)
        for key in self.dict:
            yield key[i:]


class StringCache(MemcachedCache):
    """Django Memcached bindings for caching trivially serialisable data.

    Anything that can you can directly .write() and then .read() back
    unambiguously from a StringIO object can be used with this cache backend.
    """
    @property
    def _cache(self):
        """
        Implements transparent thread-safe access to a memcached client.
        """
        if getattr(self, '_client', None) is None:
            self._client = self._lib.Client(
                self._servers,
                pickler=Nonpickler,
                unpickler=Nonunpickler
            )
        return self._client

    def get_many(self, keys, version=None):
        new_keys = map(lambda x: self.make_key(x, version=version), keys)
        ret = self._cache.get_multi(new_keys)
        prefix = self.make_key('X', version=version)[:-1]
        return CacheMessage(ret, prefix)

    def get_cache_message(self, version=None):
        prefix = self.make_key('X', version=version)[:-1]
        return CacheMessage(dict(), prefix)

    def set_many(self, cache_message, timeout=0):
        self._cache.set_multi(
            cache_message.dict,
            self._get_memcache_timeout(timeout)
        )


class QuickPickleCache(MemcachedCache):
    @property
    def _cache(self):
        """
        Implements transparent thread-safe access to a memcached client.
        """
        if getattr(self, '_client', None) is None:
            self._client = self._lib.Client(self._servers, pickleProtocol=-1)
        return self._client
