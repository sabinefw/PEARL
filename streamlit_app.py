import os
import sys
import tempfile
from html import escape

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".pyvis_vendor"))

import networkx as nx
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

from Concurrent import Concurrent
from cco_service import CCOService

UI_SCALE = 0.8
VIEWPORT_HEIGHT_RESERVE = 0
TAB_PANEL_HEIGHT = round(610 * UI_SCALE) - VIEWPORT_HEIGHT_RESERVE
PANEL_BOX_TOP_GAP = round(18 * UI_SCALE)
PANEL_BOX_VERTICAL_RESERVE = round(24 * UI_SCALE)
LOGWISE_BOX_HEIGHT = TAB_PANEL_HEIGHT - PANEL_BOX_VERTICAL_RESERVE - PANEL_BOX_TOP_GAP
TRACEWISE_BOX_HEIGHT = LOGWISE_BOX_HEIGHT
CONCURRENCY_LIST_HEIGHT = LOGWISE_BOX_HEIGHT - round(235 * UI_SCALE)
TRACEWISE_CONCURRENCY_VERTICAL_RESERVE = round(220 * UI_SCALE)
TRACEWISE_CONCURRENCY_LIST_HEIGHT = (
    TRACEWISE_BOX_HEIGHT - TRACEWISE_CONCURRENCY_VERTICAL_RESERVE
)
COMPACT_ACTION_LIST_HEIGHT_COMPENSATION = round(24 * UI_SCALE)
LOGWISE_CONCURRENCY_LIST_HEIGHT = (
    CONCURRENCY_LIST_HEIGHT + COMPACT_ACTION_LIST_HEIGHT_COMPENSATION
)
PO_TRACE_LIST_HEIGHT = (
    LOGWISE_BOX_HEIGHT
    - round(250 * UI_SCALE)
    + COMPACT_ACTION_LIST_HEIGHT_COMPENSATION
)
GRAPH_VIEW_HEIGHT = LOGWISE_BOX_HEIGHT - round(80 * UI_SCALE)
GRAPH_VIEW_VARIANT_LABEL_HEIGHT = round(70 * UI_SCALE)
GRAPH_VIEW_VARIANT_SPACER_HEIGHT = round(10 * UI_SCALE)

# ONLY VISUAL FIX
st.set_page_config(layout="wide")
st.markdown(
    """
    <style>
    :root {
        --ui-scale: __UI_SCALE__;
        --app-height: 100vh;
        --panel-height: calc(var(--app-height) - 9.6rem);
        --column-height: calc(var(--panel-height) - 1.35rem);
        --tab-border-color: #000000;
        --tab-border-width: 1px;
    }
    html {
        font-size: calc(16px * var(--ui-scale));
    }
    div[data-testid="stAppViewContainer"] .main .block-container,
    div[data-testid="stAppViewContainer"] [data-testid="block-container"],
    div[data-testid="stMainBlockContainer"] {
        padding-top: 0 !important;
        padding-bottom: 1rem;
    }
    div[data-testid="stAppViewContainer"] .main,
    section[data-testid="stMain"] {
        padding-top: 0;
    }
    header[data-testid="stHeader"] {
        height: 2.35rem;
    }
    header[data-testid="stHeader"] > div {
        padding-top: 0.15rem;
        padding-bottom: 0.15rem;
    }
    h1 {
        margin-top: 0;
        padding-top: 0;
        margin-bottom: 1.2rem;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        width: 100%;
        gap: 0.35rem;
        border-bottom: var(--tab-border-width) solid var(--tab-border-color);
        padding-left: 0.1rem;
        padding-bottom: 0;
        box-sizing: border-box;
        align-items: end;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-panel"],
    div[data-testid="stTabs"] [role="tabpanel"] {
        border: 0;
        padding: 0;
        min-height: var(--panel-height);
        height: var(--panel-height);
        overflow: visible;
        box-sizing: border-box;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-panel"] > div,
    div[data-testid="stTabs"] [role="tabpanel"] > div {
        height: 100%;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-panel"] div[data-testid="stVerticalBlock"],
    div[data-testid="stTabs"] [role="tabpanel"] div[data-testid="stVerticalBlock"] {
        height: 100%;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-panel"] div[data-testid="stHorizontalBlock"],
    div[data-testid="stTabs"] [role="tabpanel"] div[data-testid="stHorizontalBlock"] {
        height: 100%;
        align-items: stretch;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-panel"] div[data-testid="column"],
    div[data-testid="stTabs"] [role="tabpanel"] div[data-testid="column"] {
        height: 100%;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-panel"] div[data-testid="column"] > div,
    div[data-testid="stTabs"] [role="tabpanel"] div[data-testid="column"] > div {
        height: 100%;
    }
    div[data-testid="stTabs"] [data-baseweb="tab"] {
        flex: 1 1 0;
        height: 2.65rem;
        background: #f0f2f6;
        border: var(--tab-border-width) solid var(--tab-border-color);
        border-radius: 0.7rem 0.7rem 0 0;
        color: #374151;
        font-weight: 600;
        box-shadow: none;
        position: relative;
        z-index: 1;
        overflow: visible;
        margin-bottom: 0;
    }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
    div[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
        background: #ffffff;
        color: #111827;
        border-color: var(--tab-border-color);
        border-bottom-color: #ffffff;
        box-shadow: none;
        margin-bottom: -1px;
        z-index: 2;
    }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"]::after,
    div[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"]::after {
        content: "";
        position: absolute;
        left: -1px;
        right: -1px;
        bottom: -2px;
        height: 4px;
        background: #ffffff;
        z-index: 3;
    }
    .st-key-logwise_panel div[data-testid="stVerticalBlockBorderWrapper"],
    .st-key-tracewise_panel div[data-testid="stVerticalBlockBorderWrapper"] {
        border: var(--tab-border-width) solid var(--tab-border-color) !important;
        border-top: 0 !important;
        border-top-left-radius: 0 !important;
        border-top-right-radius: 0 !important;
        background: #ffffff !important;
        margin-top: -1px !important;
        box-shadow: none !important;
    }
    .st-key-logwise_panel div[data-testid="stVerticalBlockBorderWrapper"] > div,
    .st-key-tracewise_panel div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background: #ffffff !important;
    }
    div[data-testid="stTabs"] button[role="tab"]:focus,
    div[data-testid="stTabs"] button[role="tab"]:focus-visible,
    div[data-testid="stTabs"] [data-baseweb="tab"]:focus,
    div[data-testid="stTabs"] [data-baseweb="tab"]:focus-visible {
        outline: none !important;
        box-shadow: none !important;
    }
    .status-banner {
        min-height: 3.45rem;
        height: 3.45rem;
        border-radius: 0.7rem;
        padding: 0.7rem 1rem;
        border: 1px solid transparent;
        display: flex;
        align-items: center;
        font-weight: 500;
        margin-top: 0;
        font-size: 1.18rem;
        box-sizing: border-box;
    }
    .status-success {
        background: #dcfce7;
        border-color: #86efac;
        color: #166534;
    }
    .status-info {
        background: #dbeafe;
        border-color: #93c5fd;
        color: #1d4ed8;
    }
    .status-warning {
        background: #fef3c7;
        border-color: #f59e0b;
        color: #92400e;
    }
    .status-error {
        background: #fee2e2;
        border-color: #fca5a5;
        color: #b91c1c;
    }
    .status-empty {
        background: #f8fafc;
        border-color: #e5e7eb;
        color: transparent;
    }
    div[data-testid="stWidgetLabel"] p,
    div[data-testid="stMarkdownContainer"] p,
    .stButton > button,
    .stDownloadButton > button,
    div[role="radiogroup"] label,
    div[data-baseweb="select"] * {
        font-size: 1.18rem;
    }
    .stButton > button,
    .stDownloadButton > button {
        min-height: 1.9rem;
        height: 1.9rem;
    }
    div[data-testid="stFileUploaderDropzone"] {
        min-height: 2.9rem;
        height: 2.9rem;
        padding-top: 0.2rem;
        padding-bottom: 0.2rem;
        box-sizing: border-box;
    }
    div[data-baseweb="select"] > div {
        min-height: 3.45rem;
        height: 3.45rem;
        box-sizing: border-box;
    }
    .top-status-label {
        height: 1.75rem;
        font-size: 1.18rem;
        font-weight: 400;
        color: #31333f;
        line-height: 1.75rem;
        margin-bottom: 0.45rem;
    }
    .column-divider {
        width: 1px;
        min-height: 100%;
        background: #d1d5db;
        margin: 0 auto;
    }
    .section-spacer {
        height: 0.95rem;
    }
    .add-concurrency-arrow {
        height: 1.9rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
    }
    .st-key-logwise_conc div[data-baseweb="select"] * {
        font-size: 1rem !important;
        line-height: 1.1 !important;
    }
    .st-key-logwise_conc div[data-baseweb="select"] > div {
        display: flex !important;
        align-items: center !important;
        min-height: 1.9rem !important;
        height: 1.9rem !important;
    }
    .st-key-logwise_conc div[data-baseweb="select"] div[role="combobox"] {
        display: flex !important;
        align-items: center !important;
        min-height: 1.9rem !important;
    }
    div[data-testid="stCheckbox"] input[type="checkbox"],
    div[role="radiogroup"] input[type="radio"] {
        accent-color: #16a34a !important;
    }
    div[data-testid="stCheckbox"] [data-checked="true"],
    div[role="radiogroup"] [data-checked="true"] {
        background-color: #16a34a !important;
        border-color: #16a34a !important;
    }
    div[data-testid="stCheckbox"] svg,
    div[role="radiogroup"] svg {
        fill: #16a34a !important;
    }
    </style>
    """.replace("__UI_SCALE__", str(UI_SCALE)),
    unsafe_allow_html=True,
)

