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

TAB_PANEL_HEIGHT = 610
PANEL_BOX_TOP_GAP = 18
LOGWISE_BOX_HEIGHT = TAB_PANEL_HEIGHT - 24 - PANEL_BOX_TOP_GAP
TRACEWISE_BOX_HEIGHT = LOGWISE_BOX_HEIGHT

# ONLY VISUAL FIX
st.set_page_config(layout="wide")
st.markdown(
    """
    <style>
    :root {
        --app-height: 100vh;
        --panel-height: calc(var(--app-height) - 9.6rem);
        --column-height: calc(var(--panel-height) - 1.35rem);
        --tab-border-color: #000000;
        --tab-border-width: 1px;
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
        margin-bottom: 0.2rem;
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
        min-height: 3.35rem;
        height: 3.35rem;
    }
    div[data-testid="stFileUploaderDropzone"] {
        min-height: 3.45rem;
        height: 3.45rem;
        padding-top: 0.35rem;
        padding-bottom: 0.35rem;
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
    </style>
    """,
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

st.title("CCO Interface")

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


def set_user_concurrency_pairs(mode, scope, user_pairs):
    scope_key = make_scope_key(mode, scope)
    set_nested_session_value("user_concurrencies", scope_key, user_pairs)


def write_uploaded_bytes_to_tempfile(file_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xes") as tmp_file:
        tmp_file.write(file_bytes)
        return tmp_file.name


def ensure_prepared(mode, scope):
    state = cco.get_state(mode, scope)
    if state.get("filog_base") is not None:
        return state

    file_bytes = st.session_state["uploaded_file_bytes"]
    if file_bytes is None:
        raise ValueError("No uploaded log file available.")

    tmp_file_path = write_uploaded_bytes_to_tempfile(file_bytes)
    try:
        cco.prepare_log(tmp_file_path, mode, scope)
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


def set_ui_message(kind, text):
    st.session_state["ui_message"] = {"kind": kind, "text": text}


def set_po_trace_download(scope_key, filog_out, file_name, mode=None, scope=None):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xes") as tmp_file:
        tmp_file_path = tmp_file.name

    try:
        cco.write_xes(filog_out, tmp_file_path, mode=mode, scope=scope)
        with open(tmp_file_path, "rb") as f:
            st.session_state["po_trace_downloads"][scope_key] = {
                "bytes": f.read(),
                "file_name": file_name,
            }
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)


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

    for key in list(st.session_state.keys()):
        if key.startswith("cc_done_"):
            del st.session_state[key]
        elif key.startswith("po_radio_"):
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
    height = max(420, 150 + (max_layer_size * 110))
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
    html = html.replace('style="width: 100%;"', f'style="width: {width}px;"')
    components.html(html, height=height + 20, scrolling=True)


def render_panel_boxes(scope, box_height, render_conc, render_po, render_graph, show_conc_box=True):
    col_conc, col_po, col_graph = st.columns([1.5, 1.05, 4.45], gap="small")

    with col_conc:
        if show_conc_box:
            st.container(height=PANEL_BOX_TOP_GAP, border=False)
            with st.container(border=True, key=f"{scope}_conc", height=box_height):
                st.subheader("Concurrencies")
                render_conc()

    with col_po:
        st.container(height=PANEL_BOX_TOP_GAP, border=False)
        with st.container(border=True, key=f"{scope}_po", height=box_height):
            st.subheader("PO Traces")
            render_po()

    with col_graph:
        st.container(height=PANEL_BOX_TOP_GAP, border=False)
        with st.container(border=True, key=f"{scope}_graph", height=box_height):
            st.subheader("Graph View")
            render_graph()


def render_po_ui(mode, scope, uploaded_file):
    po_list = st.session_state["po_traces"].get(make_scope_key(mode, scope), [])
    scope_key = make_scope_key(mode, scope)
    download_payload = st.session_state["po_trace_downloads"].get(scope_key)
    selected_po_idx = None

    def render_conc():
        st.write("")

    def render_po():
        nonlocal selected_po_idx, po_list, download_payload
        if uploaded_file:
            button_col_compute, button_col_download = st.columns([1, 1], gap="small")

            with button_col_compute:
                if st.button("Compute PO Traces", key=f"compute_po_{mode}_{scope}", use_container_width=True):
                    try:
                        ensure_prepared(mode, scope)
                        filog_out, povariants = cco.compute_po_traces(mode, scope, stats_only=False)
                        st.session_state["po_traces"][scope_key] = povariants
                        po_list = st.session_state["po_traces"].get(scope_key, [])
                        set_po_trace_download(
                            scope_key,
                            filog_out,
                            "po_traces_tracewise.xes",
                            mode=mode,
                            scope=scope,
                        )
                        download_payload = st.session_state["po_trace_downloads"].get(scope_key)
                        set_ui_message("success", f"PO Traces successfully computed! Number of traces: {len(povariants)}")
                    except Exception as e:
                        set_ui_message("error", f"Error computing PO traces (tracewise): {e}")

            with button_col_download:
                if download_payload:
                    st.download_button(
                        label="Download .xes",
                        data=download_payload["bytes"],
                        file_name=download_payload["file_name"],
                        mime="application/octet-stream",
                        key=f"download_po_{mode}_{scope}",
                        on_click="ignore",
                        use_container_width=True,
                    )

        if po_list:
            st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
            selected_po_idx = st.radio(
                "Select PO",
                options=list(range(len(po_list))),
                format_func=lambda i: f"PO {po_list[i].graph.get('id', i)}",
                key=f"po_radio_{mode}_{scope}",
                label_visibility="collapsed",
            )
        else:
            st.write("")

    def render_graph():
        if po_list and selected_po_idx is not None:
            po = po_list[selected_po_idx]
            render_interactive_po_graph(po, f"{mode}_{scope}_{selected_po_idx}")

    render_panel_boxes(scope, TRACEWISE_BOX_HEIGHT, render_conc, render_po, render_graph, show_conc_box=False)


def render_logwise_content(mode, uploaded_file):
    state = cco.get_state(mode, "logwise")
    scope_key = make_scope_key(mode, "logwise")
    po_list = st.session_state["po_traces"].get(scope_key, [])
    download_payload = st.session_state["po_trace_downloads"].get(scope_key)
    selected_po_idx = None

    def render_conc():
        nonlocal state
        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

        if uploaded_file:
            button_col_compute, button_col_save = st.columns([1.35, 0.95])

            with button_col_compute:
                if st.button(
                    "Compute Concurrencies",
                    disabled=st.session_state.get(f"cc_done_{mode}_logwise", False),
                ):
                    try:
                        ensure_prepared(mode, "logwise")
                        detected = cco.detect_concurrencies(mode, "logwise")
                        state = cco.get_state(mode, "logwise")

                        scope_key = make_scope_key(mode, "logwise")
                        detected_pairs = {
                            frozenset(pair) for pair in detected.to_tuples()
                        }
                        set_detected_concurrency_pairs(mode, "logwise", detected_pairs)
                        set_user_concurrency_pairs(mode, "logwise", set(detected_pairs))

                        st.session_state[f"cc_done_{mode}_logwise"] = True

                        if len(list(detected)) > 0:
                            set_ui_message("success", "Concurrencies successfully computed!")
                        else:
                            set_ui_message("info", "No concurrencies were detected for your parameter selection.")

                    except Exception as e:
                        set_ui_message("error", f"Error computing concurrencies: {e}")

            with button_col_save:
                if st.button(
                    "Save Changes",
                    disabled=not st.session_state.get(f"cc_done_{mode}_logwise", False),
                ):
                    scope_key = make_scope_key(mode, "logwise")
                    selected_concurrencies = st.session_state.get("user_concurrencies", {}).get(scope_key, set())
                    edited_concurrent = frozensets_to_concurrent(selected_concurrencies)
                    try:
                        cco.set_concurrencies(mode, "logwise", edited_concurrent)
                        st.session_state["po_traces"].pop(scope_key, None)
                        st.session_state["po_trace_downloads"].pop(scope_key, None)
                        set_ui_message("success", f"{len(edited_concurrent)} concurrencies selected")
                    except Exception as e:
                        set_ui_message("error", f"Error saving concurrencies: {e}")

            st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

        scope_key = make_scope_key(mode, "logwise")
        detected_pairs = get_detected_concurrency_pairs(mode, "logwise")

        if detected_pairs is not None:
            if "user_concurrencies" not in st.session_state:
                st.session_state["user_concurrencies"] = {}

            if scope_key not in st.session_state["user_concurrencies"]:
                set_user_concurrency_pairs(mode, "logwise", set(detected_pairs))

            user_conc = st.session_state["user_concurrencies"][scope_key]

            if len(detected_pairs) > 0:
                conc_pairs = sorted(
                    (display_pair(pair) for pair in detected_pairs),
                    key=lambda pair: (str(pair[0]), str(pair[1])),
                )

                for pair in conc_pairs:
                    a, b = pair
                    key = f"{mode}-logwise-{a}-{b}"

                    pair_set = frozenset([a, b])

                    selected = st.checkbox(
                        f"{a} <-> {b}",
                        key=key,
                        value=(pair_set in user_conc),
                    )

                    if selected:
                        user_conc.add(pair_set)
                    else:
                        user_conc.discard(pair_set)

                set_user_concurrency_pairs(mode, "logwise", user_conc)

    def render_po():
        nonlocal selected_po_idx, po_list, download_payload
        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
        if uploaded_file:
            button_col_compute, button_col_download = st.columns([1, 1], gap="small")

            with button_col_compute:
                state = cco.get_state(mode, "logwise")
                if st.button(
                    "Compute PO Traces",
                    disabled=state.get("concurrencies") is None,
                    use_container_width=True,
                ):
                    try:
                        filog_out, povariants = cco.compute_po_traces(mode, "logwise", stats_only=False)
                        st.session_state["po_traces"][scope_key] = povariants
                        po_list = st.session_state["po_traces"].get(scope_key, [])
                        set_po_trace_download(
                            scope_key,
                            filog_out,
                            "po_traces_logwise.xes",
                            mode=mode,
                            scope="logwise",
                        )
                        download_payload = st.session_state["po_trace_downloads"].get(scope_key)
                        set_ui_message("success", f"PO Traces computed: {len(povariants)}")
                    except Exception as e:
                        set_ui_message("error", f"Error computing PO traces (logwise): {e}")

            with button_col_download:
                if download_payload:
                    st.download_button(
                        label="Download .xes",
                        data=download_payload["bytes"],
                        file_name=download_payload["file_name"],
                        mime="application/octet-stream",
                        key=f"download_po_{mode}_logwise",
                        on_click="ignore",
                        use_container_width=True,
                    )

        if po_list:
            st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
            selected_po_idx = st.radio(
                "Select PO",
                options=list(range(len(po_list))),
                format_func=lambda i: f"PO {po_list[i].graph.get('id', i)}",
                key=f"po_radio_{mode}_logwise",
                label_visibility="collapsed",
            )
        else:
            selected_po_idx = None

    def render_graph():
        if po_list and selected_po_idx is not None:
            po = po_list[selected_po_idx]
            render_interactive_po_graph(po, f"{mode}_logwise_{selected_po_idx}")

    render_panel_boxes("logwise", LOGWISE_BOX_HEIGHT, render_conc, render_po, render_graph)


def render_tracewise_content(mode, uploaded_file):
    render_po_ui(mode, "tracewise", uploaded_file)


# Upload + Mode
top_upload, top_mode, top_status = st.columns([1, 1, 2])

with top_upload:
    uploaded_file = st.file_uploader(
        "Upload Logfile",
        type=["xes"],
        key=f"upload_log_file_{st.session_state['upload_widget_nonce']}",
    )

with top_mode:
    mode = st.selectbox("Mode", ["alpha", "lifecycle"], index=0, label_visibility="visible")

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

st.markdown(
    f"""
    <style>
    .st-key-tab_btn_logwise button,
    .st-key-tab_btn_tracewise button {{
        width: 100%;
        height: 100%;
        border: 1px solid #000000 !important;
        border-radius: 0.7rem 0.7rem 0 0 !important;
        box-shadow: none !important;
        color: #374151 !important;
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
        margin-bottom: -1px !important;
        z-index: {2 if st.session_state["active_scope"] == "logwise" else 1};
    }}
    .st-key-tab_btn_tracewise button {{
        background: {tab_tracewise_bg} !important;
        border-bottom-color: {tab_tracewise_bottom} !important;
        margin-bottom: -1px !important;
        z-index: {2 if st.session_state["active_scope"] == "tracewise" else 1};
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
    .st-key-logwise_conc h3,
    .st-key-logwise_po h3,
    .st-key-logwise_graph h3,
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
    .st-key-logwise_conc .stButton > button,
    .st-key-logwise_po .stButton > button,
    .st-key-logwise_po .stDownloadButton > button,
    .st-key-tracewise_po .stButton > button,
    .st-key-tracewise_po .stDownloadButton > button {{
        min-height: 3.5rem !important;
        height: 3.5rem !important;
        max-height: 3.5rem !important;
        line-height: 1.2 !important;
        padding-top: 0.35rem !important;
        padding-bottom: 0.35rem !important;
    }}
    .st-key-logwise_conc .stButton > button {{
        font-size: 0.94rem !important;
    }}
    .st-key-logwise_po .stButton > button,
    .st-key-logwise_po .stDownloadButton > button,
    .st-key-tracewise_po .stButton > button,
    .st-key-tracewise_po .stDownloadButton > button {{
        font-size: 1rem !important;
        min-height: 3.5rem !important;
        height: 3.5rem !important;
        max-height: 3.5rem !important;
        width: 100% !important;
    }}
    .st-key-logwise_po .stButton > button p,
    .st-key-logwise_po .stDownloadButton > button p,
    .st-key-tracewise_po .stButton > button p,
    .st-key-tracewise_po .stDownloadButton > button p,
    .st-key-logwise_po .stButton > button div[data-testid="stMarkdownContainer"] p,
    .st-key-logwise_po .stDownloadButton > button div[data-testid="stMarkdownContainer"] p,
    .st-key-tracewise_po .stButton > button div[data-testid="stMarkdownContainer"] p,
    .st-key-tracewise_po .stDownloadButton > button div[data-testid="stMarkdownContainer"] p {{
        font-size: 1rem !important;
        line-height: 1.05 !important;
    }}
    div[data-testid="stCheckbox"] {{
        margin-bottom: 0.42rem !important;
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
            if st.button("Logwise", key="tab_btn_logwise", use_container_width=True):
                if st.session_state["active_scope"] != "logwise":
                    st.session_state["active_scope"] = "logwise"
                    st.rerun()

        with tab_col_2:
            if st.button("Tracewise", key="tab_btn_tracewise", use_container_width=True):
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

if st.session_state["pending_uploaded_file_bytes"] is not None:
    render_pending_upload_prompt(status_placeholder)
else:
    render_ui_message(status_placeholder)








