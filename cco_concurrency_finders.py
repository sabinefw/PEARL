from typing import Optional

import pandas as pd

# Timestamp-based concurrency support for tracewise extraction.
from Concurrent import Concurrent

from warnings import warn


def findAlphaConcurrency(
    variants,
    successorlist: Optional[dict[str, list]] = None,
    concurrencies: Optional[Concurrent] = None,
):
    """Analyses if activity pairs occur in both orders and are thus to be considered concurrent (on trace or log level).
    Here, the concurrency is stored based on name of activity only, not on positions in trace i.e. instances of activites.
    """

    if concurrencies is None:
        concurrencies = Concurrent()
    if successorlist is None:
        successorlist = dict()

    previous = variants[0]
    for activity in variants[1:]:  # dictionary with successors for every activity
        if previous in successorlist:
            if activity not in successorlist[previous]:
                successorlist[previous].append(activity)
        else:
            successorlist[previous] = [activity]
        previous = activity

    # if k occurs as successor of s and v.v., they are concurrent
    for k, successors_of_k in successorlist.items():
        for s in successors_of_k:
            if k == s:
                continue
            if s in successorlist:
                successors_of_s = successorlist[s]
                if k in successors_of_s:
                    concurrencies.add_pair(k, s)
    return successorlist, concurrencies


class TimestampConcurrencyFinder:
    """Analyses if events in one trace share the same timestamp bucket. Timestamp
    concurrency is stored on activity level for reporting and on event position
    level for tracewise partial order generation.
    """

    def __init__(self, activities, timestamps, granularity="hour"):
        self.activities = tuple(activities)
        self.timestamps = tuple(timestamps)
        self.granularity = granularity

    def find(self):
        if len(self.activities) != len(self.timestamps):
            raise ValueError(
                "Activities and timestamps must contain the same number of events."
            )

        if self.granularity == "hour":
            frequency = "h"
        elif self.granularity == "minute":
            frequency = "min"
        elif self.granularity == "second":
            frequency = "s"
        elif self.granularity == "timestamp":
            frequency = None
        else:
            raise NotImplementedError()

        parsed_timestamps = pd.to_datetime(
            list(self.timestamps),
            errors="coerce",
            utc=True,
        )
        if parsed_timestamps.isna().any():
            raise ValueError(
                "Timestamp concurrency requires a valid time:timestamp value "
                "for every event."
            )

        if frequency is None:
            timestamp_buckets = parsed_timestamps
        else:
            timestamp_buckets = parsed_timestamps.floor(frequency)

        positions_by_bucket = {}
        for position, bucket in enumerate(timestamp_buckets):
            if bucket not in positions_by_bucket:
                positions_by_bucket[bucket] = []
            positions_by_bucket[bucket].append(position)

        activity_concurrencies = Concurrent()
        positional_concurrencies = Concurrent()
        concurrency_counts = {}

        for positions in positions_by_bucket.values():
            for offset, left_position in enumerate(positions):
                for right_position in positions[offset + 1 :]:
                    positional_concurrencies.add_pair(left_position, right_position)
                    pair = frozenset(
                        (
                            self.activities[left_position],
                            self.activities[right_position],
                        )
                    )
                    activity_concurrencies.add(pair)
                    concurrency_counts[pair] = (
                        concurrency_counts.get(pair, 0) + 1
                    )

        return {
            "concurrencies": activity_concurrencies,
            "positional_concurrencies": positional_concurrencies,
            "concurrency_counts": concurrency_counts,
        }