components.html(
    """
    <script>
    const setAppHeight = () => {
      const h = window.innerHeight || document.documentElement.clientHeight || 0;
      window.parent.document.documentElement.style.setProperty("--app-height", `${h}px`);
    };
    setAppHeight();
    window.addEventListener("resize", setAppHeight);
    </script>
    """,
    height=0,
)

st.title("PEARL - Partial order Extraction, Analysis, Refinement and Log export")
st.markdown('<div style="height: calc(0.5cm * var(--ui-scale));"></div>', unsafe_allow_html=True)

# Service initialisieren
if "cco_service" not in st.session_state:
    st.session_state["cco_service"] = CCOService()

cco = st.session_state["cco_service"]

# PO TRACE STATE
if "po_traces" not in st.session_state:
    st.session_state["po_traces"] = {}

if "uploaded_file_bytes" not in st.session_state:
    st.session_state["uploaded_file_bytes"] = None

if "uploaded_file_name" not in st.session_state:
    st.session_state["uploaded_file_name"] = None

if "ui_message" not in st.session_state:
    st.session_state["ui_message"] = None

if "po_trace_downloads" not in st.session_state:
    st.session_state["po_trace_downloads"] = {}

if "detected_concurrencies" not in st.session_state:
    st.session_state["detected_concurrencies"] = {}

if "manually_added_concurrencies" not in st.session_state:
    st.session_state["manually_added_concurrencies"] = {}

if "pending_concurrency_changes" not in st.session_state:
    st.session_state["pending_concurrency_changes"] = {}

if "stale_po_results" not in st.session_state:
    st.session_state["stale_po_results"] = {}

if "selected_po_variant_ids" not in st.session_state:
    st.session_state["selected_po_variant_ids"] = {}

if "saved_po_variant_ids" not in st.session_state:
    st.session_state["saved_po_variant_ids"] = {}

if "pending_po_variant_selection_changes" not in st.session_state:
    st.session_state["pending_po_variant_selection_changes"] = {}

if "viewed_po_variant_ids" not in st.session_state:
    st.session_state["viewed_po_variant_ids"] = {}

if "upload_widget_nonce" not in st.session_state:
    st.session_state["upload_widget_nonce"] = 0

if "pending_uploaded_file_name" not in st.session_state:
    st.session_state["pending_uploaded_file_name"] = None

if "pending_uploaded_file_bytes" not in st.session_state:
    st.session_state["pending_uploaded_file_bytes"] = None


def make_scope_key(mode, scope):
    return f"{mode}:{scope}"


def set_nested_session_value(dict_key, item_key, value):
    mapping = dict(st.session_state.get(dict_key, {}))
    mapping[item_key] = value
    st.session_state[dict_key] = mapping


def get_detected_concurrency_pairs(mode, scope):
    scope_key = make_scope_key(mode, scope)
    detected_pairs = st.session_state.get("detected_concurrencies", {}).get(scope_key)
    if detected_pairs is not None:
        return detected_pairs

    state = cco.get_state(mode, scope)
    detected_pairs = state.get("detected_concurrencies")
    if detected_pairs is not None:
        set_nested_session_value("detected_concurrencies", scope_key, detected_pairs)
        return detected_pairs

    return None


def set_detected_concurrency_pairs(mode, scope, detected_pairs):
    scope_key = make_scope_key(mode, scope)
    set_nested_session_value("detected_concurrencies", scope_key, detected_pairs)
    cco.get_state(mode, scope)["detected_concurrencies"] = detected_pairs


def get_manually_added_concurrency_pairs(mode, scope):
    scope_key = make_scope_key(mode, scope)
    return st.session_state["manually_added_concurrencies"].get(scope_key, set())


def set_manually_added_concurrency_pairs(mode, scope, manually_added_pairs):
    scope_key = make_scope_key(mode, scope)
    set_nested_session_value(
        "manually_added_concurrencies", scope_key, manually_added_pairs
    )


def set_user_concurrency_pairs(mode, scope, user_pairs):
    scope_key = make_scope_key(mode, scope)
    set_nested_session_value("user_concurrencies", scope_key, user_pairs)


def _concurrency_pairs(concurrencies):
    if concurrencies is None:
        return set()
    return {frozenset(pair) for pair in concurrencies.to_tuples()}


def get_logwise_changes_pending(mode):
    scope_key = make_scope_key(mode, "logwise")
    return st.session_state["pending_concurrency_changes"].get(scope_key, False)


def set_logwise_changes_pending(mode, changes_pending):
    scope_key = make_scope_key(mode, "logwise")
    set_nested_session_value("pending_concurrency_changes", scope_key, changes_pending)


def update_logwise_changes_pending(mode):
    scope_key = make_scope_key(mode, "logwise")
    user_pairs = st.session_state.get("user_concurrencies", {}).get(scope_key, set())
    saved_pairs = _concurrency_pairs(cco.get_state(mode, "logwise").get("concurrencies"))
    changes_pending = user_pairs != saved_pairs
    was_pending = get_logwise_changes_pending(mode)
    set_logwise_changes_pending(mode, changes_pending)
    return changes_pending, changes_pending != was_pending


def get_po_results_stale(mode):
    scope_key = make_scope_key(mode, "logwise")
    return st.session_state["stale_po_results"].get(scope_key, False)


def set_po_results_stale(mode, stale):
    scope_key = make_scope_key(mode, "logwise")
    set_nested_session_value("stale_po_results", scope_key, stale)


def render_concurrency_summary(automatically_detected, manually_added):
    st.markdown(
        '<div class="count-summary">'
        f"{automatically_detected} pairs automatically detected and "
        f"{manually_added} manually added"
        "</div>",
        unsafe_allow_html=True,
    )


def get_total_case_count(mode, scope):
    variants = cco.get_state(mode, scope).get("vars") or {}
    return sum(int(multiplicity) if multiplicity else 1 for multiplicity in variants.values())


def render_po_variant_summary(mode, scope, po_variants):
    total_cases = get_total_case_count(mode, scope)
    st.markdown(
        f'<div class="count-summary">{len(po_variants)} PO variants '
        f"(total: {total_cases} cases)</div>",
        unsafe_allow_html=True,
    )


def _po_variant_ids(po_variants):
    return {po.graph["id"] for po in po_variants}


def get_selected_po_variant_ids(mode, scope):
    scope_key = make_scope_key(mode, scope)
    return st.session_state["selected_po_variant_ids"].get(scope_key)


def set_selected_po_variant_ids(mode, scope, po_variant_ids):
    scope_key = make_scope_key(mode, scope)
    set_nested_session_value("selected_po_variant_ids", scope_key, set(po_variant_ids))


def get_saved_po_variant_ids(mode, scope):
    scope_key = make_scope_key(mode, scope)
    return st.session_state["saved_po_variant_ids"].get(scope_key)


def set_saved_po_variant_ids(mode, scope, po_variant_ids):
    scope_key = make_scope_key(mode, scope)
    set_nested_session_value("saved_po_variant_ids", scope_key, set(po_variant_ids))


def get_po_variant_selection_changes_pending(mode, scope):
    scope_key = make_scope_key(mode, scope)
    return st.session_state["pending_po_variant_selection_changes"].get(
        scope_key, False
    )


def set_po_variant_selection_changes_pending(mode, scope, changes_pending):
    scope_key = make_scope_key(mode, scope)
    set_nested_session_value(
        "pending_po_variant_selection_changes", scope_key, changes_pending
    )


def _clear_po_variant_selection_widgets(mode, scope):
    for key in list(st.session_state.keys()):
        if key.startswith(f"po_variant_selected_{mode}_{scope}_"):
            del st.session_state[key]


def get_viewed_po_variant_id(mode, scope):
    scope_key = make_scope_key(mode, scope)
    return st.session_state["viewed_po_variant_ids"].get(scope_key)


