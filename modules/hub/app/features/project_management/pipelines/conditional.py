from collections import OrderedDict
from collections.abc import Mapping

# Request identity: URL path plus its query parameters in sorted order.
ConditionalKey = tuple[str, tuple[tuple[str, str], ...]]


def conditional_key(path: str, params: Mapping[str, str | int] | None = None) -> ConditionalKey:
    return path, tuple(sorted((str(k), str(v)) for k, v in (params or {}).items()))


class ConditionalCache:
    """Last successful GitHub response body and its ETag per request, for ``If-None-Match`` revalidation.

    Entries are keyed by URL and parameters only, never by token: GitHub authorizes a conditional
    request with the caller's credentials before it answers 304, so a caller without access still
    receives its own error. Only successful responses carrying an ETag are stored. Memory is bounded
    by entry count and total body bytes (least recently used first); a body larger than
    ``max_entry_bytes`` is not stored.
    """

    def __init__(
        self,
        max_entries: int = 2048,
        max_bytes: int = 32 * 1024 * 1024,
        max_entry_bytes: int = 8 * 1024 * 1024,
    ):
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self.max_entry_bytes = min(max_entry_bytes, max_bytes)
        self.bytes = 0
        self.entries: OrderedDict[ConditionalKey, tuple[str, bytes]] = OrderedDict()

    def get(self, key: ConditionalKey) -> tuple[str, bytes] | None:
        entry = self.entries.get(key)
        if entry is not None:
            self.entries.move_to_end(key)
        return entry

    def put(self, key: ConditionalKey, etag: str, body: bytes) -> None:
        self.discard(key)
        if not etag or len(body) > self.max_entry_bytes:
            return
        self.entries[key] = (etag, body)
        self.bytes += len(body)
        while self.bytes > self.max_bytes or len(self.entries) > self.max_entries:
            _, (_, dropped) = self.entries.popitem(last=False)
            self.bytes -= len(dropped)

    def discard(self, key: ConditionalKey) -> None:
        entry = self.entries.pop(key, None)
        if entry is not None:
            self.bytes -= len(entry[1])


conditional_cache = ConditionalCache()
