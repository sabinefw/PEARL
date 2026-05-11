from typing import Optional
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
        )

    def _find_concurrs_to_this_activity(
        self,
        starting_activity_idx,
        pos_concurrency,
    ):
        conc_cand_names = Concurrent()
        conc_cand_pos = []

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

            conc_cand_names.add_pair(
                self._get_base_name(starting_activity), self._get_base_name(following_act)
            )  # NOTE: self-concurrency is possible!
            conc_cand_pos.append(f_i)
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
        else:
            concurrency = Concurrent()

        return concurrency, pos_concurrency, stopping_act_idx