def set_viewed_po_variant_id(mode, scope, po_variant_id):
    scope_key = make_scope_key(mode, scope)
    set_nested_session_value("viewed_po_variant_ids", scope_key, po_variant_id)


def reset_po_variant_selection(mode, scope, po_variants):
    scope_key = make_scope_key(mode, scope)
    po_variant_ids = _po_variant_ids(po_variants)
    set_selected_po_variant_ids(mode, scope, po_variant_ids)
    set_saved_po_variant_ids(mode, scope, po_variant_ids)
    set_po_variant_selection_changes_pending(mode, scope, False)
    set_viewed_po_variant_id(
        mode,
        scope,
        po_variants[0].graph["id"] if po_variants else None,
    )

    _clear_po_variant_selection_widgets(mode, scope)
    for key in list(st.session_state.keys()):
        if key == f"po_radio_{mode}_{scope}":
            del st.session_state[key]

    st.session_state["po_trace_downloads"].pop(scope_key, None)


def ensure_po_variant_selection(mode, scope, po_variants):
    po_variant_ids = _po_variant_ids(po_variants)
    selected_po_variant_ids = get_selected_po_variant_ids(mode, scope)
    if selected_po_variant_ids is None:
        selected_po_variant_ids = set(po_variant_ids)
        set_selected_po_variant_ids(mode, scope, selected_po_variant_ids)

    saved_po_variant_ids = get_saved_po_variant_ids(mode, scope)
    if saved_po_variant_ids is None:
        set_saved_po_variant_ids(mode, scope, selected_po_variant_ids)
        set_po_variant_selection_changes_pending(mode, scope, False)

    viewed_po_variant_id = get_viewed_po_variant_id(mode, scope)
    if viewed_po_variant_id not in po_variant_ids:
        viewed_po_variant_id = po_variants[0].graph["id"] if po_variants else None
        set_viewed_po_variant_id(mode, scope, viewed_po_variant_id)

    return selected_po_variant_ids, viewed_po_variant_id


def render_po_variant_list(mode, scope, po_variants, disabled=False):
    selected_po_variant_ids, viewed_po_variant_id = ensure_po_variant_selection(
        mode, scope, po_variants
    )
    updated_selected_po_variant_ids = set(selected_po_variant_ids)

    with st.container(height=PO_TRACE_LIST_HEIGHT, border=False):
        for po in po_variants:
            po_variant_id = po.graph["id"]
            select_column, view_column = st.columns(
                [1, 0.22], gap="small", vertical_alignment="center"
            )

            with select_column:
                is_selected = st.checkbox(
                    f"PO {po_variant_id}  ({po.graph.get('multiplicity', 0)} cases)",
                    key=f"po_variant_selected_{mode}_{scope}_{po_variant_id}",
                    value=(po_variant_id in selected_po_variant_ids),
                    disabled=disabled,
                )

            with view_column:
                view_container_key = (
                    f"po_variant_view_container_active_{mode}_{scope}_{po_variant_id}"
                    if po_variant_id == viewed_po_variant_id
                    else f"po_variant_view_container_{mode}_{scope}_{po_variant_id}"
                )
                with st.container(key=view_container_key):
                    if st.button(
                        "View",
                        key=f"po_variant_view_{mode}_{scope}_{po_variant_id}",
                        disabled=disabled,
                        use_container_width=True,
                    ):
                        set_viewed_po_variant_id(mode, scope, po_variant_id)
                        st.rerun()

            if is_selected:
                updated_selected_po_variant_ids.add(po_variant_id)
            else:
                updated_selected_po_variant_ids.discard(po_variant_id)

    if updated_selected_po_variant_ids != selected_po_variant_ids:
        set_selected_po_variant_ids(mode, scope, updated_selected_po_variant_ids)
        saved_po_variant_ids = get_saved_po_variant_ids(mode, scope) or set()
        changes_pending = updated_selected_po_variant_ids != saved_po_variant_ids
        set_po_variant_selection_changes_pending(mode, scope, changes_pending)
        if changes_pending:
            set_ui_message(
                "warning", "Please save changes before generating an XES file!"
            )
        else:
            st.session_state["ui_message"] = None
        st.rerun()

    return viewed_po_variant_id


def render_po_variant_selection_actions(mode, scope, po_variants, disabled=False):
    selected_po_variant_ids, _ = ensure_po_variant_selection(mode, scope, po_variants)
    po_variant_ids = _po_variant_ids(po_variants)
    changes_pending = get_po_variant_selection_changes_pending(mode, scope)

    with st.container(key=f"{mode}_{scope}_po_selection_actions"):
        select_all_column, save_column = st.columns(2, gap="small")

        with select_all_column:
            if st.button(
                "Select all",
                key=f"select_all_po_{mode}_{scope}",
                disabled=(
                    disabled
                    or not po_variant_ids
                    or selected_po_variant_ids == po_variant_ids
                ),
                use_container_width=True,
            ):
                set_selected_po_variant_ids(mode, scope, po_variant_ids)
                set_po_variant_selection_changes_pending(
                    mode,
                    scope,
                    po_variant_ids != (get_saved_po_variant_ids(mode, scope) or set()),
                )
                _clear_po_variant_selection_widgets(mode, scope)
                set_ui_message(
                    "warning", "Please save changes before generating an XES file!"
                )
                st.rerun()

        with save_column:
            if st.button(
                "Save",
                key=f"save_po_selection_{mode}_{scope}",
                disabled=disabled or not changes_pending,
                use_container_width=True,
            ):
                scope_key = make_scope_key(mode, scope)
                set_saved_po_variant_ids(mode, scope, selected_po_variant_ids)
                set_po_variant_selection_changes_pending(mode, scope, False)
                st.session_state["po_trace_downloads"].pop(scope_key, None)
                set_ui_message(
                    "success",
                    "PO variant selection saved. Generate an XES file to export it.",
                )
                st.rerun()


