import numpy as np
import pandas as pd
import pm4py
from copy import copy
from pm4py.objects.conversion.log import converter as log_converter


def generate_pm4py_list(my_list):
    """Convert a python iterable into something that pm4py exports as a 'list' XML tag."""

    my_list = copy(my_list)
    children = [(str(index), elem) for index, elem in enumerate(my_list)]
    return {"value": None, "children": children}


def keepOneRepresentativeAndMultiplicity(log, caseids_variante, m):
    """Reduces the input log to one representative of the same variant and adds its multiplicity."""

    if m == 0:
        # sometimes there is no multiplicity in the log but if the trace is there, it must be 1
        m = 1
    repr = caseids_variante[0]  # case id des ersten repräsentanten/case dieser variante

    # filter part of log with this variant / representative
    filter_ = log["case:concept:name"] == repr
    log.loc[filter_, "case:multiplicity"] = m  # save multiplicity of trace variant

    # do not discard first index of part of log in order to keep one representative
    caseids_variante.pop(0)
    discard = log["case:concept:name"].isin(caseids_variante)
    log = log[~discard]

    return log


def ordered_activities(case_id: str, log: pd.DataFrame):  # possibly not needed anymore
    """Return all activities, ordered by timestamp, of trace `case_id` from `log`."""

    this_case = log.query("`case:concept:name` == @case_id")
    this_case = this_case.sort_values("time:timestamp")
    return tuple(this_case["concept:name"])


def writePOinfo(log, caseids_variant, succ, po_name):
    """Write successors for every event in the partial order as a 'list'/pm4py-'dict' to log for write_xes export"""

    if "po_successors" not in log.columns:
        log["po_successors"] = pd.Series(dtype="object")
    if "case:po_name" not in log.columns:
        log["case:po_name"] = pd.Series(dtype=int)

    for caseid in caseids_variant:
        trace = log.query("`case:concept:name` == @caseid")
        offset = trace.index.min()  # activity id of first activity of current variant

        for event, event_successors in succ.items():
            event_id = event + offset
            successor_ids = np.array(event_successors) + offset
            succ_ids_pm4pylist = generate_pm4py_list(successor_ids)

            # assert log.index.name == "identity:id"
            log.at[event_id, "po_successors"] = succ_ids_pm4pylist
            log.at[event_id, "case:po_name"] = po_name

    return log

def write_xes_and_drop_NaNs(df: pd.DataFrame, output_file:str):
    log_with_postp = log_converter.apply(
        df, variant=log_converter.Variants.TO_EVENT_LOG,
        parameters={"stream_postprocessing": True}
    )
    pm4py.write_xes(log_with_postp, output_file)