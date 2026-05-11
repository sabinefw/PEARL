import pm4py
import cco_writers
from tqdm import tqdm


def read_log(infilename, mode, scope):
    """Reads log, filters for complete and (in lifecycle mode) start activites, writes unique event ids,
    extracts variant information and prepares logs for further transformation."""

    log = pm4py.read_xes(infilename)


    lc_available = "lifecycle:transition" in log.columns
    if mode == "lifecycle" and not lc_available:
        raise ValueError(
            "Lifecycle oracle mode is not executable due to missing lifecycle information in log."
        )

    if lc_available:
        filog_towrite = pm4py.filter_event_attribute_values(
            log,
            "lifecycle:transition",
            [
                "COMPLETE",
                "complete",
                "Complete",
            ],
            "event",
            True,
        )
    else:
        filog_towrite = log

    filog_towrite = filog_towrite.copy()

    # normal preparation of log in order to write partial order information later on
    # XXX: Is there a good reason not to start at 0?
    filog_towrite.loc[:, "identity:id"] = range(0, len(filog_towrite))
    filog_towrite.set_index("identity:id", inplace=True)

    caseid_dict = {}
    keyword_c = "default_c"
    keyword_s = "default_s"

    # normal identification of case ids per variant
    if not (mode == "lifecycle" and scope == "tracewise"):
        splitlog = pm4py.split_by_process_variant(filog_towrite)
        for k, v in splitlog:
            ids = v["case:concept:name"].unique()
            caseid_dict[k] = ids.tolist()

    # lifecycle mode needs additional information in the log for concurrency identification and maybe to write
    if mode == "lifecycle":
        filog_wlc, keyword_c, keyword_s = preprocess_lifecycle(log)
        vars_wlc = pm4py.get_variants(filog_wlc, activity_key="new:activity:identifier")

        if scope == "tracewise":
            # only in this case, the log with start and complete lifecycle information is used for writing the .xes file
            # therefore special preparation of log and specific identification of variant ids including lc start and stop info
            filog_wlc["identity:id"] = range(0, len(filog_wlc))
            filog_wlc.set_index("identity:id", inplace=True)

            splitlog = pm4py.split_by_process_variant(filog_wlc, activity_key="new:activity:identifier")
            for k, v in splitlog:
                ids = v["case:concept:name"].unique()
                caseid_dict[k] = ids.tolist()

            filog_towrite = filog_wlc.copy()

    else: # will not be used in non-lifecycle modes but must be set as return value
        filog_wlc = filog_towrite
        vars_wlc = pm4py.get_variants(filog_towrite, activity_key="concept:name")

    return filog_towrite, filog_wlc, vars_wlc, caseid_dict, keyword_c, keyword_s


def preprocess_lifecycle(log):
    filteredlogComplAndStart = pm4py.filter_event_attribute_values(
        log,
        "lifecycle:transition",
        ["COMPLETE", "complete", "Complete", "START", "start", "Start"],
        "event",
        True,
    )
    lcattributes = filteredlogComplAndStart["lifecycle:transition"].unique()
    if "Complete" in lcattributes:
        keyword_c = "_Complete"
        keyword_s = "_Start"
    elif "complete" in lcattributes:
        keyword_c = "_complete"
        keyword_s = "_start"
    else:
        keyword_c = "_COMPLETE"
        keyword_s = "_START"

    filog_wlc = filteredlogComplAndStart.copy()
    filog_wlc["new:activity:identifier"] = (
        filog_wlc.loc[:, "concept:name"]
        + "_"
        + filog_wlc.loc[:, "lifecycle:transition"]
    )
    # lifecycle mode braucht lifecycle Informationen im log zum extrahieren der concurrency
    return filog_wlc, keyword_c, keyword_s


def reduce_log_seq_variants(filog_towrite, mode, scope, vars, vars_wlc, caseid_dict):
    """Keeps only one sequential trace representative per sequential variant, discards duplicates"""

    if mode == "lifecycle" and scope == "tracewise":
        # lifecycle tracewise auf log w lc info schreiben
        seqv = vars_wlc.keys()
        vars = vars_wlc
    else:
        seqv = vars.keys()

    for v in tqdm(seqv, desc="reducing log, completed traces: "):
        # vorverarbeitung kondensieren, multiplizitäten
        multiplicity = vars[v]
        caseids_akt_variante = caseid_dict[v]
        caseid_dict[v] = [caseids_akt_variante[0]]

        # assert len(caseids_akt_variante) > 0, "no entries in teillog"

        filog_towrite = cco_writers.keepOneRepresentativeAndMultiplicity(
            filog_towrite, caseids_akt_variante, multiplicity
        )

    return filog_towrite, caseid_dict


def reduce_log_po_variants(filog_towrite):
    """Keeps only one sequential trace per partially ordered trace variant, i.e. only one representative of the sequential
    trace variant which lead to the same partially ordered trace, and their combined multiplicities.
    """

    po_ids = filog_towrite["case:po_name"].unique()
    for id in tqdm(po_ids, desc="reducing log, completed variants: "):
        filt_ = filog_towrite["case:po_name"] == id
        seqvarid = filog_towrite.loc[filt_, "case:concept:name"].unique()
        seqvarid = seqvarid.tolist()

        multsum = 0

        if len(seqvarid) > 0:
            for s in seqvarid:
                filt2_ = filog_towrite["case:concept:name"] == s
                casemult = filog_towrite.loc[filt2_, "case:multiplicity"].unique()
                multsum = multsum + casemult[0]

            filog_towrite = cco_writers.keepOneRepresentativeAndMultiplicity(
                filog_towrite, seqvarid, multsum
            )

    return filog_towrite