def write_uploaded_bytes_to_tempfile(file_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xes") as tmp_file:
        tmp_file.write(file_bytes)
        return tmp_file.name


def ensure_prepared(mode, scope, semantics):
    state = cco.get_state(mode, scope)
    if state.get("filog_base") is not None:
        cco.set_semantics(mode, scope, semantics)
        return state

    file_bytes = st.session_state["uploaded_file_bytes"]
    if file_bytes is None:
        raise ValueError("No uploaded log file available.")

    tmp_file_path = write_uploaded_bytes_to_tempfile(file_bytes)
    try:
        cco.prepare_log(
            tmp_file_path,
            mode,
            scope,
            semantics,
            source=st.session_state["uploaded_file_name"],
        )
    finally:
        os.remove(tmp_file_path)

    return cco.get_state(mode, scope)


def frozensets_to_concurrent(selected_pairs):
    concurrent = Concurrent()
    for pair in selected_pairs:
        items = list(pair)
        if len(items) == 1:
            concurrent.add_pair(items[0], items[0])
        elif len(items) == 2:
            concurrent.add_pair(items[0], items[1])
    return concurrent


def display_pair(pair):
    items = sorted(pair)
    if len(items) == 1:
        return items[0], items[0]
    return items[0], items[1]


def get_activity_options(mode, scope):
    state = cco.get_state(mode, scope)
    variants = state.get("vars") or {}
    activities = {
        activity
        for variant in variants.keys()
        for activity in variant
    }
    return sorted(activities)


def sort_po_traces(po_traces):
    return sorted(
        po_traces,
        key=lambda po: (
            -po.graph.get("multiplicity", 0),
            po.graph.get("id", 0),
        ),
    )


def get_concurrency_support(mode, scope, pair):
    state = cco.get_state(mode, scope)
    supports = state.get("concurrency_supports")
    if supports is None:
        return None
    return int(supports.get(pair, 0))


def get_alpha_direction_count(mode, scope, activity_a, activity_b):
    state = cco.get_state(mode, scope)
    direction_counts = state.get("concurrency_direction_counts")
    if direction_counts is None:
        return None
    return int(direction_counts.get((activity_a, activity_b), 0))


def set_ui_message(kind, text):
    st.session_state["ui_message"] = {"kind": kind, "text": text}


def prepare_xes_download(
    scope_key,
    filog_out,
    file_name,
    mode=None,
    scope=None,
    po_variant_ids=None,
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xes") as tmp_file:
        tmp_file_path = tmp_file.name

    try:
        cco.write_xes(
            filog_out,
            tmp_file_path,
            mode=mode,
            scope=scope,
            po_variant_ids=po_variant_ids,
        )
        with open(tmp_file_path, "rb") as f:
            st.session_state["po_trace_downloads"][scope_key] = {
                "bytes": f.read(),
                "file_name": file_name,
            }
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)


def render_xes_download_control(
    scope_key,
    filog_out,
    file_name,
    mode,
    scope,
    key_suffix,
    po_variant_ids,
    selection_changes_pending=False,
):
    download_payload = st.session_state["po_trace_downloads"].get(scope_key)

    if selection_changes_pending:
        st.button(
            "Download .xes" if download_payload else "Generate .xes",
            key=f"pending_download_po_{key_suffix}",
            disabled=True,
            use_container_width=True,
        )
        return

    if download_payload:
        st.download_button(
            label="Download .xes",
            data=download_payload["bytes"],
            file_name=download_payload["file_name"],
            mime="application/octet-stream",
            key=f"download_po_{key_suffix}",
            on_click="ignore",
            use_container_width=True,
        )
        return

    if filog_out is None or not po_variant_ids:
        st.button(
            "Generate .xes",
            key=f"prepare_download_po_{key_suffix}",
            disabled=True,
            use_container_width=True,
        )
        return

    if st.button("Generate .xes", key=f"prepare_download_po_{key_suffix}", use_container_width=True):
        try:
            prepare_xes_download(
                scope_key,
                filog_out,
                file_name,
                mode=mode,
                scope=scope,
                po_variant_ids=po_variant_ids,
            )
            set_ui_message("success", "XES file prepared. Click Download .xes to save it.")
            st.rerun()
        except Exception as e:
            set_ui_message("error", f"Error generating XES download: {e}")


def has_service_data():
    return any(
        state.get("filog_base") is not None
        or state.get("concurrencies") is not None
        or state.get("po_log") is not None
        or state.get("povariants") is not None
        for state in cco.state.values()
    )


def has_computed_data():
    if st.session_state["po_traces"]:
        return True
    if st.session_state["po_trace_downloads"]:
        return True
    if st.session_state.get("user_concurrencies"):
        return True
    if any(st.session_state.get(key) for key in st.session_state if key.startswith("cc_done_")):
        return True
    if has_service_data():
        return True
    return False


def clear_computed_state():
    global cco

    st.session_state["po_traces"] = {}
    st.session_state["po_trace_downloads"] = {}
    st.session_state["ui_message"] = None

    if "user_concurrencies" in st.session_state:
        del st.session_state["user_concurrencies"]

    if "detected_concurrencies" in st.session_state:
        del st.session_state["detected_concurrencies"]

    if "manually_added_concurrencies" in st.session_state:
        del st.session_state["manually_added_concurrencies"]

    if "pending_concurrency_changes" in st.session_state:
        del st.session_state["pending_concurrency_changes"]

    if "stale_po_results" in st.session_state:
        del st.session_state["stale_po_results"]

    if "selected_po_variant_ids" in st.session_state:
        del st.session_state["selected_po_variant_ids"]

    if "saved_po_variant_ids" in st.session_state:
        del st.session_state["saved_po_variant_ids"]

    if "pending_po_variant_selection_changes" in st.session_state:
        del st.session_state["pending_po_variant_selection_changes"]

    if "viewed_po_variant_ids" in st.session_state:
        del st.session_state["viewed_po_variant_ids"]

    for key in list(st.session_state.keys()):
        if key.startswith("cc_done_"):
            del st.session_state[key]
        elif key.startswith("po_radio_"):
            del st.session_state[key]
        elif key.startswith("po_variant_selected_"):
            del st.session_state[key]
        elif key.startswith("po_select_"):
            del st.session_state[key]
        elif key.startswith("download_po_"):
            del st.session_state[key]
        elif key.startswith("compute_po_"):
            del st.session_state[key]
        elif key.startswith("alpha-logwise-") or key.startswith("lifecycle-logwise-"):
            del st.session_state[key]

    st.session_state["cco_service"] = CCOService()
    cco = st.session_state["cco_service"]


def clear_pending_upload():
    st.session_state["pending_uploaded_file_name"] = None
    st.session_state["pending_uploaded_file_bytes"] = None


def accept_uploaded_file(file_name, file_bytes, clear_existing=False):
    if clear_existing:
        clear_computed_state()
    st.session_state["uploaded_file_name"] = file_name
    st.session_state["uploaded_file_bytes"] = file_bytes
    clear_pending_upload()


def render_ui_message(target=None):
    message = st.session_state.get("ui_message")
    html = ""
    if message:
        kind = escape(message["kind"])
        text = escape(message["text"])
        html = f'<div class="status-banner status-{kind}">{text}</div>'
    else:
        html = '<div class="status-banner status-empty">&nbsp;</div>'

    if target is None:
        st.markdown(html, unsafe_allow_html=True)
    else:
        target.markdown(html, unsafe_allow_html=True)


def render_pending_upload_prompt(target):
    with target.container():
        message_col, yes_col, no_col = st.columns([0.74, 0.13, 0.13], gap="small")

        with message_col:
            st.markdown(
                '<div class="status-banner status-warning">New .xes upload clears current results. Proceed?</div>',
                unsafe_allow_html=True,
            )

        with yes_col:
            if st.button("Yes", key="confirm_new_upload", use_container_width=True):
                accept_uploaded_file(
                    st.session_state["pending_uploaded_file_name"],
                    st.session_state["pending_uploaded_file_bytes"],
                    clear_existing=True,
                )
                st.rerun()

        with no_col:
            if st.button("No", key="cancel_new_upload", use_container_width=True):
                clear_pending_upload()
                st.session_state["upload_widget_nonce"] += 1
                st.rerun()


def _po_levels(po):
    layers = list(nx.topological_generations(po))
    if not layers:
        return {}

    for layer_idx, layer in enumerate(layers):
        for node in layer:
            po.nodes[node]["_level"] = layer_idx

    return {node: po.nodes[node]["_level"] for node in po.nodes()}


def _po_positions(po):
    layers = list(nx.topological_generations(po))
    if not layers:
        return {}

    x_spacing = 240
    y_spacing = 120
    top_margin = 80
    left_margin = 120
    positions = {}

    for layer_idx, layer in enumerate(layers):
        count = len(layer)
        total_height = (count - 1) * y_spacing
        start_y = top_margin - (total_height / 2)

        for node_idx, node in enumerate(layer):
            positions[node] = {
                "x": left_margin + (layer_idx * x_spacing),
                "y": start_y + (node_idx * y_spacing),
            }

    return positions


def render_interactive_po_graph(po, key):
    levels = _po_levels(po)
    positions = _po_positions(po)
    if not levels or not positions:
        return

    layer_sizes = {}
    for level in levels.values():
        layer_sizes[level] = layer_sizes.get(level, 0) + 1

    max_level = max(levels.values()) if levels else 0
    max_layer_size = max(layer_sizes.values()) if layer_sizes else 1
    height = max(
        1,
        min(
            GRAPH_VIEW_HEIGHT - GRAPH_VIEW_VARIANT_LABEL_HEIGHT,
            max(300, 150 + (max_layer_size * 110)),
        )
        - 4,
    )
    width = max(900, 260 + ((max_level + 1) * 240))

    net = Network(
        height=f"{height}px",
        width="100%",
        directed=True,
        notebook=False,
        cdn_resources="in_line",
    )

    for node in po.nodes():
        label = str(po.nodes[node].get("activity", node))
        net.add_node(
            n_id=str(node),
            label=label,
            title=label,
            shape="box",
            x=positions[node]["x"],
            y=positions[node]["y"],
        )

    for source, target in po.edges():
        net.add_edge(str(source), str(target), arrows="to")

    net.set_options(
        """
        {
          "interaction": {
            "dragNodes": true,
            "dragView": true,
            "zoomView": true,
            "hideEdgesOnDrag": false,
            "hideEdgesOnZoom": false,
            "navigationButtons": true,
            "selectable": true,
            "hover": true
          },
          "physics": {
            "enabled": false
          },
          "nodes": {
            "shape": "box",
            "font": {
              "size": 16
            },
            "margin": 10
          },
          "edges": {
            "smooth": false,
            "color": {
              "color": "#6b7280",
              "highlight": "#2563eb"
            }
          }
        }
        """
    )

    html = net.generate_html(notebook=False)
    html = html.replace("border: 1px solid lightgray;", "border: 0 !important;")
    html = html.replace(
        "</head>",
        "<style>html, body { margin: 0; padding: 0; overflow: hidden; } #mynetwork, #mynetwork > div, .vis-network { border: 0 !important; outline: 0 !important; box-shadow: none !important; border-radius: 0 !important; }</style></head>",
    )
    html = html.replace('style="width: 100%;"', f'style="width: {width}px;"')
    components.html(html, height=height, scrolling=False)


def render_viewed_po_variant_label(po_variant_id):
    st.markdown(
        f'<div class="viewed-po-variant-label">PO {escape(str(po_variant_id))}</div>',
        unsafe_allow_html=True,
    )
    st.container(height=GRAPH_VIEW_VARIANT_SPACER_HEIGHT, border=False)


def render_panel_boxes(scope, box_height, render_conc, render_po, render_graph, show_conc_box=True, conc_title="Concurrencies"):
    col_conc, col_po, col_graph = st.columns([2.145, 1.10, 3.755], gap="small")

    with col_conc:
        if show_conc_box:
            st.container(height=PANEL_BOX_TOP_GAP, border=False)
            with st.container(border=True, key=f"{scope}_conc", height=box_height):
                st.subheader(conc_title)
                render_conc()

    with col_po:
        st.container(height=PANEL_BOX_TOP_GAP, border=False)
        with st.container(border=True, key=f"{scope}_po", height=box_height):
            st.subheader("PO Variants")
            render_po()

    with col_graph:
        st.container(height=PANEL_BOX_TOP_GAP, border=False)
        with st.container(border=True, key=f"{scope}_graph", height=box_height):
            st.subheader("PO Trace Graph View")
            render_graph()


def render_po_ui(mode, scope, uploaded_file):
    po_list = sort_po_traces(
        st.session_state["po_traces"].get(make_scope_key(mode, scope), [])
    )
    scope_key = make_scope_key(mode, scope)
    if po_list:
        _, viewed_po_variant_id = ensure_po_variant_selection(mode, scope, po_list)
    else:
        viewed_po_variant_id = None

    def render_conc():
        st.markdown(
            '<div class="tracewise-concurrency-info">'
            "In tracewise scope, concurrent or unordered event pairs are detected independently "
            "for each trace or case, based on the actual observations and the selected extraction "
            "method. The resulting partially ordered trace variants are then grouped by isomorphs. "
            "The detected unordered event pairs are displayed "
            "for information only and cannot be edited."
            "</div>",
            unsafe_allow_html=True,
        )

        if po_list and viewed_po_variant_id is not None:
            viewed_po_variant = next(
                po for po in po_list if po.graph["id"] == viewed_po_variant_id
            )
            concurrencies = viewed_po_variant.graph.get("concurrencies")
            if concurrencies:
                conc_pairs_seen = set()
                conc_pairs = []
                for pair in concurrencies:
                    sorted_pair = tuple(sorted(pair))
                    if sorted_pair not in conc_pairs_seen:
                        conc_pairs_seen.add(sorted_pair)
                        conc_pairs.append(pair)

                conc_pairs.sort(key=lambda pair: display_pair(pair))

                with st.container(
                    height=TRACEWISE_CONCURRENCY_LIST_HEIGHT, border=False
                ):
                    for pair in conc_pairs:
                        a, b = display_pair(pair)
                        st.checkbox(
                            f"{a} ↔ {b}",
                            key=f"tracewise_conc_{mode}_{scope}_{viewed_po_variant_id}_{a}_{b}",
                            value=True,
                            disabled=True,
                        )
        else:
            st.write("")

    def render_po():
        nonlocal viewed_po_variant_id, po_list
        if uploaded_file:
            with st.container(key=f"{mode}_{scope}_po_actions"):
                if st.button(
                    "Compute PO Traces",
                    key=f"compute_po_{mode}_{scope}",
                    disabled=cco.get_state(mode, scope).get("po_log") is not None,
                    use_container_width=True,
                ):
                    try:
                        ensure_prepared(mode, scope, semantics)
                        filog_out, povariants = cco.compute_po_traces(mode, scope, stats_only=False)
                        povariants = sort_po_traces(povariants)
                        st.session_state["po_traces"][scope_key] = povariants
                        po_list = povariants
                        reset_po_variant_selection(mode, scope, povariants)
                        set_ui_message("success", f"PO Traces successfully computed! Number of traces: {len(povariants)}")
                        st.rerun()
                    except Exception as e:
                        set_ui_message("error", f"Error computing PO traces (tracewise): {e}")

                download_state = cco.get_state(mode, scope)
                saved_po_variant_ids = get_saved_po_variant_ids(mode, scope) or set()
                render_xes_download_control(
                    scope_key,
                    download_state.get("po_log"),
                    "po_traces_tracewise.xes",
                    mode=mode,
                    scope=scope,
                    key_suffix=f"{mode}_{scope}",
                    po_variant_ids=saved_po_variant_ids,
                    selection_changes_pending=get_po_variant_selection_changes_pending(
                        mode, scope
                    ),
                )
                render_po_variant_selection_actions(mode, scope, po_list)

        if po_list:
            render_po_variant_summary(mode, scope, po_list)
            viewed_po_variant_id = render_po_variant_list(mode, scope, po_list)
        else:
            st.write("")

    def render_graph():
        if po_list and viewed_po_variant_id is not None:
            viewed_po_variant = next(
                po for po in po_list if po.graph["id"] == viewed_po_variant_id
            )
            render_viewed_po_variant_label(viewed_po_variant_id)
            render_interactive_po_graph(
                viewed_po_variant,
                f"{mode}_{scope}_{viewed_po_variant_id}",
            )

    render_panel_boxes(
        scope,
        TRACEWISE_BOX_HEIGHT,
        render_conc,
        render_po,
        render_graph,
        conc_title="Unordered Event Pairs (selected trace)",
    )


def render_logwise_content(mode, uploaded_file):
    state = cco.get_state(mode, "logwise")
    scope_key = make_scope_key(mode, "logwise")
    po_list = sort_po_traces(st.session_state["po_traces"].get(scope_key, []))
    po_results_stale = get_po_results_stale(mode)
    if po_list:
        _, viewed_po_variant_id = ensure_po_variant_selection(
            mode, "logwise", po_list
        )
    else:
        viewed_po_variant_id = None

    def render_conc():
        nonlocal state
        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

        if uploaded_file:
            with st.container(key=f"{mode}_logwise_conc_detect_action"):
                detect_column, save_column = st.columns(2, gap="small")
                with detect_column:
                    if st.button(
                        "Apply Extraction Method",
                        disabled=st.session_state.get(f"cc_done_{mode}_logwise", False),
                        use_container_width=True,
                    ):
                        try:
                            ensure_prepared(mode, "logwise", semantics)
                            detected = cco.detect_concurrencies(mode, "logwise")
                            state = cco.get_state(mode, "logwise")

                            scope_key = make_scope_key(mode, "logwise")
                            detected_pairs = {
                                frozenset(pair) for pair in detected.to_tuples()
                            }
                            set_detected_concurrency_pairs(mode, "logwise", detected_pairs)
                            set_manually_added_concurrency_pairs(mode, "logwise", set())
                            set_user_concurrency_pairs(mode, "logwise", set(detected_pairs))
                            set_logwise_changes_pending(mode, False)
                            set_po_results_stale(mode, False)

                            st.session_state[f"cc_done_{mode}_logwise"] = True

                            if len(list(detected)) > 0:
                                set_ui_message("success", "Concurrencies successfully computed!")
                            else:
                                set_ui_message("info", "No concurrencies were detected for your parameter selection.")

                            st.rerun()
                        except Exception as e:
                            set_ui_message("error", f"Error computing concurrencies: {e}")

                with save_column:
                    if st.button(
                        "Save Changes",
                        disabled=not get_logwise_changes_pending(mode),
                        use_container_width=True,
                    ):
                        selected_concurrencies = st.session_state.get(
                            "user_concurrencies", {}
                        ).get(scope_key, set())
                        edited_concurrent = frozensets_to_concurrent(
                            selected_concurrencies
                        )
                        try:
                            cco.set_concurrencies(mode, "logwise", edited_concurrent)
                            st.session_state["po_trace_downloads"].pop(scope_key, None)
                            set_logwise_changes_pending(mode, False)
                            set_po_results_stale(mode, True)
                            set_ui_message(
                                "info",
                                "Changes saved. Please recompute the partially ordered trace variants!",
                            )
                            st.rerun()
                        except Exception as e:
                            set_ui_message("error", f"Error saving concurrencies: {e}")

        scope_key = make_scope_key(mode, "logwise")
        detected_pairs = get_detected_concurrency_pairs(mode, "logwise")

        if detected_pairs is not None:
            if "user_concurrencies" not in st.session_state:
                st.session_state["user_concurrencies"] = {}

            if scope_key not in st.session_state["user_concurrencies"]:
                set_user_concurrency_pairs(mode, "logwise", set(detected_pairs))

            user_conc = st.session_state["user_concurrencies"][scope_key]

            activity_options = get_activity_options(mode, "logwise")
            with st.container(key=f"{mode}_logwise_conc_add_action"):
                if activity_options:
                    add_col_a, add_col_arrow, add_col_b, add_col_button = st.columns([1.07, 0.12, 1.07, 0.51], gap="small")

                    with add_col_a:
                        activity_a = st.selectbox(
                            "Activity A",
                            options=activity_options,
                            key=f"add_concurrency_a_{mode}_logwise",
                            label_visibility="collapsed",
                        )

                    with add_col_arrow:
                        st.markdown(
                            '<div class="add-concurrency-arrow">↔</div>',
                            unsafe_allow_html=True,
                        )

                    with add_col_b:
                        activity_b = st.selectbox(
                            "Activity B",
                            options=activity_options,
                            key=f"add_concurrency_b_{mode}_logwise",
                            label_visibility="collapsed",
                        )

                    with add_col_button:
                        if st.button("Add", key=f"add_concurrency_{mode}_logwise", use_container_width=True):
                            pair_to_add = frozenset([activity_a, activity_b])
                            if pair_to_add in detected_pairs:
                                set_ui_message("warning", "This concurrency already exists!")
                            else:
                                detected_pairs = set(detected_pairs)
                                user_conc = set(user_conc)
                                detected_pairs.add(pair_to_add)
                                user_conc.add(pair_to_add)
                                set_detected_concurrency_pairs(mode, "logwise", detected_pairs)
                                manually_added_pairs = get_manually_added_concurrency_pairs(
                                    mode, "logwise"
                                )
                                manually_added_pairs = set(manually_added_pairs)
                                manually_added_pairs.add(pair_to_add)
                                set_manually_added_concurrency_pairs(
                                    mode, "logwise", manually_added_pairs
                                )
                                set_user_concurrency_pairs(mode, "logwise", user_conc)
                                set_ui_message("success", "Concurrency added. Save changes to apply.")

            with st.container(key=f"{mode}_logwise_conc_save_action"):
                save_column, save_spacer = st.columns(2, gap="small")
                with save_column:
                    st.button(
                        "Save Changes",
                        key=f"save_changes_placeholder_{mode}_logwise",
                        disabled=True,
                        use_container_width=True,
                    )

            with st.container(key="logwise_concurrency_results"):
                manually_added_pairs = get_manually_added_concurrency_pairs(mode, "logwise")
                automatically_detected = len(detected_pairs - manually_added_pairs)
                manually_added = len(detected_pairs & manually_added_pairs)
                render_concurrency_summary(automatically_detected, manually_added)

                if len(detected_pairs) > 0:
                    conc_pairs = sorted(
                        detected_pairs,
                        key=lambda pair: (
                            -(get_concurrency_support(mode, "logwise", pair) or 0),
                            str(display_pair(pair)[0]),
                            str(display_pair(pair)[1]),
                        ),
                    )
                    list_top_spacer = round(8 * UI_SCALE)
                    st.container(height=list_top_spacer, border=False)

                    with st.container(
                            height=(
                                    LOGWISE_CONCURRENCY_LIST_HEIGHT - list_top_spacer
                            ),
                            border=False,
                    ):
                        previous_pair_was_automatic = False
                        for pair_index, pair in enumerate(conc_pairs):
                            a, b = display_pair(pair)
                            key = f"{mode}-logwise-{a}-{b}"
                            support_container_key = (
                                f"concurrency_support_item_{mode}_{pair_index}"
                            )

                            pair_set = frozenset([a, b])
                            pair_was_manually_added = (
                                pair_set in manually_added_pairs
                            )
                            if (
                                pair_was_manually_added
                                and previous_pair_was_automatic
                            ):
                                st.container(
                                    height=round(10 * UI_SCALE), border=False
                                )
                            support = get_concurrency_support(
                                mode, "logwise", pair_set
                            )
                            label = f"{a} ↔ {b}"
                            annotation = None
                            if pair_was_manually_added:
                                annotation = "(manually added)"
                            elif support is not None:
                                annotation = f"(support: {support})"

                            show_alpha_direction_counts = (
                                mode == "alpha"
                                and support is not None
                                and pair_set not in manually_added_pairs
                            )
                            with st.container(key=support_container_key):
                                if annotation is not None:
                                    st.markdown(
                                        f"""
                                        <style>
                                        .st-key-{support_container_key}
                                        div[data-testid="stCheckbox"] label p::after {{
                                            content: "   {annotation}";
                                            color: #9ca3af !important;
                                            font-size: 1rem !important;
                                            font-weight: 400 !important;
                                        }}
                                        </style>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                                if show_alpha_direction_counts:
                                    with st.container(
                                        key=(
                                            f"alpha_concurrency_item_{mode}_"
                                            f"{pair_index}"
                                        )
                                    ):
                                        selected = st.checkbox(
                                            label,
                                            key=key,
                                            value=(pair_set in user_conc),
                                        )

                                        a_to_b = get_alpha_direction_count(
                                            mode, "logwise", a, b
                                        )
                                        b_to_a = get_alpha_direction_count(
                                            mode, "logwise", b, a
                                        )
                                        st.markdown(
                                            '<div class="alpha-direction-counts">'
                                            f"{escape(str(a))} → {escape(str(b))}: "
                                            f"{a_to_b} times<br>"
                                            f"{escape(str(b))} → {escape(str(a))}: "
                                            f"{b_to_a} times"
                                            "</div>",
                                            unsafe_allow_html=True,
                                        )
                                        st.markdown(
                                            '<div class="alpha-concurrency-item-spacer"></div>',
                                            unsafe_allow_html=True,
                                        )
                                else:
                                    selected = st.checkbox(
                                        label,
                                        key=key,
                                        value=(pair_set in user_conc),
                                    )

                            if selected:
                                user_conc.add(pair_set)
                            else:
                                user_conc.discard(pair_set)

                            previous_pair_was_automatic = (
                                not pair_was_manually_added
                            )

                    set_user_concurrency_pairs(mode, "logwise", user_conc)
                    updated_changes_pending, pending_state_changed = update_logwise_changes_pending(mode)
                    if pending_state_changed:
                        if updated_changes_pending:
                            set_ui_message(
                                "warning",
                                "Please save changes and recompute the partially ordered trace variants!",
                            )
                        else:
                            st.session_state["ui_message"] = None
                        st.rerun()

    def render_po():
        nonlocal viewed_po_variant_id, po_list
        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
        if uploaded_file:
            state = cco.get_state(mode, "logwise")
            with st.container(key=f"{mode}_logwise_po_actions"):
                if st.button(
                    "Compute PO Traces",
                    disabled=(
                        state.get("concurrencies") is None
                        or get_logwise_changes_pending(mode)
                        or state.get("po_log") is not None
                    ),
                    use_container_width=True,
                ):
                    try:
                        filog_out, povariants = cco.compute_po_traces(mode, "logwise", stats_only=False)
                        povariants = sort_po_traces(povariants)
                        st.session_state["po_traces"][scope_key] = povariants
                        po_list = povariants
                        reset_po_variant_selection(mode, "logwise", povariants)
                        set_po_results_stale(mode, False)
                        set_ui_message("success", f"PO Traces computed: {len(povariants)}")
                        st.rerun()
                    except Exception as e:
                        set_ui_message("error", f"Error computing PO traces (logwise): {e}")

                download_state = cco.get_state(mode, "logwise")
                saved_po_variant_ids = (
                    get_saved_po_variant_ids(mode, "logwise") or set()
                )
                render_xes_download_control(
                    scope_key,
                    download_state.get("po_log"),
                    "po_traces_logwise.xes",
                    mode=mode,
                    scope="logwise",
                    key_suffix=f"{mode}_logwise",
                    po_variant_ids=saved_po_variant_ids,
                    selection_changes_pending=get_po_variant_selection_changes_pending(
                        mode, "logwise"
                    ),
                )
                render_po_variant_selection_actions(
                    mode,
                    "logwise",
                    po_list,
                    disabled=po_results_stale,
                )

        if po_list:
            render_po_variant_summary(mode, "logwise", po_list)
            container_key = (
                "logwise_po_results_stale"
                if po_results_stale
                else "logwise_po_results"
            )
            with st.container(key=container_key):
                viewed_po_variant_id = render_po_variant_list(
                    mode,
                    "logwise",
                    po_list,
                    disabled=po_results_stale,
                )
        else:
            viewed_po_variant_id = None

    def render_graph():
        if po_list and viewed_po_variant_id is not None:
            viewed_po_variant = next(
                po for po in po_list if po.graph["id"] == viewed_po_variant_id
            )
            container_key = "logwise_graph_results_stale" if po_results_stale else "logwise_graph_results"
            with st.container(key=container_key):
                render_viewed_po_variant_label(viewed_po_variant_id)
                render_interactive_po_graph(
                    viewed_po_variant,
                    f"{mode}_logwise_{viewed_po_variant_id}",
                )

    render_panel_boxes(
        "logwise",
        LOGWISE_BOX_HEIGHT,
        render_conc,
        render_po,
        render_graph,
        conc_title="Unordered Activity Pairs (entire log)",
    )


def render_tracewise_content(mode, uploaded_file):
    render_po_ui(mode, "tracewise", uploaded_file)


# Upload + Semantics + Mode
top_upload, top_semantics, top_mode, top_status = st.columns([1.5, 0.75, 0.75, 3])

with top_upload:
    uploaded_file = st.file_uploader(
        "Upload Logfile",
        type=["xes"],
        key=f"upload_log_file_{st.session_state['upload_widget_nonce']}",
    )

with top_semantics:
    semantics = st.selectbox(
        "Select Semantics",
        ["certain", "uncertain"],
        index=0,
        label_visibility="visible",
    )

with top_mode:
    # Timestamp modes are available for both logwise and tracewise detection.
    timestamp_modes = [
        "same_hour",
        "same_minute",
        "same_second",
        "same_timestamp",
    ]
    if semantics == "uncertain":
        available_modes = timestamp_modes
    else:
        available_modes = ["alpha", "lifecycle"] + timestamp_modes

    if st.session_state.get("selected_detection_mode") not in available_modes:
        st.session_state["selected_detection_mode"] = available_modes[0]

    mode = st.selectbox(
        "Select Extraction Method",
        available_modes,
        key="selected_detection_mode",
        label_visibility="visible",
    )

with top_status:
    st.markdown('<div class="top-status-label">Message</div>', unsafe_allow_html=True)
    status_placeholder = st.empty()

if uploaded_file is not None:
    current_bytes = uploaded_file.getvalue()
    current_name = uploaded_file.name
    if (
        st.session_state["uploaded_file_name"] != current_name
        or st.session_state["uploaded_file_bytes"] != current_bytes
    ):
        replacing_existing_file = st.session_state["uploaded_file_bytes"] is not None
        if replacing_existing_file and has_computed_data():
            st.session_state["pending_uploaded_file_name"] = current_name
            st.session_state["pending_uploaded_file_bytes"] = current_bytes
        else:
            accept_uploaded_file(
                current_name,
                current_bytes,
                clear_existing=replacing_existing_file,
            )

# ---------------- STABLE 4 MODE SWITCH ----------------
if "last_mode" not in st.session_state:
    st.session_state["last_mode"] = mode

if st.session_state["last_mode"] != mode:
    st.session_state["last_mode"] = mode
    st.rerun()

if "active_scope" not in st.session_state:
    st.session_state["active_scope"] = "logwise"

tab_logwise_bg = "#ffffff" if st.session_state["active_scope"] == "logwise" else "#f0f2f6"
tab_tracewise_bg = "#ffffff" if st.session_state["active_scope"] == "tracewise" else "#f0f2f6"
tab_logwise_bottom = "#ffffff" if st.session_state["active_scope"] == "logwise" else "#000000"
tab_tracewise_bottom = "#ffffff" if st.session_state["active_scope"] == "tracewise" else "#000000"
tab_logwise_color = "#111827" if st.session_state["active_scope"] == "logwise" else "#9ca3af"
tab_tracewise_color = "#111827" if st.session_state["active_scope"] == "tracewise" else "#9ca3af"

st.markdown(
    f"""
    <style>
    .st-key-tab_btn_logwise button,
    .st-key-tab_btn_tracewise button {{
        width: 100%;
        min-height: 3.35rem !important;
        height: 3.35rem !important;
        max-height: 3.35rem !important;
        border: 1px solid #000000 !important;
        border-radius: 0.7rem 0.7rem 0 0 !important;
        box-shadow: none !important;
        font-weight: 500 !important;
        font-size: 2rem !important;
        margin: 0 !important;
        position: relative;
    }}
    .st-key-tab_btn_logwise button p,
    .st-key-tab_btn_tracewise button p,
    .st-key-tab_btn_logwise button div[data-testid="stMarkdownContainer"] p,
    .st-key-tab_btn_tracewise button div[data-testid="stMarkdownContainer"] p {{
        font-size: 2rem !important;
        line-height: 1.1 !important;
        font-weight: 500 !important;
    }}
    .st-key-tab_btn_logwise button {{
        background: {tab_logwise_bg} !important;
        border-bottom-color: {tab_logwise_bottom} !important;
        color: {tab_logwise_color} !important;
        margin-bottom: -1px !important;
        z-index: {2 if st.session_state["active_scope"] == "logwise" else 1};
    }}
    .st-key-tab_btn_tracewise button {{
        background: {tab_tracewise_bg} !important;
        border-bottom-color: {tab_tracewise_bottom} !important;
        color: {tab_tracewise_color} !important;
        margin-bottom: -1px !important;
        z-index: {2 if st.session_state["active_scope"] == "tracewise" else 1};
    }}
    .st-key-tab_btn_logwise button p,
    .st-key-tab_btn_logwise button div[data-testid="stMarkdownContainer"] p {{
        color: {tab_logwise_color} !important;
    }}
    .st-key-tab_btn_tracewise button p,
    .st-key-tab_btn_tracewise button div[data-testid="stMarkdownContainer"] p {{
        color: {tab_tracewise_color} !important;
    }}
    .st-key-tab_btn_logwise button:focus,
    .st-key-tab_btn_logwise button:focus-visible,
    .st-key-tab_btn_tracewise button:focus,
    .st-key-tab_btn_tracewise button:focus-visible {{
        outline: none !important;
        box-shadow: none !important;
    }}
    .st-key-tab_bar {{
        margin-bottom: 0 !important;
    }}
    .st-key-tab_shell,
    .st-key-tab_shell > div,
    .st-key-tab_shell div[data-testid="stVerticalBlock"],
    .st-key-tab_shell .element-container {{
        gap: 0 !important;
        row-gap: 0 !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }}
    .st-key-tab_shell div[data-testid="stElementContainer"] {{
        margin-bottom: 0 !important;
    }}
    .st-key-tab_bar > div,
    .st-key-tab_bar div[data-testid="stVerticalBlock"],
    .st-key-tab_bar div[data-testid="stHorizontalBlock"],
    .st-key-tab_bar div[data-testid="column"],
    .st-key-tab_bar div[data-testid="stElementContainer"],
    .st-key-tab_bar .stButton,
    .st-key-tab_bar .element-container {{
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
    }}
    .st-key-tab_bar div[data-testid="stHorizontalBlock"] {{
        gap: 0 !important;
    }}
    .st-key-tab_bar div[data-testid="column"] {{
        padding-left: 0 !important;
        padding-right: 0 !important;
    }}
    .st-key-active_panel {{
        border-left: 1px solid #000000 !important;
        border-right: 1px solid #000000 !important;
        border-bottom: 1px solid #000000 !important;
        border-top: 0 !important;
        border-radius: 0 !important;
        background: #ffffff !important;
        margin-top: -1px !important;
        position: relative !important;
        top: 0 !important;
        overflow: visible !important;
        box-shadow: none !important;
        padding: 0 !important;
    }}
    .st-key-active_panel div[data-testid="stVerticalBlockBorderWrapper"] {{
        border: 0 !important;
        border-radius: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
        margin-top: 0 !important;
        padding: 0 !important;
    }}
    .st-key-active_panel > div,
    .st-key-active_panel > div > div[data-testid="stVerticalBlock"],
    .st-key-active_panel div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        background: transparent !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        position: relative !important;
        z-index: 1 !important;
        min-height: 0 !important;
    }}
    .st-key-active_panel_inner,
    .st-key-active_panel_inner > div,
    .st-key-active_panel_inner > div > div[data-testid="stVerticalBlock"] {{
        height: 100% !important;
        min-height: 0 !important;
    }}
    .st-key-active_panel_inner > div > div[data-testid="stVerticalBlock"] {{
        padding: 0.45rem !important;
        box-sizing: border-box !important;
    }}
    .st-key-logwise_conc div[data-testid="stVerticalBlockBorderWrapper"],
    .st-key-logwise_po div[data-testid="stVerticalBlockBorderWrapper"],
    .st-key-logwise_graph div[data-testid="stVerticalBlockBorderWrapper"],
    .st-key-tracewise_conc div[data-testid="stVerticalBlockBorderWrapper"],
    .st-key-tracewise_po div[data-testid="stVerticalBlockBorderWrapper"],
    .st-key-tracewise_graph div[data-testid="stVerticalBlockBorderWrapper"] {{
        border: 0 !important;
        border-radius: 0.7rem !important;
        background: #ffffff !important;
        box-shadow: inset 0 0 0 1px #d1d5db !important;
    }}
    .st-key-logwise_graph div[data-testid="stVerticalBlockBorderWrapper"],
    .st-key-tracewise_graph div[data-testid="stVerticalBlockBorderWrapper"] {{
        box-sizing: border-box !important;
        overflow: hidden !important;
    }}
    .st-key-logwise_po_results_stale,
    .st-key-logwise_graph_results_stale {{
        opacity: 0.42;
        pointer-events: none;
    }}
    .stButton > button:not(:disabled),
    .stDownloadButton > button:not(:disabled) {{
        border-color: #000000 !important;
    }}
    .stButton > button:disabled,
    .stDownloadButton > button:disabled {{
        border-color: #d1d5db !important;
    }}
    .st-key-tab_btn_logwise .stButton > button:not(:disabled),
    .st-key-tab_btn_logwise button:not(:disabled) {{
        border-bottom-color: {tab_logwise_bottom} !important;
    }}
    .st-key-tab_btn_tracewise .stButton > button:not(:disabled),
    .st-key-tab_btn_tracewise button:not(:disabled) {{
        border-bottom-color: {tab_tracewise_bottom} !important;
    }}
    .count-summary {{
        color: #9ca3af;
        margin: calc(3mm * var(--ui-scale)) 0;
    }}
    .alpha-direction-counts {{
        color: #9ca3af;
        font-size: 0.85rem;
        line-height: 1.35;
        margin: 0;
    }}
    [class*="st-key-alpha_concurrency_item_"] .alpha-direction-counts {{
        margin: -0.73rem 0 0 1.75rem !important;
    }}
    .alpha-concurrency-item-spacer {{
        display: block;
        height: 1.7rem;
    }}
    .tracewise-concurrency-info {{
        color: #9ca3af;
        margin: 0 0 calc(3mm * var(--ui-scale));
        line-height: 1.35;
    }}
    .app-footer {{
        color: #000000;
        font-size: 0.85rem;
        text-align: right;
        margin-top: 0.65rem;
    }}
    .app-footer a {{
        color: #000000;
        text-decoration: underline;
    }}
    .st-key-tracewise_conc h3 {{
        color: #9ca3af !important;
    }}
    .st-key-logwise_conc h3,
    .st-key-logwise_po h3,
    .st-key-logwise_graph h3,
    .st-key-tracewise_conc h3,
    .st-key-tracewise_po h3,
    .st-key-tracewise_graph h3 {{
        margin-bottom: 0.9rem !important;
    }}
    .st-key-logwise_conc .stButton,
    .st-key-logwise_po .stButton,
    .st-key-logwise_po .stDownloadButton,
    .st-key-tracewise_po .stButton,
    .st-key-tracewise_po .stDownloadButton {{
        margin-bottom: 1.175rem !important;
    }}
    [class*="po_actions"] .stButton,
    [class*="po_actions"] .stDownloadButton {{
        margin-bottom: 0.35rem !important;
    }}
    [class*="conc_detect_action"] .stButton,
    [class*="conc_add_action"] .stButton {{
        margin-bottom: 0.35rem !important;
    }}
    [class*="po_selection_actions"] .stButton {{
        margin-bottom: 0 !important;
    }}
    [class*="conc_save_action"] .stButton {{
        margin-bottom: 0 !important;
    }}
    [class*="conc_save_action"] .stButton > button {{
        visibility: hidden;
    }}
    .st-key-logwise_conc .stButton > button,
    .st-key-logwise_po .stButton > button,
    .st-key-logwise_po .stDownloadButton > button,
    .st-key-tracewise_po .stButton > button,
    .st-key-tracewise_po .stDownloadButton > button {{
        min-height: 1.9rem !important;
        height: 1.9rem !important;
        max-height: 1.9rem !important;
        line-height: 1.2 !important;
        padding-top: 0.35rem !important;
        padding-bottom: 0.35rem !important;
    }}
    .st-key-logwise_conc .stButton > button {{
        font-size: 1rem !important;
    }}
    .st-key-logwise_po .stButton > button,
    .st-key-logwise_po .stDownloadButton > button,
    .st-key-tracewise_po .stButton > button,
    .st-key-tracewise_po .stDownloadButton > button {{
        font-size: 1rem !important;
        min-height: 1.9rem !important;
        height: 1.9rem !important;
        max-height: 1.9rem !important;
        width: 100% !important;
    }}
    .st-key-logwise_conc .stButton > button p,
    .st-key-logwise_po .stButton > button p,
    .st-key-logwise_po .stDownloadButton > button p,
    .st-key-tracewise_po .stButton > button p,
    .st-key-tracewise_po .stDownloadButton > button p,
    .st-key-logwise_conc .stButton > button div[data-testid="stMarkdownContainer"] p,
    .st-key-logwise_po .stButton > button div[data-testid="stMarkdownContainer"] p,
    .st-key-logwise_po .stDownloadButton > button div[data-testid="stMarkdownContainer"] p,
    .st-key-tracewise_po .stButton > button div[data-testid="stMarkdownContainer"] p,
    .st-key-tracewise_po .stDownloadButton > button div[data-testid="stMarkdownContainer"] p {{
        font-size: 1rem !important;
        line-height: 1.05 !important;
    }}
    [class*="po_selection_actions"] .stButton > button {{
        min-height: 1.9rem !important;
        height: 1.9rem !important;
        max-height: 1.9rem !important;
    }}
    [class*="st-key-po_variant_view_"] .stButton {{
        margin-bottom: calc(0.42rem - 2mm) !important;
    }}
    .st-key-logwise_po div[data-testid="stCheckbox"],
    .st-key-tracewise_po div[data-testid="stCheckbox"] {{
        margin-bottom: calc(0.42rem - 2mm) !important;
    }}
    [class*="st-key-po_variant_view_"] .stButton > button {{
        min-height: 1.55rem !important;
        height: 1.55rem !important;
        max-height: 1.55rem !important;
        padding: 0.1rem 0.25rem !important;
        font-size: 0.7rem !important;
        line-height: 1 !important;
    }}
    [class*="st-key-po_variant_view_"] .stButton > button p,
    [class*="st-key-po_variant_view_"] .stButton > button div[data-testid="stMarkdownContainer"] p {{
        font-size: 0.7rem !important;
        line-height: 1 !important;
    }}
    [class*="po_variant_view_container"] {{
        transform: translate(-2mm, 0.5mm);
    }}
    [class*="po_variant_view_container_active"] .stButton > button:not(:disabled) {{
        background-color: #16a34a !important;
        border-color: #16a34a !important;
        color: #ffffff !important;
    }}
    [class*="po_variant_view_container_active"] .stButton > button:not(:disabled) p,
    [class*="po_variant_view_container_active"] .stButton > button:not(:disabled) div[data-testid="stMarkdownContainer"] p {{
        color: #ffffff !important;
    }}
    .viewed-po-variant-label {{
        height: 1.8rem;
        box-sizing: border-box;
        display: flex;
        align-items: center;
        position: relative;
        z-index: 1;
        background: #ffffff;
        color: #16a34a;
        font-size: 1.18rem;
        font-weight: 600;
        line-height: 1.2;
        margin: 0 0 0.25rem;
    }}
    div[data-testid="stCheckbox"] {{
        margin-bottom: 0.42rem !important;
    }}
    div[data-testid="stCheckbox"] label {{
        align-items: center !important;
    }}
    div[data-testid="stCheckbox"] input[type="checkbox"],
    div[role="radiogroup"] input[type="radio"] {{
        accent-color: #16a34a !important;
    }}
    div[data-testid="stCheckbox"] [data-checked="true"],
    div[role="radiogroup"] [data-checked="true"] {{
        background-color: #16a34a !important;
        border-color: #16a34a !important;
    }}
    div[data-testid="stCheckbox"] svg,
    div[role="radiogroup"] svg {{
        fill: #16a34a !important;
    }}
    div[role="radiogroup"] > label {{
        padding-top: 0.3rem !important;
        padding-bottom: 0.3rem !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container(key="tab_shell"):
    with st.container(key="tab_bar"):
        tab_col_1, tab_col_2 = st.columns(2, gap="small")

        with tab_col_1:
            if st.button(
                "Logwise Scope",
                key="tab_btn_logwise",
                use_container_width=True,
            ):
                if st.session_state["active_scope"] != "logwise":
                    st.session_state["active_scope"] = "logwise"
                    st.rerun()

        with tab_col_2:
            if st.button("Tracewise Scope", key="tab_btn_tracewise", use_container_width=True):
                if st.session_state["active_scope"] != "tracewise":
                    st.session_state["active_scope"] = "tracewise"
                    st.rerun()

    with st.container(key="active_panel", height=TAB_PANEL_HEIGHT):
        with st.container(key="active_panel_inner", height=TAB_PANEL_HEIGHT):
            has_active_upload = st.session_state["uploaded_file_bytes"] is not None
            if st.session_state["active_scope"] == "logwise":
                render_logwise_content(mode, has_active_upload)
            else:
                render_tracewise_content(mode, has_active_upload)

st.markdown(
    '<div class="app-footer">'
    "Current version: 1.0 - Sabine Folz-Weinstein, Fakultät M+I, "
    'Fernuniversität in Hagen, <a href="https://www.fernuni-hagen.de/service/impressum.shtml" '
    'target="_blank">Impressum</a>'
    "</div>",
    unsafe_allow_html=True,
)

if st.session_state["pending_uploaded_file_bytes"] is not None:
    render_pending_upload_prompt(status_placeholder)
else:
    render_ui_message(status_placeholder)
