"""
Streamlit Dashboard — APIM Multi-Region Health Monitor

Live visualization of Azure API Management multi-region gateway health,
with controls to simulate DR scenarios using disableGateway.

Run:
    streamlit run dashboard/app.py

Expects a .env file (or environment variables) with:
    APIM_NAME, RESOURCE_GROUP, APIM_GATEWAY_URL,
    APIM_PRIMARY_REGIONAL_URL, APIM_SECONDARY_REGIONAL_URL,
    PRIMARY_REGION, SECONDARY_REGION
"""

import os
import sys
import time
from datetime import datetime, timezone

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add shared utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from utils import (
    check_default_gateway,
    check_region_health,
    send_traffic_burst,
    toggle_gateway,
)

# ── Configuration ────────────────────────────────────────────────────────────
APIM_NAME          = os.getenv("APIM_NAME", "")
RESOURCE_GROUP     = os.getenv("RESOURCE_GROUP", "")
GATEWAY_URL        = os.getenv("APIM_GATEWAY_URL", "")
PRIMARY_URL        = os.getenv("APIM_PRIMARY_REGIONAL_URL", "")
SECONDARY_URL      = os.getenv("APIM_SECONDARY_REGIONAL_URL", "")
PRIMARY_REGION     = os.getenv("PRIMARY_REGION", "East US")
SECONDARY_REGION   = os.getenv("SECONDARY_REGION", "West US 2")

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="APIM Multi-Region Dashboard",
    page_icon="🌍",
    layout="wide",
)

st.title("🌍 APIM Multi-Region Health Dashboard")
st.caption(
    f"Monitoring **{APIM_NAME}** — {PRIMARY_REGION} (primary) + {SECONDARY_REGION} (secondary)"
)

# ── Sidebar: configuration override ─────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")
    st.text_input("APIM Name", value=APIM_NAME, key="apim_name_input", disabled=True)
    st.text_input("Resource Group", value=RESOURCE_GROUP, key="rg_input", disabled=True)
    st.text_input("Default Gateway URL", value=GATEWAY_URL, key="gw_input", disabled=True)

    st.divider()
    st.header("🔧 Gateway Controls")
    st.caption("Simulate region failures using the official disableGateway API.")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔴 Disable East US", use_container_width=True):
            with st.spinner("Disabling primary gateway..."):
                try:
                    msg = toggle_gateway(APIM_NAME, RESOURCE_GROUP, PRIMARY_REGION, disable=True, is_primary=True)
                    st.success(msg)
                except Exception as e:
                    st.error(f"Error: {e}")

    with col_b:
        if st.button("🔴 Disable West US 2", use_container_width=True):
            with st.spinner("Disabling secondary gateway..."):
                try:
                    msg = toggle_gateway(APIM_NAME, RESOURCE_GROUP, SECONDARY_REGION, disable=True, is_primary=False)
                    st.success(msg)
                except Exception as e:
                    st.error(f"Error: {e}")

    if st.button("🟢 Enable All Gateways", use_container_width=True):
        with st.spinner("Re-enabling all gateways..."):
            try:
                msg1 = toggle_gateway(APIM_NAME, RESOURCE_GROUP, PRIMARY_REGION, disable=False, is_primary=True)
                msg2 = toggle_gateway(APIM_NAME, RESOURCE_GROUP, SECONDARY_REGION, disable=False, is_primary=False)
                st.success(f"{msg1}\n{msg2}")
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()
    auto_refresh = st.toggle("Auto-refresh (10s)", value=False)
    num_test_requests = st.slider("Traffic test requests", 5, 50, 20)


# ── Health check section ─────────────────────────────────────────────────────
def render_region_card(col, name: str, url: str, health: dict):
    """Render a region health card in a Streamlit column."""
    with col:
        if health["status"] == "healthy":
            st.success(f"🟢 **{name}**")
        elif health["status"] == "unhealthy":
            st.error(f"🟡 **{name}** (unhealthy)")
        else:
            st.error(f"🔴 **{name}** (unreachable)")

        st.metric("Latency", f"{health['latency_ms']} ms")
        st.text(f"Backend region: {health['region']}")
        st.text(f"HTTP status: {health['status_code'] or 'N/A'}")

        if health.get("error"):
            st.caption(f"⚠️ {health['error'][:120]}")


