import pm4py
from pandas.testing import assert_frame_equal

from cco import cco

OUT_DIR = "generated_test_data/"
MODES = "alpha", "lifecycle"
SCOPES = "logwise", "tracewise"
KEEPS = "one", "all"


def generate_test_logs(name):
    for m in MODES:
        for s in SCOPES:
            for k in KEEPS:
                print(f"Processing {m}, {s}, {k}...")
                if m == "alpha":
                    inputfile = "repairExample.xes"
                elif m == "lifecycle":
                    inputfile = "christest.xes"
                outputfile = gen_fname(m, s, k, name)

                cco(m, s, k, inputfile, OUT_DIR + outputfile)


def gen_fname(m, s, k, name):
    outputfile = f"output_{name}_{m}_{s}_{k}.xes"
    return outputfile


def test_dummy():
    pass


def test_coo_regression():
    target_name = "regression"
    test_name = "test-regression"
    generate_test_logs(test_name)

    for m in MODES:
        for s in SCOPES:
            for k in KEEPS:
                target = pm4py.read_xes(OUT_DIR + gen_fname(m, s, k, target_name))
                test = pm4py.read_xes(OUT_DIR + gen_fname(m, s, k, test_name))
                assert_frame_equal(target, test)


if __name__ == "__main__":
    generate_test_logs("regression")
