## Functionality of the Configurable Concurrency Oracle Tool

The Configurable Concurrency Oracle (CCO) detects concurrencies among the activities/events in the event log provided as .xes file. In its current version, it detects concurrency using the so-called "alpha" or lifecycle oracles, and it can detect and apply concurrency on activity level (logwise) or on event level (tracewise), selectable by the "mode" and "scope" parameters. In lifecycle oracle mode, all events occurring in between a start-activity and its first matching complete-activity are considered concurrent to the interval-defining activity. It then transforms the sequential traces of the log to partially ordered traces. Isomorphs among the partially ordered trace variants are identified using the VF2++ algorithm.<br><br>
The CCO can be used to analyze concurrencies in the log only, or to additionally export a partially ordered log. If you do not require a log output, please select "stats_only" = True, which will reduce the runtime of the tool.<br><br>
The CCO will always export a .csv file containing the concurrencies detected in the log, named "concurrencies.csv". Please note that concurrencies are defined and listed for pairs of activities, and all concurrencies appear in the file in both directions. Furthermore, there is a console output of the analysis report, showing the concurrencies detected in the log, and the total numbers of sequential and partially ordered traces in the log.<br><br>
If you need a .xes output of the partially ordered log, you need to specify a filename for the output file. The CCO can either keep all case variants of the processed event log in the output, but it can also compactify the log and reduce the output to one representative trace per sequential variant or one representative trace per partially ordered variant, selectable by the parameter "keep".<br><br>
Partial order information is added to the .xes output file as follows:

- A unique ID is added to every event using the key "identifier:id", example:

```
<int key="identity:id" value="0" />
```

- The successor nodes (events) of an event in the partial order are added on event level using the key "po_successors", which lists the successors' IDs as values of its children. Please note that events that are part of the partial order but have no successors (they may even be isolated nodes) nevertheless have a list of successors, which is empty. Events which are not part of the partial order but part of the sequential trace (e.g. start activities) have a "nan" value as po_successor list. Example for an event which has successors with IDs 1, 2 and 3:

```
  <list key="po_successors">
    <values>
     <string key="0" value="11" />
     <string key="1" value="12" />
     <string key="2" value="15" />
    </values>
   </list>
```

- The partial order variant number is added on trace level using the key "po_name", example:

```
  <float key="po_name" value="1.0" />
```

- In case of a reduction of the log, the combined multiplicities of the cases represented by a trace in the log is added on trace level using the key "multiplicity", example:

```
 <float key="multiplicity" value="3.0" />
```

## Parameters of the CCO Tool

- mode = "alpha" | "lifecycle"<br>
- scope = "logwise" | "tracewise"<br>
- infilename = the filename of the log to be processed, only .xes files are allowed<br>
- outfilename = the filename for the output log<br>
- stats_only = True | False<br>

## Installation

```bash
git clone https://github.com/sabinefw/ConfigurableConcurrencyOracleTool.git
cd ConfigurableConcurrencyOracleTool
pip install .
```

## Usage

Either from python:

```python
from cco import cco

cco(
    infilename="example-data/repairExampleNice.xes",
    outfilename="output-repairReduced.xes",
    mode="alpha",
    scope="tracewise",
    keep="one_per_po_variant",
    stats_only=False,
)
```

or call it directly from your shell as a CLI:

```bash
python -m cco example-data/repairExampleNice.xes output-repairReduced.xes
```
