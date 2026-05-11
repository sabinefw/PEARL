from itertools import permutations


# XXX: We're not wrapping all set methods, so some methods might return a
# set instead of a Concurrent object
class Concurrent(set):
    """Represents a set of pairs. Each pair is concurrent."""

    def add_pair(self, *concurrent_items):
        self.add(frozenset(concurrent_items))

    def add(self, element):
        if not isinstance(element, frozenset):
            raise ValueError()
        super().add(element)

    def to_tuples(self):
        """Return an iterable of 2-tuples in all allowed, concurrent realizations"""
        for pair in self:
            if len(pair) == 1:
                # self-concurrent event
                (singular,) = pair
                yield (singular, singular)
            else:
                for realization in permutations(pair, 2):
                    yield realization

    def union(self, other):
        return Concurrent(super().union(other))

    def difference(self, other):
        return Concurrent(super().difference(other))
