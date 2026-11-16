## Functionality of the PEARL Tool

The PEARL Tool for Partial order Extraction, Analysis, Refinement and Log export is a tool that allows to detect concurrent or unorderable activities/events in an event log and to transform the data to partially ordered traces. It can be used to analyze concurrent/unordered events and the resulting partially ordered traces only, or to additionally export the partially ordered log. PEARL provides an interactive Web-Frontend but its backend is also usable as a CLI script. The event log must be provided as .xes file. <br>
In its current version, PEARL offers a choice of different extraction methods for both certain or uncertain semantics: the so-called "alpha" concurrency oracle, lifecycle-based and timestamp-based extraction methods. These methods can be applied either on activity level (logwise) or on event level (tracewise). In lifecycle-based extraction, all events occurring in between a start-activity and its first matching complete-activity are considered concurrent to the interval-defining activity. Via the interactive web frontend, the detected pairs are editable (i.e., add, select, deselect) in logwise scope. <br>
After the detection (and possible editing) of concurrent/unorderable pairs, PEARL transforms the traces of the log to partially ordered traces. Isomorphs among the partially ordered trace variants are identified using the VF2++ algorithm. In the web frontend, the generated partially ordered traces can be visually inspected, and selected or deselected for the export.<br>
In the web frontend, the export automatically condenses the file content to one representative per partially ordered variant, including its multiplicity (i.e., represented cases of the source log). In CLI use, it is also possible to retain and export all cases.<br>
<br>
Partial order information is added to the .xes output file as follows:

- A unique ID is added to every event using the key "identity:id", example:

```
<int key="identity:id" value="0" />
```

- The successor nodes (events) of an event in the partial order are added on event level using the key "po_successors", which lists the successors' IDs as values of its children. Please note that events that are part of the partial order but have no successors (they may even be isolated nodes) nevertheless have a list of successors, which is empty. Events which are not part of the partial order but part of the sequential trace (e.g. start activities) have an empty po_successors list. Example for an event which has successors with IDs 1, 2 and 3:

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

On log level, it also exports metadata information on the intended semantics (string key="po:semantics"), the applied extraction method (string key="po:extraction_method"), and the source data file name (string key="po:source").

To directly use it from your shell as a CLI (without UI frontend), please refer to the CCO Tool, also here on Github.