st.header("📡 Region Health")

if not GATEWAY_URL:
    st.warning(
        "Missing configuration. Run the Jupyter notebook first to create `.env` with deployment outputs."
    )
    st.stop()

col1, col2 = st.columns(2)

primary_health = check_region_health(PRIMARY_URL)
secondary_health = check_region_health(SECONDARY_URL)

render_region_card(col1, f"{PRIMARY_REGION} (Primary)", PRIMARY_URL, primary_health)
render_region_card(col2, f"{SECONDARY_REGION} (Secondary)", SECONDARY_URL, secondary_health)

# Default gateway check
st.divider()
st.subheader("🌐 Default Gateway")
default_health = check_default_gateway(GATEWAY_URL)
dcol1, dcol2, dcol3 = st.columns(3)
with dcol1:
    st.metric("Status", default_health["status"])
with dcol2:
    st.metric("Routed to Region", default_health["region"])
with dcol3:
    st.metric("Latency", f"{default_health['latency_ms']} ms")

# ── Traffic simulation ────────────────────────────────────────────────────────
st.divider()
st.header("🚦 Traffic Simulation")
st.caption(
    f"Send {num_test_requests} requests to the default gateway and see which region serves each."
)

if st.button("▶️ Run Traffic Test", use_container_width=True):
    with st.spinner(f"Sending {num_test_requests} requests..."):
        results = send_traffic_burst(GATEWAY_URL, num_requests=num_test_requests)

    # Summary
    region_counts = {}
    latencies = {}
    for r in results:
        reg = r["region"]
        region_counts[reg] = region_counts.get(reg, 0) + 1
        latencies.setdefault(reg, []).append(r["latency_ms"])

    col_pie, col_detail = st.columns([1, 2])

    with col_pie:
        fig = px.pie(
            names=list(region_counts.keys()),
            values=list(region_counts.values()),
            title="Traffic Distribution by Region",
            color_discrete_sequence=["#2196F3", "#FF9800", "#F44336"],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_detail:
        st.subheader("Per-Region Stats")
        for reg, count in region_counts.items():
            avg_lat = sum(latencies[reg]) / len(latencies[reg])
            min_lat = min(latencies[reg])
            max_lat = max(latencies[reg])
            st.write(
                f"**{reg}**: {count}/{num_test_requests} requests "
                f"(avg {avg_lat:.0f}ms, min {min_lat:.0f}ms, max {max_lat:.0f}ms)"
            )

    # Latency timeline
    fig_lat = go.Figure()
    for r in results:
        color = "#2196F3" if r["region"] == "eastus" else "#FF9800" if r["region"] == "westus2" else "#F44336"
        fig_lat.add_trace(go.Bar(
            x=[r["request_num"]],
            y=[r["latency_ms"]],
            marker_color=color,
            name=r["region"],
            showlegend=False,
        ))
    fig_lat.update_layout(
        title="Latency per Request",
        xaxis_title="Request #",
        yaxis_title="Latency (ms)",
        barmode="stack",
    )
    st.plotly_chart(fig_lat, use_container_width=True)

    # Request log
    with st.expander("📋 Full Request Log"):
        for r in results:
            icon = "🔵" if r["region"] == "eastus" else "🟠" if r["region"] == "westus2" else "🔴"
            st.text(
                f"{icon} #{r['request_num']:>3d}  region={r['region']:<10s}  "
                f"latency={r['latency_ms']:>7.1f}ms  status={r['status_code']}"
            )

# ── Auto-refresh ──────────────────────────────────────────────────────────────
st.divider()
st.caption(f"Last updated: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")

if auto_refresh:
    time.sleep(10)
    st.rerun()
