import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

import pandas as pd
import plotly.express as px
import streamlit as st

from services.document_service import DocumentEntry, DocumentService
from services.exception_engine import ExceptionEngine
from services.loader import MISLoader
from services.pdf_service import PDFService
from services.performance_service import PerformanceService
from services.planning_service import PlanningService
from services.validator import DataValidator
from utils.theme import apply_theme


st.set_page_config(
    page_title="IOB Dindigul - Premium Portal",
    page_icon="assets/favicon.svg",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_theme()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FACTS_PATH = os.path.join(DATA_DIR, "facts.parquet")
BRANCHES_PATH = os.path.join(DATA_DIR, "branches.csv")
EXCEPTIONS_PATH = os.path.join(DATA_DIR, "exceptions.parquet")

os.makedirs(DATA_DIR, exist_ok=True)

PAGE_OPTIONS = [
    "Dashboard",
    "Performance Lab",
    "Document Center",
    "Risk Register",
    "Targets And Campaigns",
    "Calendar And Milestones",
    "Data Hub",
    "Archive",
    "System",
]


@st.cache_data
def load_branches():
    if os.path.exists(BRANCHES_PATH):
        df = pd.read_csv(BRANCHES_PATH)
        df["code"] = df["code"].astype(str).str.zfill(4)
        return df
    return pd.DataFrame()


@st.cache_data
def load_facts():
    if os.path.exists(FACTS_PATH):
        df = pd.read_parquet(FACTS_PATH)
        df["sol"] = df["sol"].astype(str).str.zfill(4)
        df["date"] = pd.to_datetime(df["date"])
        return df
    return pd.DataFrame(columns=["sol", "date", "metric", "value"])


@st.cache_data
def load_exceptions():
    if os.path.exists(EXCEPTIONS_PATH):
        df = pd.read_parquet(EXCEPTIONS_PATH)
        if "sol" in df.columns:
            df["sol"] = df["sol"].astype(str).str.zfill(4)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        return df
    return pd.DataFrame(columns=["sol", "date", "type", "severity", "message", "metric_impact"])


@st.cache_resource
def get_pdf_service():
    return PDFService()


@st.cache_resource
def get_doc_service():
    return DocumentService()


@st.cache_resource
def get_planning_service():
    return PlanningService()


pdf_service = get_pdf_service()
doc_service = get_doc_service()
planning_service = get_planning_service()


def get_ro_details(dept_name=None):
    branches = load_branches()
    ro_df = branches[branches["type"] == "REGIONAL OFFICE"]
    
    details = {
        "name": "Regional Office, Dindigul",
        "contact": "0451-2423456",
        "email": "roplanning@iob.in",
        "address_en": "80 Feet Road, Dindigul - 624002",
        "address_ta": "80 அடி சாலை, திண்டுக்கல் - 624002",
        "address_hi": "80 फीट रोड, डिंडीगुल - 624002",
    }
    
    if not ro_df.empty:
        ro_rec = ro_df.iloc[0]
        details.update({
            "name": ro_rec.get("nameEn", details["name"]),
            "contact": ro_rec.get("phone", details["contact"]),
            "email": ro_rec.get("email", details["email"]),
            "address_en": str(ro_rec.get("address", details["address_en"])).replace(", ", ", <br/>", 1),
            "address_ta": str(ro_rec.get("addressTa", details["address_ta"])).replace(", ", ", <br/>", 1),
            "address_hi": str(ro_rec.get("addressHi", details["address_hi"])).replace(", ", ", <br/>", 1),
        })

    if dept_name:
        try:
            depts_path = os.path.join(DATA_DIR, "departments.csv")
            if os.path.exists(depts_path):
                depts = pd.read_csv(depts_path)
                match = depts[depts["dept_en"].str.upper() == str(dept_name).upper()]
                if not match.empty and "email" in match.columns:
                    details["email"] = match.iloc[0]["email"]
        except Exception as e:
            logger.error(f"Error fetching dept email for {dept_name}: {e}")
            
    return details


def current_fy_label(reference_date=None):
    ref = pd.Timestamp(reference_date or datetime.now())
    start_year = ref.year if ref.month >= 4 else ref.year - 1
    return f"FY {start_year}-{str(start_year + 1)[-2:]}"


def format_currency_cr(value):
    return f"Rs. {value / 100:,.2f} Cr"


def format_currency_lakh(value):
    return f"Rs. {value:,.2f} L"


def render_page_intro(title, description, kicker, pills=None):
    pills = pills or []
    pills_html = "".join(f'<span class="stat-pill">{pill}</span>' for pill in pills)
    st.markdown(
        f"""
        <section class="hero-shell">
            <div class="hero-kicker">{kicker}</div>
            <h1 class="hero-title">{title}</h1>
            <div class="hero-description">{description}</div>
            <div class="pill-row">{pills_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_app_shell_start():
    st.markdown('<div class="app-shell">', unsafe_allow_html=True)


def render_app_shell_end():
    st.markdown("</div>", unsafe_allow_html=True)


def render_topbar(active_page):
    facts = load_facts()
    exceptions = load_exceptions()
    latest_date, _ = get_latest_and_previous_dates(facts)
    status_bits = [
        current_fy_label(),
        active_page,
        f"{len(exceptions):,} flags",
        latest_date.strftime("%d %b %Y") if latest_date is not None else "No MIS date",
    ]
    chips_html = "".join(f'<span class="topbar-chip">{item}</span>' for item in status_bits)
    st.markdown(
        f"""
        <div class="topbar">
            <div class="topbar-brand">
                <div class="topbar-mark">IOB</div>
                <div>
                    <div class="topbar-title">Dindigul Regional Operating Console</div>
                    <div class="topbar-subtitle">A live workspace for MIS intelligence, field action, and document generation.</div>
                </div>
            </div>
            <div class="topbar-status">{chips_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_navigation(current_page):
    st.markdown('<div class="nav-shell"><div class="nav-caption">Workspace Navigation</div><div class="top-nav-host">', unsafe_allow_html=True)
    
    # Premium Icon Mapping
    icons = {
        "Dashboard": "🏠",
        "Performance Lab": "🧪",
        "Document Center": "📁",
        "Risk Register": "🛡️",
        "Targets And Campaigns": "🎯",
        "Calendar And Milestones": "📅",
        "Data Hub": "⚡",
        "Archive": "🗄️",
        "System": "⚙️",
    }
    
    page = st.radio(
        "Workspace Navigation",
        PAGE_OPTIONS,
        index=PAGE_OPTIONS.index(current_page),
        format_func=lambda x: f"{icons.get(x, '•')} {x}",
        horizontal=True,
        label_visibility="collapsed",
        key="top_navigation",
    )
    st.markdown("</div></div>", unsafe_allow_html=True)
    return page


def render_section_shell(title, subtitle, class_name=""):
    st.markdown(
        f"""
        <section class="section-card {class_name}">
            <div class="section-title">{title}</div>
            <div class="section-subtitle">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )


def close_section_shell():
    st.markdown("</section>", unsafe_allow_html=True)


def render_metric_card(label, value, delta=None, caption=None, tone="tone-focus"):
    delta_html = ""
    if delta:
        delta_color = "#1f7a57" if delta.startswith("+") else "#c9574f"
        delta_html = f'<div class="metric-delta" style="color: {delta_color};">{delta}</div>'
    caption_html = f'<div class="metric-caption">{caption}</div>' if caption else ""
    st.markdown(
        f"""
        <div class="metric-card {tone}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
            {caption_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(title, description):
    st.markdown(
        f"""
        <div class="empty-state">
            <strong>{title}</strong>
            {description}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_info_tiles(items):
    tiles = "".join(
        f"""
        <div class="info-tile">
            <div class="k">{label}</div>
            <div class="v">{value}</div>
        </div>
        """
        for label, value in items
    )
    st.markdown(f'<div class="info-grid">{tiles}</div>', unsafe_allow_html=True)


def render_mini_stats(items):
    cols = st.columns(len(items), gap="small")
    for col, (label, value, meta) in zip(cols, items):
        with col:
            st.markdown(
                f"""
                <div class="mini-stat">
                    <div class="mini-stat-label">{label}</div>
                    <div class="mini-stat-value">{value}</div>
                    <div class="mini-stat-meta">{meta}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_note_list(items):
    body = "".join(f'<div class="note-pill">{item}</div>' for item in items if item)
    st.markdown(f'<div class="note-pill-row">{body}</div>', unsafe_allow_html=True)


def render_exception_list(exception_rows, max_items=5):
    if exception_rows.empty:
        render_empty_state(
            "Regional risk desk is clear.",
            "No exceptions are currently available for the latest review cycle.",
        )
        return
    for _, row in exception_rows.head(max_items).iterrows():
        severity = str(row.get("severity", "MEDIUM")).upper()
        badge_class = {
            "CRITICAL": "severity-badge severity-critical",
            "HIGH": "severity-badge severity-high",
        }.get(severity, "severity-badge severity-medium")
        st.markdown(
            f"""
            <div class="alert-item" data-severity="{severity}">
                <div class="alert-topline">
                    <div class="alert-code">{row.get("sol", "0000")} | {row.get("type", "EXCEPTION")}</div>
                    <span class="{badge_class}">{severity.title()}</span>
                </div>
                <div class="alert-message">{row.get("message", "No message available.")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def build_plot_theme(fig):
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=46, b=8),
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right"),
        hovermode="x unified",
        font=dict(family="Manrope, sans-serif", color="#162033"),
        hoverlabel=dict(
            bgcolor="rgba(17,40,67,0.96)",
            bordercolor="rgba(255,255,255,0.15)",
            font=dict(color="#ffffff", family="Manrope, sans-serif"),
        ),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, showline=False, tickfont=dict(color="#6a7284"))
    fig.update_yaxes(gridcolor="rgba(21,58,102,0.08)", zeroline=False, tickfont=dict(color="#6a7284"))
    return fig


def merge_facts_into_registry(new_facts: pd.DataFrame):
    existing = load_facts()
    combined = pd.concat([existing, new_facts], ignore_index=True)
    combined["sol"] = combined["sol"].astype(str).str.zfill(4)
    combined["date"] = pd.to_datetime(combined["date"])
    combined["value"] = pd.to_numeric(combined["value"], errors="coerce").fillna(0.0)
    combined = combined.groupby(["sol", "date", "metric"], as_index=False)["value"].sum()
    combined.to_parquet(FACTS_PATH, index=False)

    branches = load_branches()
    exceptions = ExceptionEngine.scan(combined, branches)
    if not exceptions.empty:
        exceptions.to_parquet(EXCEPTIONS_PATH, index=False)
    elif os.path.exists(EXCEPTIONS_PATH):
        os.remove(EXCEPTIONS_PATH)

    st.cache_data.clear()


def get_latest_and_previous_dates(facts: pd.DataFrame):
    if facts.empty:
        return None, None
    dates = sorted(facts["date"].dropna().unique())
    latest = dates[-1]
    previous = dates[-2] if len(dates) > 1 else None
    return pd.to_datetime(latest), pd.to_datetime(previous) if previous is not None else None


def build_region_target_summary(snapshot: pd.DataFrame, targets_df: pd.DataFrame):
    if snapshot.empty or targets_df.empty:
        return pd.DataFrame()
    target_map = targets_df.set_index("metric")["target_value"].to_dict()
    rows = []
    for metric in ["Bus", "Dep", "Adv", "CASA", "NPA"]:
        current_value = float(snapshot[metric].sum()) if metric in snapshot.columns else 0.0
        target_value = float(target_map.get(metric, 0) or 0)
        achievement = (current_value / target_value * 100) if target_value else 0.0
        rows.append(
            {
                "Metric": metric,
                "Current": current_value,
                "Target": target_value,
                "Achievement %": round(achievement, 2),
            }
        )
    return pd.DataFrame(rows)


def view_dashboard():
    facts = load_facts()
    exceptions = load_exceptions()
    branches = load_branches()
    snapshot = PerformanceService.latest_snapshot(facts, branches)
    latest_date, previous_date = get_latest_and_previous_dates(facts)

    render_page_intro(
        "Strategic Dashboard",
        "A sharper control room for regional momentum, risk pressure, branch milestones, and planning signals.",
        "Executive Overview",
        pills=[
            f"Facts rows: {len(facts):,}",
            f"Branches tracked: {len(branches):,}",
            f"Exception flags: {len(exceptions):,}",
        ],
    )

    if facts.empty or snapshot.empty or latest_date is None:
        render_empty_state(
            "No MIS registry is available yet.",
            "Use the Data Hub to ingest the latest MIS file. The portal will then calculate exceptions, branch scoring, milestones, and document context automatically.",
        )
        return

    current_data = facts[facts["date"] == latest_date]
    previous_data = facts[facts["date"] == previous_date] if previous_date is not None else pd.DataFrame()

    def metric_total(frame, metric_name):
        subset = frame[frame["metric"] == metric_name]
        return float(subset["value"].sum()) if not subset.empty else 0.0

    def delta_for(metric_name):
        if previous_data.empty:
            return "Fresh cycle"
        prev = metric_total(previous_data, metric_name)
        curr = metric_total(current_data, metric_name)
        if prev == 0:
            return "Fresh cycle"
        return f"{((curr - prev) / prev) * 100:+.1f}% vs prior"

    avg_casa = snapshot["CASA_PCT"].mean() if "CASA_PCT" in snapshot.columns else 0.0
    avg_cd = snapshot["CD_Ratio"].mean() if "CD_Ratio" in snapshot.columns else 0.0
    affected_branches = exceptions["sol"].nunique() if not exceptions.empty else 0

    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        render_metric_card("Total Business", format_currency_cr(metric_total(current_data, "Bus")), delta_for("Bus"), tone="tone-focus")
    with c2:
        render_metric_card("Total Deposits", format_currency_cr(metric_total(current_data, "Total Dep")), delta_for("Total Dep"), tone="tone-growth")
    with c3:
        render_metric_card("Total Advances", format_currency_cr(metric_total(current_data, "Adv")), delta_for("Adv"), tone="tone-focus")
    with c4:
        render_metric_card("Gross NPA", format_currency_lakh(metric_total(current_data, "NPA")), delta_for("NPA"), tone="tone-alert")

    col1, col2 = st.columns([1.65, 1], gap="medium")
    with col1:
        render_section_shell(
            "Regional Growth Trajectory",
            f"Trendline through {latest_date.strftime('%d %b %Y')} for deposits, advances, and total business.",
            class_name="bento-card bento-tall",
        )
        trend_data = facts[facts["metric"].isin(["Total Dep", "Adv", "Bus"])].groupby(["date", "metric"], as_index=False)["value"].sum()
        trend_data["value_cr"] = trend_data["value"] / 100
        fig = px.area(
            trend_data,
            x="date",
            y="value_cr",
            color="metric",
            color_discrete_map={"Total Dep": "#153a66", "Adv": "#148a8a", "Bus": "#d4a64f"},
            labels={"value_cr": "Volume (Cr)", "date": "", "metric": ""},
        )
        fig = build_plot_theme(fig)
        fig.update_traces(line=dict(width=2.5), opacity=0.9)
        fig.update_layout(
            legend_title_text="",
            modebar_remove=["zoom", "pan", "select", "lasso2d", "autoScale2d"],
        )
        fig.update_traces(hovertemplate="%{fullData.name}<br>%{x|%d %b %Y}<br>%{y:,.2f} Cr<extra></extra>")
        st.plotly_chart(fig, use_container_width=True)
        render_mini_stats(
            [
                ("Momentum", delta_for("Bus"), "Business movement"),
                ("CASA Mean", f"{avg_casa:,.1f}%", "Regional deposit quality"),
                ("CD Mean", f"{avg_cd:,.1f}%", "Average liquidity stress"),
            ]
        )
        close_section_shell()

    with col2:
        render_section_shell(
            "Risk Spotlight",
            "Latest flagged exceptions surfaced for quick morning review.",
            class_name="bento-card",
        )
        latest_flags = exceptions.sort_values(["date", "severity"], ascending=[False, True]) if not exceptions.empty else exceptions
        render_mini_stats(
            [
                ("Critical", f"{len(exceptions[exceptions['severity'] == 'CRITICAL']):,}" if not exceptions.empty else "0", "Immediate attention"),
                ("High", f"{len(exceptions[exceptions['severity'] == 'HIGH']):,}" if not exceptions.empty else "0", "Control follow-up"),
                ("Branches", f"{affected_branches:,}", "Touched by exceptions"),
            ]
        )
        render_exception_list(latest_flags, max_items=5)
        close_section_shell()

    scored = PerformanceService.compute_branch_scores(snapshot)
    anniversaries = PerformanceService.upcoming_anniversaries(branches, latest_date.to_pydatetime(), within_days=30)
    milestones = PerformanceService.milestone_hits(snapshot)
    band_counts = scored["performance_band"].value_counts().rename_axis("band").reset_index(name="count")
    mix_df = pd.DataFrame(
        {
            "Metric": ["Deposits", "Advances"],
            "Value": [metric_total(current_data, "Dep") / 100, metric_total(current_data, "Adv") / 100],
        }
    )

    col3, col4, col5 = st.columns([1.05, 1.05, 1.2], gap="medium")
    with col3:
        render_section_shell(
            "Book Composition",
            "A quick visual split of the regional book with tighter chart presentation.",
            class_name="bento-card",
        )
        fig_mix = px.pie(
            mix_df,
            values="Value",
            names="Metric",
            hole=0.64,
            color="Metric",
            color_discrete_map={"Deposits": "#16385f", "Advances": "#0f8b8d"},
        )
        fig_mix = build_plot_theme(fig_mix)
        fig_mix.update_traces(
            textinfo="percent",
            textfont_size=13,
            marker=dict(line=dict(color="rgba(255,255,255,0.9)", width=3)),
            hovertemplate="%{label}<br>%{value:,.2f} Cr<extra></extra>",
        )
        fig_mix.update_layout(
            showlegend=True,
            margin=dict(l=0, r=0, t=10, b=0),
            modebar_remove=["zoom", "pan", "select", "lasso2d", "autoScale2d"],
        )
        st.plotly_chart(fig_mix, use_container_width=True)
        render_note_list(
            [
                f"Deposits: {mix_df.loc[mix_df['Metric'] == 'Deposits', 'Value'].iloc[0]:,.2f} Cr",
                f"Advances: {mix_df.loc[mix_df['Metric'] == 'Advances', 'Value'].iloc[0]:,.2f} Cr",
            ]
        )
        close_section_shell()

    with col4:
        render_section_shell(
            "Performance Bands",
            "Branch scoring grouped into operating bands for a faster regional read.",
            class_name="bento-card",
        )
        fig_bands = px.bar(
            band_counts,
            x="band",
            y="count",
            color="band",
            color_discrete_map={"Leading": "#16385f", "Stable": "#0f8b8d", "Needs Focus": "#d2675d"},
        )
        fig_bands = build_plot_theme(fig_bands)
        fig_bands.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0), modebar_remove=["zoom", "pan", "select", "lasso2d", "autoScale2d"])
        fig_bands.update_traces(
            marker_line_width=0,
            hovertemplate="%{x}: %{y} branches<extra></extra>",
        )
        st.plotly_chart(fig_bands, use_container_width=True)
        render_mini_stats(
            [
                ("Top Score", f"{scored['performance_score'].max():,.1f}", "Best branch score"),
                ("Median", f"{scored['performance_score'].median():,.1f}", "Regional midpoint"),
                ("Focus", f"{len(scored[scored['performance_band'] == 'Needs Focus']):,}", "Branches needing lift"),
            ]
        )
        close_section_shell()

    with col5:
        render_section_shell(
            "Branch Performance Leaders",
            "Automated scoring blends scale, deposit quality, stress, and profitability.",
            class_name="bento-card bento-tall",
        )
        leaders = scored[["nameEn", "district", "performance_score", "performance_band"]].head(8).rename(
            columns={"nameEn": "Branch", "district": "District", "performance_score": "Score", "performance_band": "Band"}
        )
        st.dataframe(leaders, use_container_width=True, hide_index=True)
        render_note_list(
            [
                f"Leader: {leaders.iloc[0]['Branch']}" if not leaders.empty else "",
                f"Best band count: {len(scored[scored['performance_band'] == 'Leading']):,}",
            ]
        )
        close_section_shell()

    col6, col7 = st.columns([1.2, 1.45], gap="medium")
    with col6:
        render_section_shell(
            "Calendar And Milestones",
            "Anniversaries and landmark branch achievements surfaced without manual tracking.",
            class_name="bento-card",
        )
        if not anniversaries.empty:
            st.caption("Upcoming branch anniversaries")
            st.dataframe(
                anniversaries.rename(
                    columns={
                        "nameEn": "Branch",
                        "district": "District",
                        "anniversary_date": "Anniversary",
                        "days_to_anniversary": "Days Away",
                        "years_completed": "Years",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            render_empty_state("No anniversary alerts due soon.", "Upcoming milestones will appear here automatically.")
        if not milestones.empty:
            st.caption("Latest milestone hits")
            st.dataframe(
                milestones.head(6).rename(
                    columns={
                        "branch_name": "Branch",
                        "metric": "Metric",
                        "milestone": "Milestone",
                        "current_value_cr": "Current (Cr)",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
        close_section_shell()

    with col7:
        render_section_shell(
            "Top Business Branches",
            "Horizontal ranking keeps the strongest branches visible without forcing a long table scan.",
            class_name="bento-card",
        )
        business_rows = current_data[current_data["metric"] == "Bus"].copy()
        if not business_rows.empty and not branches.empty:
            business_rows["value_cr"] = business_rows["value"] / 100
            ranked = (
                business_rows.merge(branches[["code", "nameEn", "district"]], left_on="sol", right_on="code", how="left")
                .sort_values("value_cr", ascending=False)
                .head(8)
            )
            fig_rank = px.bar(
                ranked.sort_values("value_cr"),
                x="value_cr",
                y="nameEn",
                orientation="h",
                color="value_cr",
                color_continuous_scale=["#d9ece5", "#78bba6", "#0f8b8d", "#16385f"],
                labels={"value_cr": "Business (Cr)", "nameEn": ""},
            )
            fig_rank = build_plot_theme(fig_rank)
            fig_rank.update_layout(
                coloraxis_showscale=False,
                margin=dict(l=10, r=10, t=10, b=10),
                modebar_remove=["zoom", "pan", "select", "lasso2d", "autoScale2d"],
            )
            fig_rank.update_traces(hovertemplate="%{y}<br>%{x:,.2f} Cr<extra></extra>", marker_line_width=0)
            st.plotly_chart(fig_rank, use_container_width=True)
            render_note_list(
                [
                    f"Peak branch: {ranked.iloc[0]['nameEn']}",
                    f"Top business: {ranked.iloc[0]['value_cr']:,.2f} Cr",
                    f"Tracked date: {latest_date.strftime('%d %b %Y')}",
                ]
            )
        else:
            render_empty_state("Branch ranking unavailable.", "Business rows will render here once MIS facts are available.")
        close_section_shell()


def view_performance_lab():
    facts = load_facts()
    branches = load_branches()
    targets_df = planning_service.list_targets(current_fy_label())

    render_page_intro(
        "Performance Lab",
        "Automated branch scoring, target achievement, milestone detection, and marketing focus queues from the central MIS registry.",
        "Intelligence Engine",
        pills=["Performance scoring", "Marketing focus", "Milestones", current_fy_label()],
    )

    snapshot = PerformanceService.latest_snapshot(facts, branches)
    if snapshot.empty:
        render_empty_state(
            "Performance analytics needs MIS data.",
            "Ingest branch facts first so the lab can score branches and map target achievement.",
        )
        return

    scored = PerformanceService.compute_branch_scores(snapshot)
    focus_df = PerformanceService.marketing_focus_report(snapshot, targets_df)
    target_summary = build_region_target_summary(snapshot, targets_df)
    milestone_df = PerformanceService.milestone_hits(snapshot)
    band_df = scored.groupby("performance_band", as_index=False).size().rename(columns={"size": "count"})
    district_df = (
        scored.groupby("district", as_index=False)["performance_score"]
        .mean()
        .sort_values("performance_score", ascending=False)
        .head(8)
    )

    render_mini_stats(
        [
            ("Scored Branches", f"{len(scored):,}", "Live branch ranking"),
            ("Focus Queue", f"{len(focus_df):,}" if not focus_df.empty else "0", "Branches needing action"),
            ("Milestones", f"{len(milestone_df):,}" if not milestone_df.empty else "0", "Detected landmark hits"),
        ]
    )

    col1, col2, col3 = st.columns([1.2, 1, 1], gap="medium")
    with col1:
        render_section_shell(
            "Branch Scoreboard",
            "Sorted regional leaderboard with a compact performance classification.",
            class_name="bento-card bento-tall",
        )
        display = scored[
            ["sol", "nameEn", "district", "Bus", "Total Dep", "Adv", "CASA_PCT", "CD_Ratio", "Branch_PL", "performance_score", "performance_band"]
        ].copy()
        display["Bus"] = (display["Bus"] / 100).round(2)
        display["Total Dep"] = (display["Total Dep"] / 100).round(2)
        display["Adv"] = (display["Adv"] / 100).round(2)
        display.rename(
            columns={
                "sol": "SOL",
                "nameEn": "Branch",
                "district": "District",
                "Total Dep": "Deposits (Cr)",
                "Adv": "Advances (Cr)",
                "Bus": "Business (Cr)",
                "CASA_PCT": "CASA %",
                "CD_Ratio": "CD %",
                "Branch_PL": "P&L (L)",
                "performance_score": "Score",
                "performance_band": "Band",
            },
            inplace=True,
        )
        st.dataframe(display, use_container_width=True, hide_index=True)
        render_note_list(
            [
                f"Top branch: {display.iloc[0]['Branch']}" if not display.empty else "",
                f"Median score: {scored['performance_score'].median():,.1f}",
            ]
        )
        close_section_shell()

    with col2:
        render_section_shell(
            "Regional Target Achievement",
            "Compares the latest region totals against FY targets stored in the planner.",
            class_name="bento-card",
        )
        if not target_summary.empty:
            target_table = target_summary.copy()
            target_table["Current"] = target_table.apply(
                lambda row: round(row["Current"] / 100, 2) if row["Metric"] != "NPA" else round(row["Current"], 2),
                axis=1,
            )
            target_table["Target"] = target_table.apply(
                lambda row: round(row["Target"] / 100, 2) if row["Metric"] != "NPA" else round(row["Target"], 2),
                axis=1,
            )
            st.dataframe(target_table, use_container_width=True, hide_index=True)
        else:
            render_empty_state(
                "FY targets have not been loaded yet.",
                "Use the Targets and Campaigns page to ingest or maintain annual parameter targets.",
            )
        close_section_shell()

    with col3:
        render_section_shell(
            "Score Distribution",
            "Performance bands and district-level averages keep the lab from feeling like a single large ranking table.",
            class_name="bento-card",
        )
        fig_band = px.bar(
            band_df,
            x="performance_band",
            y="count",
            color="performance_band",
            color_discrete_map={"Leading": "#16385f", "Stable": "#0f8b8d", "Needs Focus": "#d2675d"},
        )
        fig_band = build_plot_theme(fig_band)
        fig_band.update_layout(showlegend=False, margin=dict(l=0, r=0, t=8, b=8), modebar_remove=["zoom", "pan", "select", "lasso2d", "autoScale2d"])
        fig_band.update_traces(marker_line_width=0, hovertemplate="%{x}: %{y} branches<extra></extra>")
        st.plotly_chart(fig_band, use_container_width=True)
        if not district_df.empty:
            st.dataframe(
                district_df.rename(columns={"district": "District", "performance_score": "Avg Score"}),
                use_container_width=True,
                hide_index=True,
            )
        close_section_shell()

    col4, col5 = st.columns([1.2, 1], gap="medium")
    with col4:
        render_section_shell(
            "Marketing Focus Queue",
            "Branches below quality thresholds or business expectations are clustered here for officer action.",
            class_name="bento-card",
        )
        if not focus_df.empty:
            display = focus_df.copy()
            display["Bus"] = (display["Bus"] / 100).round(2)
            display["Dep"] = (display["Dep"] / 100).round(2)
            display["Adv"] = (display["Adv"] / 100).round(2)
            display.rename(
                columns={
                    "sol": "SOL",
                    "nameEn": "Branch",
                    "district": "District",
                    "Bus": "Business (Cr)",
                    "Dep": "Deposits (Cr)",
                    "Adv": "Advances (Cr)",
                    "CASA_PCT": "CASA %",
                    "CD_Ratio": "CD %",
                    "Branch_PL": "P&L (L)",
                    "focus_reason": "Focus Reason",
                },
                inplace=True,
            )
            st.dataframe(display, use_container_width=True, hide_index=True)
        else:
            render_empty_state(
                "No marketing priority queue is active.",
                "The current snapshot does not show any branches breaching the configured focus heuristics.",
            )
        close_section_shell()

    with col5:
        render_section_shell(
            "Milestone Registry",
            "Tracks major business, deposit, and advance landmarks such as 50 Cr, 100 Cr, and beyond.",
            class_name="bento-card",
        )
        if not milestone_df.empty:
            st.dataframe(
                milestone_df.rename(
                    columns={
                        "branch_name": "Branch",
                        "metric": "Metric",
                        "milestone": "Milestone",
                        "current_value_cr": "Current (Cr)",
                        "district": "District",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
            milestone_mix = milestone_df.groupby("metric", as_index=False).size().rename(columns={"size": "count"})
            fig_milestone = px.pie(
                milestone_mix,
                names="metric",
                values="count",
                hole=0.6,
                color="metric",
                color_discrete_sequence=["#16385f", "#0f8b8d", "#d3a24e"],
            )
            fig_milestone = build_plot_theme(fig_milestone)
            fig_milestone.update_layout(showlegend=True, margin=dict(l=0, r=0, t=8, b=0), modebar_remove=["zoom", "pan", "select", "lasso2d", "autoScale2d"])
            fig_milestone.update_traces(textinfo="percent", hovertemplate="%{label}: %{value} hits<extra></extra>")
            st.plotly_chart(fig_milestone, use_container_width=True)
        else:
            render_empty_state(
                "No milestone registry yet.",
                "As branches cross regional landmark thresholds, this section will fill automatically.",
            )
        close_section_shell()


def view_document_center():
    branches = load_branches()
    facts = load_facts()
    exceptions = load_exceptions()
    latest_date, _ = get_latest_and_previous_dates(facts)

    render_page_intro(
        "Document Center",
        "Generate explanation letters, risk advisories, internal notes, and marketing officer summaries from live branch data.",
        "Document Workflow",
        pills=["PDF output", "Date aware", "Branch context"],
    )

    mode = st.radio(
        "Document workflow",
        ["Internal Note", "Explanation Letter", "Risk Advisory", "Marketing Officer Report"],
        horizontal=True,
    )
    render_note_list(
        [
            "Internal notes for quick office communication",
            "Explanation letters tied to branch and date",
            "Risk advisories with prior-period comparison",
            "Marketing officer reports from focus heuristics",
        ]
    )

    if mode == "Internal Note":
        left, right = st.columns([1.45, 1], gap="medium")
        with left:
            render_section_shell(
                "Internal Note Composer",
                "Use this for quick correspondence that does not need branch analytics attached.",
                class_name="bento-card",
            )
            dept = st.text_input("Issuing department", value="PLANNING")
            ref_no = st.text_input("Reference number", value=doc_service.generate_ref_no("Internal Note", dept))
            subject = st.text_area("Subject", height=90)
            body_html = st.text_area("Body content (HTML supported)", height=280)
            close_section_shell()
        with right:
            render_section_shell(
                "Issuance Summary",
                "Keep the note metadata visible while drafting so the form feels more like a workspace than a long document editor.",
                class_name="bento-card bento-tall",
            )
            signatory_name = st.text_input("Signatory name", value="Dindigul Regional Office")
            signatory_designation = st.text_input("Designation", value="Manager")
            render_info_tiles(
                [
                    ("Mode", "Internal Note"),
                    ("Department", dept or "N/A"),
                    ("Output", "Registered PDF"),
                    ("Reference", ref_no.split("/")[-1] if ref_no else "Draft"),
                ]
            )
            render_note_list(
                [
                    "Good for approvals and office circulation",
                    "No branch analytics required",
                    "Archive-ready after generation",
                ]
            )
            if st.button("Generate internal note PDF", use_container_width=True):
                doc_data = {
                    "ref_no": ref_no,
                    "date": datetime.now().strftime("%d-%m-%Y"),
                    "title_en": subject,
                    "subject": subject,
                    "body_html": body_html,
                    "initiator": {"name_en": signatory_name, "designation_en": signatory_designation},
                    "reviewers": [],
                }
                pdf_bytes, _ = pdf_service.render_standard_document("internal_note.html", doc_data, office_details=get_ro_details(dept))
                doc_service.register_document(
                    DocumentEntry(
                        ref_no=ref_no,
                        date=datetime.now().strftime("%Y-%m-%d"),
                        doc_type="Internal Note",
                        subject=subject,
                        department=dept,
                        created_by=signatory_name,
                        content=doc_data,
                        frozen=True,
                    )
                )
                st.download_button("Download internal note", pdf_bytes, f"{ref_no.replace('/', '_')}.pdf", "application/pdf", use_container_width=True)
            close_section_shell()

    elif mode == "Explanation Letter":
        if branches.empty or facts.empty:
            render_section_shell(
                "Explanation Letter Generator",
                "Creates a point-wise explanation call letter for a selected branch and MIS date using actual movements and exception data.",
                class_name="bento-card",
            )
            render_empty_state(
                "Branch facts are required for explanation letters.",
                "Ingest MIS facts first so the system can compute the branch movement and linked exception context.",
            )
            close_section_shell()
            return
        left, right = st.columns([1.1, 1.2], gap="medium")
        with left:
            render_section_shell(
                "Explanation Letter Generator",
                "Choose the branch, cut date, and issuing desk. The system then assembles the explanation package automatically.",
                class_name="bento-card",
            )
            branch_name = st.selectbox("Branch", branches["nameEn"].dropna().tolist())
            branch_rec = branches[branches["nameEn"] == branch_name].iloc[0]
            date_options = facts[facts["sol"] == branch_rec["code"]]["date"].dropna().sort_values(ascending=False).unique()
            selected_date = st.selectbox("MIS date", date_options, format_func=lambda x: pd.to_datetime(x).strftime("%d-%m-%Y"))
            dept = st.text_input("Department", value="PLANNING", key="expl_dept")
            ref_no = st.text_input("Reference number", value=doc_service.generate_ref_no("Explanation Letter", dept), key="expl_ref")
            close_section_shell()
        package = PerformanceService.build_explanation_package(facts, branches, exceptions, branch_rec["code"], pd.to_datetime(selected_date))
        with right:
            render_section_shell(
                "Explanation Package Preview",
                "The right rail keeps the branch movement, exception load, and talking points visible before you generate the final letter.",
                class_name="bento-card bento-tall",
            )
            if package:
                render_info_tiles(
                    [
                        ("Branch", package.branch_name),
                        ("Date", package.report_date.strftime("%d-%m-%Y")),
                        ("Exception rows", len(package.exception_rows)),
                        ("Previous cut", package.previous_date.strftime("%d-%m-%Y") if package.previous_date is not None else "N/A"),
                    ]
                )
                preview_points = package.key_points[:3] if package.key_points else ["No key points generated."]
                render_note_list(preview_points)
                if st.button("Generate explanation letter", use_container_width=True):
                    doc_data = {
                        "ref_no": ref_no,
                        "date": datetime.now().strftime("%d-%m-%Y"),
                        "title_en": f"Explanation Letter - {package.branch_name}",
                        "subject": f"Explanation sought for branch variances as on {package.report_date.strftime('%d-%m-%Y')}",
                        "branch_name": package.branch_name,
                        "sol": package.sol,
                        "report_date": package.report_date.strftime("%d-%m-%Y"),
                        "metric_rows": package.metric_rows,
                        "key_points": package.key_points,
                        "exception_rows": package.exception_rows,
                        "initiator": {"name_en": "Dindigul Regional Office", "designation_en": "Manager"},
                        "reviewers": [],
                    }
                    pdf_bytes, _ = pdf_service.render_standard_document("explanation_letter.html", doc_data, office_details=get_ro_details(dept))
                    doc_service.register_document(
                        DocumentEntry(
                            ref_no=ref_no,
                            date=datetime.now().strftime("%Y-%m-%d"),
                            doc_type="Explanation Letter",
                            subject=doc_data["subject"],
                            department=dept,
                            created_by="Dindigul Regional Office",
                            content=doc_data,
                            frozen=True,
                        )
                    )
                    st.download_button("Download explanation letter", pdf_bytes, f"{ref_no.replace('/', '_')}.pdf", "application/pdf", use_container_width=True)
            close_section_shell()

    elif mode == "Risk Advisory":
        if branches.empty or facts.empty:
            render_section_shell(
                "Operational Risk Advisory",
                "Generates the richer branch advisory letter using current and previous branch metrics.",
                class_name="bento-card",
            )
            render_empty_state("MIS facts are required.", "Ingest branch facts first so advisories can be rendered.")
            close_section_shell()
            return
        wide = PerformanceService.facts_to_wide(facts)
        left, right = st.columns([1.05, 1.15], gap="medium")
        with left:
            render_section_shell(
                "Operational Risk Advisory",
                "Branch selection and date selection stay compact, while the right side highlights the advisory context.",
                class_name="bento-card",
            )
            branch_name = st.selectbox("Branch", branches["nameEn"].dropna().tolist(), key="risk_branch")
            branch_rec = branches[branches["nameEn"] == branch_name].iloc[0]
            branch_wide = wide[wide["sol"] == branch_rec["code"]].sort_values("date")
            date_options = branch_wide["date"].dropna().unique()
            selected_date = st.selectbox("MIS date", date_options, format_func=lambda x: pd.to_datetime(x).strftime("%d-%m-%Y"), key="risk_date")
            dept = st.text_input("Department", value="OPRISK", key="risk_dept")
            ref_no = st.text_input("Reference number", value=doc_service.generate_ref_no("Risk Advisory", dept), key="risk_ref")
            close_section_shell()
        current_row = branch_wide[branch_wide["date"] == pd.to_datetime(selected_date)].iloc[0].to_dict()
        previous_rows = branch_wide[branch_wide["date"] < pd.to_datetime(selected_date)]
        prev_row = previous_rows.iloc[-1].to_dict() if not previous_rows.empty else {}
        with right:
            render_section_shell(
                "Advisory Context",
                "This rail surfaces the branch profile and key comparison anchors before the PDF is created.",
                class_name="bento-card bento-tall",
            )
            render_info_tiles(
                [
                    ("Branch", branch_name),
                    ("District", branch_rec.get("district", "N/A")),
                    ("Current Date", pd.to_datetime(selected_date).strftime("%d-%m-%Y")),
                    ("Previous Date", pd.to_datetime(prev_row["date"]).strftime("%d-%m-%Y") if prev_row.get("date") is not None else "N/A"),
                ]
            )
            render_mini_stats(
                [
                    ("CD %", f"{float(current_row.get('CD_Ratio', 0) or 0):,.1f}", "Current liquidity stress"),
                    ("CASA %", f"{float(current_row.get('CASA_PCT', 0) or 0):,.1f}", "Deposit quality"),
                    ("P&L", f"{float(current_row.get('Branch_PL', 0) or 0):,.1f} L", "Profit or deficit"),
                ]
            )
            if st.button("Generate single risk advisory PDF", use_container_width=True):
                pdf_bytes, _ = pdf_service.render_risk_advisory(
                    sol=branch_rec["code"],
                    branch_name=branch_name,
                    date=pd.to_datetime(selected_date).to_pydatetime(),
                    metrics=current_row,
                    prev_metrics=prev_row,
                    ref_no=ref_no,
                    office_details=get_ro_details(dept),
                    branch_details=branch_rec.to_dict(),
                    prev_date=pd.to_datetime(prev_row["date"]).to_pydatetime() if prev_row.get("date") is not None else None,
                )
                doc_service.register_document(
                    DocumentEntry(
                        ref_no=ref_no,
                        date=pd.to_datetime(selected_date).strftime("%Y-%m-%d"),
                        doc_type="Risk Advisory",
                        subject=f"Operational Risk Advisory - {branch_name}",
                        department=dept,
                        created_by="Dindigul Regional Office",
                        content={"sol": branch_rec["code"], "date": str(selected_date)},
                        frozen=True, # Single generation remains frozen by default
                    )
                )
                st.download_button("Download risk advisory", pdf_bytes, f"{ref_no.replace('/', '_')}.pdf", "application/pdf", use_container_width=True)
            
            st.divider()
            st.markdown("### Bulk Operations")
            st.caption("Generate advisories for all branches for the selected date.")
            
            if st.button("Bulk Generate for ALL Branches", use_container_width=True):
                selected_date_str = pd.to_datetime(selected_date).strftime("%Y-%m-%d")
                purged = doc_service.purge_unfrozen_by_type_and_date("Risk Advisory", selected_date_str)
                if purged > 0:
                    st.info(f"Purged {purged} previous unfrozen advisories for this date.")
                
                valid_branches = branches[branches["type"] == "BRANCH"]
                progress_bar = st.progress(0)
                status_text = st.empty()
                total = len(valid_branches)
                
                success_count = 0
                for i, (_, b_rec) in enumerate(valid_branches.iterrows()):
                    try:
                        b_sol = b_rec["code"]
                        b_name = b_rec["nameEn"]
                        b_wide = wide[wide["sol"] == b_sol].sort_values("date")
                        b_current_rows = b_wide[b_wide["date"] == pd.to_datetime(selected_date)]
                        
                        if b_current_rows.empty:
                            continue
                            
                        b_current_row = b_current_rows.iloc[0].to_dict()
                        b_prev_rows = b_wide[b_wide["date"] < pd.to_datetime(selected_date)]
                        b_prev_row = b_prev_rows.iloc[-1].to_dict() if not b_prev_rows.empty else {}
                        
                        b_ref = doc_service.generate_ref_no("Risk Advisory", dept)
                        
                        # Generate PDF (this is slow, but requirement is for bulk)
                        # We don't need to return bytes here if we just want to register it
                        # But wait, PDFService.render_risk_advisory generates the PDF bytes.
                        # We don't store bytes in DB, but we store the context to regenerate.
                        
                        doc_service.register_document(
                            DocumentEntry(
                                ref_no=b_ref,
                                date=selected_date_str,
                                doc_type="Risk Advisory",
                                subject=f"Operational Risk Advisory - {b_name}",
                                department=dept,
                                created_by="System (Bulk)",
                                content={"sol": b_sol, "date": selected_date_str},
                                frozen=False, # Bulk generated remain unfrozen until reviewed
                            )
                        )
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Failed to bulk generate for {b_name}: {e}")
                    
                    progress_bar.progress((i + 1) / total)
                    status_text.text(f"Processing {b_name} ({i+1}/{total})")
                
                st.success(f"Successfully bulk registered {success_count} advisories for {selected_date_str}.")
                st.rerun()

            if st.button("Freeze All Advisories for this Date", use_container_width=True, type="primary"):
                selected_date_str = pd.to_datetime(selected_date).strftime("%Y-%m-%d")
                frozen = doc_service.freeze_documents_by_type_and_date("Risk Advisory", selected_date_str)
                st.success(f"Frozen {frozen} advisories for {selected_date_str}.")
                st.rerun()

            close_section_shell()

    else:
        snapshot = PerformanceService.latest_snapshot(facts, branches)
        targets_df = planning_service.list_targets(current_fy_label())
        focus_df = PerformanceService.marketing_focus_report(snapshot, targets_df)
        if focus_df.empty:
            render_section_shell(
                "Marketing Officer Report",
                "Produces a ready-to-share officer follow-up report from branches that need campaign or deposit mobilization attention.",
                class_name="bento-card",
            )
            render_empty_state(
                "No marketing focus queue is active.",
                "Once branches fall below the heuristic thresholds, the officer report will populate automatically.",
            )
            close_section_shell()
            return
        left, right = st.columns([1.35, 1], gap="medium")
        with left:
            render_section_shell(
                "Marketing Officer Report",
                "The branch queue stays in a broad table while generation controls stay compact on the right.",
                class_name="bento-card",
            )
            st.dataframe(focus_df.rename(columns={"nameEn": "Branch", "focus_reason": "Focus Reason"}), use_container_width=True, hide_index=True)
            close_section_shell()
        with right:
            render_section_shell(
                "Officer Brief",
                "Generate the branch follow-up pack once the queue looks right.",
                class_name="bento-card bento-tall",
            )
            dept = st.text_input("Department", value="MARKETING", key="mo_dept")
            ref_no = st.text_input("Reference number", value=doc_service.generate_ref_no("Marketing Officer Report", dept), key="mo_ref")
            period_date = latest_date if latest_date is not None else pd.Timestamp(datetime.now())
            render_info_tiles(
                [
                    ("Focus Branches", len(focus_df)),
                    ("Period", pd.to_datetime(period_date).strftime("%b %Y")),
                    ("Department", dept),
                    ("Reference", ref_no.split("/")[-1] if ref_no else "Draft"),
                ]
            )
            render_note_list(
                [
                    "Use for campaign visits and deposit push",
                    "Derived from live MIS and target context",
                    "Ideal for morning officer briefing",
                ]
            )
            if st.button("Generate marketing officer PDF", use_container_width=True):
                rows = focus_df.to_dict("records")
                doc_data = {
                    "ref_no": ref_no,
                    "date": datetime.now().strftime("%d-%m-%Y"),
                    "period": pd.to_datetime(period_date).strftime("%B %Y"),
                    "title_en": "Marketing Officer Focus Report",
                    "subject": "Marketing Officer Follow-up Priorities",
                    "rows": rows,
                    "initiator": {"name_en": "Dindigul Regional Office", "designation_en": "Manager"},
                    "reviewers": [],
                }
                pdf_bytes, _ = pdf_service.render_standard_document("marketing_officer_report.html", doc_data, office_details=get_ro_details(dept))
                doc_service.register_document(
                    DocumentEntry(
                        ref_no=ref_no,
                        date=datetime.now().strftime("%Y-%m-%d"),
                        doc_type="Marketing Officer Report",
                        subject=doc_data["subject"],
                        department=dept,
                        created_by="Dindigul Regional Office",
                        content=doc_data,
                        frozen=True,
                    )
                )
                st.download_button("Download marketing officer report", pdf_bytes, f"{ref_no.replace('/', '_')}.pdf", "application/pdf", use_container_width=True)
            close_section_shell()


def view_targets_and_campaigns():
    facts = load_facts()
    branches = load_branches()
    snapshot = PerformanceService.latest_snapshot(facts, branches)
    fy_label = current_fy_label()
    targets_df = planning_service.list_targets(fy_label)
    campaigns_df = planning_service.list_campaigns()

    render_page_intro(
        "Targets And Campaigns",
        "Maintain FY parameter targets, ingest target sheets, and track live campaign plans in one place.",
        "Planning Desk",
        pills=[fy_label, "Target ingestion", "Campaign tracking"],
    )
    render_mini_stats(
        [
            ("Target Rows", f"{len(targets_df):,}", "FY planner entries"),
            ("Campaigns", f"{len(campaigns_df):,}", "Stored campaign records"),
            ("Region Branches", f"{len(snapshot):,}" if not snapshot.empty else "0", "Current coverage"),
        ]
    )

    col1, col2 = st.columns([1.25, 1])
    with col1:
        render_section_shell(
            "FY Target Ingestion",
            "Upload a CSV or Excel target sheet or maintain the planner manually for business, deposits, advances, and other parameters.",
            class_name="bento-card",
        )
        target_file = st.file_uploader("Target file", type=["csv", "xlsx"], key="target_upload")
        owner = st.text_input("Target owner", value="Planning Department")
        if target_file is not None:
            target_frame = pd.read_csv(target_file) if target_file.name.endswith(".csv") else pd.read_excel(target_file)
            st.dataframe(target_frame.head(20), use_container_width=True, hide_index=True)
            if st.button("Import FY targets"):
                try:
                    inserted = planning_service.replace_targets_from_frame(target_frame, fy_label, owner=owner)
                    st.cache_data.clear()
                    st.success(f"Imported {inserted} target rows for {fy_label}.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        manual_targets = targets_df[["metric", "target_value", "owner", "notes"]].copy() if not targets_df.empty else pd.DataFrame(
            [
                {"metric": "Bus", "target_value": 0.0, "owner": owner, "notes": ""},
                {"metric": "Dep", "target_value": 0.0, "owner": owner, "notes": ""},
                {"metric": "Adv", "target_value": 0.0, "owner": owner, "notes": ""},
                {"metric": "CASA", "target_value": 0.0, "owner": owner, "notes": ""},
                {"metric": "NPA", "target_value": 0.0, "owner": owner, "notes": ""},
            ]
        )
        edited_targets = st.data_editor(manual_targets, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("Save manual targets"):
            rows = []
            for _, row in edited_targets.iterrows():
                metric = str(row.get("metric", "")).strip()
                if metric:
                    rows.append(
                        {
                            "fy": fy_label,
                            "metric": metric,
                            "target_value": float(row.get("target_value", 0) or 0),
                            "owner": str(row.get("owner", "") or ""),
                            "notes": str(row.get("notes", "") or ""),
                        }
                    )
            planning_service.upsert_targets(rows)
            st.cache_data.clear()
            st.success(f"Saved {len(rows)} target rows.")
            st.rerun()
        close_section_shell()

    with col2:
        render_section_shell(
            "Campaign Hub",
            "Track active mobilization or recovery drives with dates, metric focus, and ownership.",
            class_name="bento-card bento-tall",
        )
        title = st.text_input("Campaign title")
        focus_metric = st.selectbox("Focus metric", ["Bus", "Total Dep", "Adv", "CASA", "NPA", "Recovery"])
        start_date = st.date_input("Start date", datetime.now(), key="campaign_start")
        end_date = st.date_input("End date", datetime.now(), key="campaign_end")
        goal_value = st.number_input("Goal value", min_value=0.0, value=0.0, step=1.0)
        campaign_owner = st.text_input("Campaign owner", value="Regional Office")
        status = st.selectbox("Status", ["Planned", "Active", "Completed"])
        notes = st.text_area("Notes", height=100)
        if st.button("Add campaign"):
            if title.strip():
                planning_service.create_campaign(
                    title=title.strip(),
                    focus_metric=focus_metric,
                    start_date=pd.to_datetime(start_date).strftime("%Y-%m-%d"),
                    end_date=pd.to_datetime(end_date).strftime("%Y-%m-%d"),
                    goal_value=goal_value,
                    owner=campaign_owner,
                    status=status,
                    notes=notes,
                )
                st.success("Campaign saved.")
                st.rerun()
            else:
                st.error("Campaign title is required.")
        if not campaigns_df.empty:
            st.dataframe(campaigns_df, use_container_width=True, hide_index=True)
        else:
            render_empty_state("No campaigns saved yet.", "Create the first campaign from this panel.")
        close_section_shell()

    col3, col4 = st.columns([1.15, 1.25], gap="medium")
    with col3:
        render_section_shell(
            "Region Against Plan",
            "Live region totals are compared here against FY goals so campaign priorities can be set with real context.",
            class_name="bento-card",
        )
        if snapshot.empty or targets_df.empty:
            render_empty_state(
                "Plan comparison is waiting for inputs.",
                "Both the MIS registry and FY targets are needed before the region-to-plan comparison can be calculated.",
            )
        else:
            target_summary = build_region_target_summary(snapshot, targets_df)
            target_summary["Current"] = target_summary.apply(
                lambda row: round(row["Current"] / 100, 2) if row["Metric"] != "NPA" else round(row["Current"], 2),
                axis=1,
            )
            target_summary["Target"] = target_summary.apply(
                lambda row: round(row["Target"] / 100, 2) if row["Metric"] != "NPA" else round(row["Target"], 2),
                axis=1,
            )
            st.dataframe(target_summary, use_container_width=True, hide_index=True)
        close_section_shell()
    with col4:
        render_section_shell(
            "Achievement Snapshot",
            "A compact visual view of plan achievement so the page doesn’t read like a spreadsheet alone.",
            class_name="bento-card",
        )
        if snapshot.empty or targets_df.empty:
            render_empty_state("No visual plan summary yet.", "Add targets and current MIS data to activate this view.")
        else:
            target_summary = build_region_target_summary(snapshot, targets_df)
            chart_df = target_summary.copy()
            chart_df["Achievement %"] = chart_df["Achievement %"].clip(upper=200)
            fig = px.bar(
                chart_df,
                x="Achievement %",
                y="Metric",
                orientation="h",
                color="Achievement %",
                color_continuous_scale=["#d2675d", "#d3a24e", "#0f8b8d", "#16385f"],
            )
            fig = build_plot_theme(fig)
            fig.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=8, b=8), modebar_remove=["zoom", "pan", "select", "lasso2d", "autoScale2d"])
            fig.update_traces(hovertemplate="%{y}: %{x:.1f}%<extra></extra>", marker_line_width=0)
            st.plotly_chart(fig, use_container_width=True)
            render_note_list(
                [
                    f"Best achievement: {chart_df.sort_values('Achievement %', ascending=False).iloc[0]['Metric']}" if not chart_df.empty else "",
                    fy_label,
                ]
            )
        close_section_shell()


def view_calendar_and_anniversary():
    branches = load_branches()
    facts = load_facts()
    snapshot = PerformanceService.latest_snapshot(facts, branches)
    latest_date, _ = get_latest_and_previous_dates(facts)

    render_page_intro(
        "Calendar And Anniversary Desk",
        "Tracks branch opening anniversaries and landmark business thresholds so events and recognition can be planned proactively.",
        "Milestone Calendar",
        pills=["Anniversary alerts", "Recognition planning", "Branch landmarks"],
    )

    anniversaries = PerformanceService.upcoming_anniversaries(branches, latest_date.to_pydatetime() if latest_date is not None else datetime.now(), 60)
    milestones = PerformanceService.milestone_hits(snapshot)
    anniversary_district = anniversaries.groupby("district", as_index=False).size().rename(columns={"size": "count"}) if not anniversaries.empty else pd.DataFrame()
    milestone_metric = milestones.groupby("metric", as_index=False).size().rename(columns={"size": "count"}) if not milestones.empty else pd.DataFrame()

    render_mini_stats(
        [
            ("Anniversaries", f"{len(anniversaries):,}" if not anniversaries.empty else "0", "Within next 60 days"),
            ("Milestone Hits", f"{len(milestones):,}" if not milestones.empty else "0", "Across core metrics"),
            ("Reference Date", latest_date.strftime("%d %b %Y") if latest_date is not None else "Today", "Current calendar context"),
        ]
    )

    col1, col2, col3 = st.columns([1.15, 1.15, 1], gap="medium")
    with col1:
        render_section_shell(
            "Upcoming Anniversaries",
            "Upcoming branch anniversaries within the next 60 days for greetings, campaigns, or local events.",
            class_name="bento-card",
        )
        if not anniversaries.empty:
            st.dataframe(
                anniversaries.rename(
                    columns={
                        "code": "SOL",
                        "nameEn": "Branch",
                        "district": "District",
                        "anniversary_date": "Anniversary",
                        "days_to_anniversary": "Days Away",
                        "years_completed": "Years Completed",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            render_empty_state("No near-term anniversary events.", "When branch dates approach, they will appear here automatically.")
        close_section_shell()

    with col2:
        render_section_shell(
            "Business Milestones",
            "Detected hits for 50 Cr, 100 Cr, 250 Cr, 500 Cr, and 1000 Cr thresholds across core business metrics.",
            class_name="bento-card",
        )
        if not milestones.empty:
            st.dataframe(
                milestones.rename(
                    columns={
                        "branch_name": "Branch",
                        "metric": "Metric",
                        "milestone": "Milestone",
                        "current_value_cr": "Current (Cr)",
                        "district": "District",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            render_empty_state("No milestones detected yet.", "As branches cross landmark values, they will be listed here.")
        close_section_shell()

    with col3:
        render_section_shell(
            "Calendar Snapshot",
            "A compact visual summary of where upcoming recognition opportunities are concentrated.",
            class_name="bento-card",
        )
        if not anniversary_district.empty:
            fig_ann = px.bar(
                anniversary_district,
                x="district",
                y="count",
                color="count",
                color_continuous_scale=["#d9ece5", "#78bba6", "#0f8b8d", "#16385f"],
            )
            fig_ann = build_plot_theme(fig_ann)
            fig_ann.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=8, b=8), modebar_remove=["zoom", "pan", "select", "lasso2d", "autoScale2d"])
            fig_ann.update_traces(marker_line_width=0, hovertemplate="%{x}: %{y} anniversaries<extra></extra>")
            st.plotly_chart(fig_ann, use_container_width=True)
        if not milestone_metric.empty:
            fig_metric = px.pie(
                milestone_metric,
                names="metric",
                values="count",
                hole=0.62,
                color="metric",
                color_discrete_sequence=["#16385f", "#0f8b8d", "#d3a24e"],
            )
            fig_metric = build_plot_theme(fig_metric)
            fig_metric.update_layout(showlegend=True, margin=dict(l=0, r=0, t=8, b=0), modebar_remove=["zoom", "pan", "select", "lasso2d", "autoScale2d"])
            fig_metric.update_traces(textinfo="percent", hovertemplate="%{label}: %{value} hits<extra></extra>")
            st.plotly_chart(fig_metric, use_container_width=True)
        if anniversary_district.empty and milestone_metric.empty:
            render_empty_state("Calendar visuals will appear here.", "Anniversary and milestone data will activate these compact charts automatically.")
        close_section_shell()


def view_data_hub():
    render_page_intro(
        "Data Hub",
        "Ingest MIS files, validate the shape, merge them into the registry, and automatically refresh the exception engine.",
        "Data Pipeline",
        pills=["Excel and CSV", "Validation", "Registry merge", "Exception refresh"],
    )
    render_mini_stats(
        [
            ("Source Types", "Excel + CSV", "Supported uploads"),
            ("Output", "Fact Registry", "Normalized storage"),
            ("After Merge", "Exception refresh", "Automatic risk recalculation"),
        ]
    )

    render_section_shell(
        "MIS Ingestion",
        "Upload a source file to preview the normalized facts, validate critical coverage, and merge it into the central registry.",
        class_name="bento-card",
    )
    file = st.file_uploader("MIS source file", type=["xlsx", "csv"])
    if file:
        with st.spinner("Parsing and normalizing the uploaded MIS file..."):
            facts, parse_issues = MISLoader.process_file(file)
            is_valid, validation_issues = DataValidator.validate_ingestion(facts)
            summary = DataValidator.get_summary_stats(facts)

        if not facts.empty:
            render_info_tiles(
                [
                    ("Imported rows", f"{summary.get('total_rows', 0):,}"),
                    ("Branches", f"{summary.get('unique_branches', 0):,}"),
                    ("Dates", ", ".join(summary.get("dates", [])[:3]) or "N/A"),
                    ("Metrics", f"{summary.get('metrics_captured', 0):,}"),
                ]
            )
            left, right = st.columns([1.4, 1], gap="medium")
            with left:
                st.dataframe(facts.head(30), use_container_width=True, hide_index=True)
            with right:
                render_section_shell(
                    "Validation Readout",
                    "This side panel keeps parse and validation notes visible while you decide whether the file is ready for merge.",
                    class_name="bento-card",
                )
                if parse_issues:
                    st.warning("Parsing notes: " + " | ".join(parse_issues))
                else:
                    st.success("No parsing issues detected.")
                if validation_issues:
                    st.warning("Validation notes: " + " | ".join(validation_issues))
                else:
                    st.success("Critical validation checks passed.")
                render_note_list(
                    [
                        "Preview limited to first 30 normalized rows",
                        "Registry merge will aggregate duplicate branch-date-metric rows",
                        "Exception file refresh happens automatically",
                    ]
                )
                if st.button("Merge into central registry", use_container_width=True):
                    merge_facts_into_registry(facts)
                    st.success("MIS facts merged into the registry and exceptions recalculated.")
                    st.rerun()
                elif not is_valid:
                    st.info("The file can still be reviewed above, but merge should wait until the critical validation issues are addressed.")
                close_section_shell()
        else:
            st.error("The uploaded file did not produce usable facts.")
    close_section_shell()


def view_risk_register():
    exceptions = load_exceptions()

    render_page_intro(
        "Risk Register",
        "A cleaner view of exceptions, severity concentration, and branch-wise control stress across the latest uploaded registry.",
        "Compliance Watch",
        pills=["Severity aware", "Branch follow-up", "Exception registry"],
    )

    if exceptions.empty:
        render_empty_state(
            "No exceptions are loaded.",
            "Once MIS data is merged and scanned, this register will display the full exception trail.",
        )
        return

    critical_count = len(exceptions[exceptions["severity"] == "CRITICAL"])
    high_count = len(exceptions[exceptions["severity"] == "HIGH"])
    latest_date = exceptions["date"].max()
    branch_impact = (
        exceptions.groupby("sol", as_index=False)
        .size()
        .rename(columns={"size": "flags"})
        .sort_values("flags", ascending=False)
        .head(8)
    )
    severity_df = exceptions.groupby("severity", as_index=False).size().rename(columns={"size": "count"})

    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric_card("Total Flags", f"{len(exceptions):,}", caption="Exceptions across the current registry.")
    with c2:
        render_metric_card("Critical", f"{critical_count:,}", caption="Immediate action items.", tone="tone-alert")
    with c3:
        render_metric_card("High", f"{high_count:,}", caption="Material control exceptions.", tone="tone-growth")

    col1, col2, col3 = st.columns([0.95, 1.15, 1.1], gap="medium")
    with col1:
        render_section_shell(
            "Latest Queue",
            f"Quick-read issue stack through {latest_date.strftime('%d %b %Y')}.",
            class_name="bento-card",
        )
        latest_rows = exceptions.sort_values(["date", "severity"], ascending=[False, True])
        render_exception_list(latest_rows, max_items=7)
        close_section_shell()

    with col2:
        render_section_shell(
            "Detailed Register",
            "Full exception frame for audit review and follow-up tracking.",
            class_name="bento-card bento-tall",
        )
        display = exceptions.copy()
        display["date"] = display["date"].dt.strftime("%d-%m-%Y")
        st.dataframe(display, use_container_width=True, hide_index=True)
        close_section_shell()

    with col3:
        render_section_shell(
            "Severity And Branch Impact",
            "A compact visual summary to avoid reading the entire register just to understand where pressure is concentrated.",
            class_name="bento-card",
        )
        fig = px.bar(
            severity_df,
            x="severity",
            y="count",
            color="severity",
            color_discrete_map={"CRITICAL": "#d2675d", "HIGH": "#d3a24e", "MEDIUM": "#0f8b8d"},
        )
        fig = build_plot_theme(fig)
        fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=8, b=8), modebar_remove=["zoom", "pan", "select", "lasso2d", "autoScale2d"])
        fig.update_traces(marker_line_width=0, hovertemplate="%{x}: %{y} flags<extra></extra>")
        st.plotly_chart(fig, use_container_width=True)
        if not branch_impact.empty:
            st.dataframe(branch_impact.rename(columns={"sol": "SOL", "flags": "Flags"}), use_container_width=True, hide_index=True)
        close_section_shell()


def view_archive():
    entries = doc_service.get_all_entries()
    frozen_count = len([e for e in entries if e.frozen])
    render_page_intro(
        "Document Archive",
        "Search the registered output history across explanation letters, advisories, internal notes, and reports.",
        "Audit Trail",
        pills=[f"Registered docs: {len(entries):,}", "Document register", "Reference history"],
    )
    render_mini_stats(
        [
            ("Registered", f"{len(entries):,}", "All document records"),
            ("Frozen", f"{frozen_count:,}", "Archive-safe output"),
            ("Live", f"{len(entries) - frozen_count:,}", "Transient entries"),
        ]
    )
    render_section_shell(
        "Registered Documents",
        "The register below is sourced from the document database used by the portal.",
        class_name="bento-card",
    )
    if entries:
        rows = [
            {
                "Reference": e.ref_no,
                "Date": e.date,
                "Type": e.doc_type,
                "Subject": e.subject,
                "Department": e.department,
                "Created By": e.created_by,
                "Frozen": "❄️ Frozen" if e.frozen else "⏳ Transient",
                "Timestamp": pd.to_datetime(e.timestamp).strftime("%d-%m %H:%M"),
            }
            for e in entries
        ]
        archive_df = pd.DataFrame(rows)
        
        col1, col2 = st.columns([1.6, 1], gap="medium")
        with col1:
            render_section_shell("Registry Explorer", "Browse the full audit trail of generated documents.", class_name="bento-card")
            st.dataframe(archive_df, use_container_width=True, hide_index=True)
            close_section_shell()
            
            st.divider()
            render_section_shell("Document Action Console", "Retrieve, regenerate, or finalize registered documents.", class_name="bento-card")
            selected_ref = st.selectbox("Select document for action", archive_df["Reference"].tolist())
            if selected_ref:
                entry = next(e for e in entries if e.ref_no == selected_ref)
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(f"Download {entry.doc_type}", use_container_width=True, type="primary"):
                        with st.spinner("Regenerating PDF..."):
                            try:
                                if entry.doc_type == "Risk Advisory":
                                    # Regenerate Risk Advisory
                                    b_sol = entry.content.get("sol")
                                    b_date = entry.content.get("date")
                                    
                                    # Need to fetch metrics again
                                    facts = load_facts()
                                    branches = load_branches()
                                    wide = PerformanceService.facts_to_wide(facts)
                                    branch_rec = branches[branches["code"] == b_sol].iloc[0]
                                    branch_wide = wide[wide["sol"] == b_sol].sort_values("date")
                                    
                                    current_row = branch_wide[branch_wide["date"] == pd.to_datetime(b_date)].iloc[0].to_dict()
                                    previous_rows = branch_wide[branch_wide["date"] < pd.to_datetime(b_date)]
                                    prev_row = previous_rows.iloc[-1].to_dict() if not previous_rows.empty else {}
                                    
                                    pdf_bytes, _ = pdf_service.render_risk_advisory(
                                        sol=b_sol,
                                        branch_name=branch_rec["nameEn"],
                                        date=pd.to_datetime(b_date).to_pydatetime(),
                                        metrics=current_row,
                                        prev_metrics=prev_row,
                                        ref_no=entry.ref_no,
                                        office_details=get_ro_details(entry.department),
                                        branch_details=branch_rec.to_dict(),
                                        prev_date=pd.to_datetime(prev_row["date"]).to_pydatetime() if prev_row.get("date") is not None else None,
                                    )
                                else:
                                    # Standard documents store full doc_data in content
                                    template_map = {
                                        "Internal Note": "internal_note.html",
                                        "Explanation Letter": "explanation_letter.html",
                                        "Marketing Officer Report": "marketing_officer_report.html"
                                    }
                                    t_name = template_map.get(entry.doc_type, "internal_note.html")
                                    pdf_bytes, _ = pdf_service.render_standard_document(t_name, entry.content, office_details=get_ro_details(entry.department))
                                
                                st.download_button(
                                    "Confirm Download", 
                                    pdf_bytes, 
                                    f"{entry.ref_no.replace('/', '_')}.pdf", 
                                    "application/pdf", 
                                    use_container_width=True
                                )
                            except Exception as e:
                                st.error(f"Regeneration failed: {e}")
                
                with c2:
                    if not entry.frozen:
                        if st.button("Freeze/Finalize Document", use_container_width=True):
                            doc_service.freeze_document(entry.ref_no)
                            st.success(f"Document {entry.ref_no} is now frozen.")
                            st.rerun()
                    else:
                        st.info("Document is frozen and audit-locked.")
            close_section_shell()
            
        with col2:
            render_section_shell(
                "Archive Snapshot",
                "A quick distribution view makes the archive page feel like an app surface instead of a raw register dump.",
                class_name="bento-card",
            )
            type_counts = archive_df.groupby("Type", as_index=False).size().rename(columns={"size": "Count"})
            fig = px.bar(type_counts.sort_values("Count"), x="Count", y="Type", orientation="h", color="Count", color_continuous_scale=["#d9ece5", "#78bba6", "#0f8b8d", "#16385f"])
            fig = build_plot_theme(fig)
            fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=8, b=8), modebar_remove=["zoom", "pan", "select", "lasso2d", "autoScale2d"])
            fig.update_traces(marker_line_width=0, hovertemplate="%{y}: %{x} docs<extra></extra>")
            st.plotly_chart(fig, use_container_width=True)
            render_note_list(
                [
                    f"Latest entry: {archive_df.iloc[0]['Reference']}",
                    f"Most common type: {type_counts.sort_values('Count', ascending=False).iloc[0]['Type']}" if not type_counts.empty else "",
                ]
            )
            close_section_shell()
    else:
        render_empty_state("No registered documents yet.", "Generated PDFs will appear here after they are registered.")
    close_section_shell()


def view_system():
    render_page_intro(
        "System Console",
        "A compact view of portal state, stored plans, and maintenance actions.",
        "Administration",
        pills=["Data health", "Planning database", "Document registry"],
    )
    entries = doc_service.get_all_entries()
    targets_df = planning_service.list_targets()
    campaigns_df = planning_service.list_campaigns()

    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric_card("Documents", f"{len(entries):,}", tone="tone-focus")
    with c2:
        render_metric_card("Target Rows", f"{len(targets_df):,}", tone="tone-growth")
    with c3:
        render_metric_card("Campaigns", f"{len(campaigns_df):,}", tone="tone-alert")

    col1, col2 = st.columns([1, 1.2], gap="medium")
    with col1:
        render_section_shell(
            "Maintenance",
            "Use this area for lightweight housekeeping on the document register.",
            class_name="bento-card",
        )
        render_note_list(
            [
                "Targets and campaigns persist in the planning store",
                "Document register powers archive and output history",
                "Transient docs can be purged without touching frozen output",
            ]
        )
        if st.button("Purge unfrozen documents older than 24 hours", use_container_width=True):
            removed = doc_service.purge_unfrozen_documents(24)
            st.success(f"Purged {removed} transient documents.")
        close_section_shell()
    with col2:
        render_section_shell(
            "System Snapshot",
            "A lightweight operational picture of the portal state without sending you to the filesystem.",
            class_name="bento-card",
        )
        render_info_tiles(
            [
                ("Current FY", current_fy_label()),
                ("Archive Records", len(entries)),
                ("Planning Rows", len(targets_df)),
                ("Campaign Rows", len(campaigns_df)),
            ]
        )
        close_section_shell()


with st.sidebar:
    st.markdown(
        """
        <div class="side-brand">
            <div class="eyebrow">Regional Intelligence</div>
            <div class="title">IOB Dindigul</div>
            <div class="desc">
                A refined operating console for MIS review, document generation, target planning, campaign tracking, and branch follow-up.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="sidebar-note" style="margin-bottom: 0.8rem;">
            Primary navigation now lives in the main workspace header so the app feels like a control console rather than a report stack.
        </div>
        """,
        unsafe_allow_html=True,
    )

    side_map = "".join(f'<span class="side-map-chip">{item}</span>' for item in PAGE_OPTIONS)
    st.markdown(f'<div class="side-map">{side_map}</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="sidebar-note">
            Regional Office, Dindigul<br/>
            Version 3.0.0 Preview<br/><br/>
            Current planning cycle: {current_fy_label()}<br/>
            Suggested flow: ingest MIS, review performance lab, update targets, then generate action documents.
        </div>
        """,
        unsafe_allow_html=True,
    )

current_page = st.session_state.get("current_page", PAGE_OPTIONS[0])
render_app_shell_start()
topbar_slot = st.empty()
page = render_navigation(current_page)
topbar_slot.markdown("", unsafe_allow_html=True)
with topbar_slot.container():
    render_topbar(page)
st.session_state["current_page"] = page

if page == "Dashboard":
    view_dashboard()
elif page == "Performance Lab":
    view_performance_lab()
elif page == "Document Center":
    view_document_center()
elif page == "Risk Register":
    view_risk_register()
elif page == "Targets And Campaigns":
    view_targets_and_campaigns()
elif page == "Calendar And Milestones":
    view_calendar_and_anniversary()
elif page == "Data Hub":
    view_data_hub()
elif page == "Archive":
    view_archive()
else:
    view_system()
render_app_shell_end()
