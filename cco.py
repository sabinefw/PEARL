import typer
import pm4py
import pandas as pd
from enum import Enum

import cco_transformer
import cco_preparators
import cco_writers

app = typer.Typer()


class Mode(str, Enum):
    alpha = "alpha"
    lifecycle = "lifecycle"


class Scope(str, Enum):
    logwise = "logwise"
    tracewise = "tracewise"


class Keep(str, Enum):
    one_per_seq_variant = "one_per_seq_variant"
    all = "all"
    one_per_po_variant = "one_per_po_variant"


@app.command()
def cco(
    infilename: str = typer.Argument(help="Input .xes filename"),
    outfilename: str = typer.Argument(help="Output .xes filename"),
    mode: Mode = typer.Option(
        Mode.alpha,
        help="Algorithm used to detect concurrencies, either `alpha` or `lifecycle`",
    ),
    scope: Scope = typer.Option(
        Scope.logwise,
        help="Scope of concurrency detection, either `logwise` or `tracewise`",
    ),
    keep: Keep = typer.Option(
        Keep.all,
        help="How the output log will be reduced, either `one_per_seq_variant`, `all`, or `one_per_po_variant`",
    ),
    stats_only: bool = typer.Option(
        True, help="If True, only print statistics without generating an output file"
    ),
):
    """Transforms the sequentially ordered log from .xes input to a partially ordered log and prints analysis report on console,
    writes an .xes file containing additional partial order information based on the chosen parameters,
    possibly reduces the log to one representative of the same sequential or partial variant.
    """

    # TODO: Use exceptions instead of asserts
    # TODO: refactor to use enums
    modes = "alpha", "lifecycle"
    scopes = "logwise", "tracewise"
    keeps = "one_per_seq_variant", "all", "one_per_po_variant"
    assert mode in modes
    assert scope in scopes
    assert keep in keeps

    assert outfilename is not None or stats_only, "Provide an outfilename!"

    # read log and prepare for analysis and transformation
    filog_towrite, filog_wlc, vars_wlc, caseid_dict, keyword_c, keyword_s = (
        cco_preparators.read_log(infilename, mode, scope)
    )
    vars = pm4py.get_variants(filog_towrite, activity_key="concept:name")

    if not stats_only and keep != "all":
        # reduce log to one representative per sequential trace variant
        filog_towrite, caseid_dict = cco_preparators.reduce_log_seq_variants(
            filog_towrite, mode, scope, vars, vars_wlc, caseid_dict
        )

    # analyse concurrency, transform into partial orders, identify isomorphs, write into log
    filog_towrite, povariants = cco_transformer.transform_legacy(
        filog_towrite,
        mode,
        scope,
        vars,
        vars_wlc,
        stats_only,
        caseid_dict,
        keyword_c,
        keyword_s,
    )

    # analysis report
    if mode == "lifecycle" and scope == "tracewise":
        print("Number of sequential variants with start and complete lc info:")
        print(len(vars_wlc))
    else:
        print("Number of sequential variants:")
        print(len(vars))

    if stats_only:
        return

    # reduce log to one representative per partially ordered variant
    if keep == "one_per_po_variant":
        filog_towrite = cco_preparators.reduce_log_po_variants(filog_towrite)

    # drop analysis column
    if mode == "lifecycle" and scope == "tracewise":
        vars_at_end = pm4py.get_variants(
            filog_towrite, activity_key="new:activity:identifier"
        )
        filog_towrite = filog_towrite.drop(columns="new:activity:identifier")
    else:
        vars_at_end = pm4py.get_variants(filog_towrite, activity_key="concept:name")

    # check output and report
    print("Number of variants contained in the exported log:")
    print(len(vars_at_end))

    # write xes file
    filog_towrite.reset_index(inplace=True)
    filog_towrite["is_part_of_po"] = pd.Series(dtype=bool)
    #print(filog_towrite["po_successors"])
    #print(filog_towrite["is_part_of_po"])
    filog_towrite["is_part_of_po"] = filog_towrite["po_successors"].notna()
    filog_towrite["po_successors"] = filog_towrite["po_successors"].apply(lambda x:{'value':None,'children':[]} if pd.isna(x) else x)
    cco_writers.write_xes_and_drop_NaNs(filog_towrite, outfilename)
    #pm4py.fitness_token_based_replay()

if __name__ == "__main__":
    app()