class LifecycleConcurrencyFinder:
    """Analyses if instances of activities with lifecyle information overlap. All activities which occur
    between start and complete of an activity instance are considered concurrent to this activity.
    If activities only have a start but no end, they are considered atomic as this defines no interval.
    Lifecycle concurrency is stored on an activity level (based on activity name) for logwise use,
    and on activity instance level (based on event position in trace) for tracewise use.
    """

    def __init__(
        self,
        variants,
        keyword_complete,
        keyword_start,
    ):
        self.variants = variants
        self._keyword_complete = keyword_complete
        self._keyword_start = keyword_start

    def _get_base_name(self, activity: str) -> str:
        if activity.endswith(self._keyword_complete):
            return activity.removesuffix(self._keyword_complete)
        elif activity.endswith(self._keyword_start):
            return activity.removesuffix(self._keyword_start)
        else:
            raise ValueError(
                f"Lifecycle-activities have to end in either `{self._keyword_start}` or "
                f"`{self._keyword_complete}`, but this one (`{activity}` doesn't!"
            )

    def find(self):

        pos_equivalents = {}
        pos_concurrency = {}
        concurrency = Concurrent()
        self._concurrency_counts = {}
        self._activities_with_starts = {
            self._get_base_name(activity)
            for activity in self.variants
            if activity.endswith(self._keyword_start)
        }

        starting_activity_idxs = [
            i for i, v in enumerate(self.variants) if v.endswith(self._keyword_start)
        ]
        if len(starting_activity_idxs) == 0:
            #warn("No starting events found!")
            pass
        elif starting_activity_idxs[-1] == len(self.variants) - 1:
            # a var can only be starting if there is an ending var after it
            del starting_activity_idxs[-1]

        for starting_activity_idx in starting_activity_idxs:
            concurs_found, extended_pos_concur, stopping_activity_idx = (
                self._find_concurrs_to_this_activity(
                    starting_activity_idx,
                    pos_concurrency,
                )
            )
            if stopping_activity_idx is not None:
                concurrency = concurrency.union(concurs_found)
                pos_concurrency = extended_pos_concur
                pos_equivalents[starting_activity_idx] = stopping_activity_idx

        rv_pos_concur = Concurrent()
        for main, concurrents in pos_concurrency.items():
            for c in concurrents:
                rv_pos_concur.add_pair(main, c)

        return dict(
            concurrencies=concurrency,
            positional_concurrencies=rv_pos_concur,
            positional_equivalences=pos_equivalents,
            concurrency_counts=self._concurrency_counts,
        )

    def _find_concurrs_to_this_activity(
        self,
        starting_activity_idx,
        pos_concurrency,
    ):
        conc_cand_names = Concurrent()
        conc_cand_pos = []
        interval_concurrency_counts = {}

        starting_activity = self.variants[starting_activity_idx]
        stopping_activity_name = starting_activity.replace(self._keyword_start, self._keyword_complete)

        # register concurrencies until the stopping variant is found
        all_following_activities = self.variants[starting_activity_idx + 1:]
        indices = range(starting_activity_idx + 1, len(self.variants))
        for f_i, following_act in zip(indices, all_following_activities):
            if following_act == stopping_activity_name:
                stopping_act = following_act
                stopping_act_idx = f_i
                break

            starting_base_name = self._get_base_name(starting_activity)
            following_base_name = self._get_base_name(following_act)
            conc_cand_names.add_pair(
                starting_base_name, following_base_name
            )  # NOTE: self-concurrency is possible!
            conc_cand_pos.append(f_i)

            # Count an inner activity once: at its start, or at its complete event
            # when the activity has no lifecycle start in this variant.
            is_atomic_complete = (
                following_act.endswith(self._keyword_complete)
                and following_base_name
                not in getattr(self, "_activities_with_starts", set())
            )
            if following_act.endswith(self._keyword_start) or is_atomic_complete:
                pair = frozenset((starting_base_name, following_base_name))
                interval_concurrency_counts[pair] = (
                    interval_concurrency_counts.get(pair, 0) + 1
                )
        else:
            stopping_act_idx = None
            stopping_act = None

        # only save candidates if interval is closed with activity complete
        if stopping_act is not None:
            concurrency = conc_cand_names

            concur_pos = conc_cand_pos
            if stopping_act_idx not in pos_concurrency:
                if len(concur_pos) > 0:
                    pos_concurrency[stopping_act_idx] = concur_pos
            else:
                for c in concur_pos:
                    if c not in pos_concurrency[stopping_act_idx]:
                        pos_concurrency[stopping_act_idx].append(c)

            if not hasattr(self, "_concurrency_counts"):
                self._concurrency_counts = {}
            for pair, count in interval_concurrency_counts.items():
                self._concurrency_counts[pair] = (
                    self._concurrency_counts.get(pair, 0) + count
                )
        else:
            concurrency = Concurrent()

        return concurrency, pos_concurrency, stopping_act_idx
