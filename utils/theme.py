import streamlit as st


def apply_theme():
    """Apply a more application-like visual system with motion and navigation chrome."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Sora:wght@500;600;700;800&display=swap');

        :root {
            --bg: #f3efe7;
            --bg-soft: #faf7f1;
            --shell: rgba(255, 251, 245, 0.82);
            --panel: rgba(255, 255, 255, 0.76);
            --panel-strong: rgba(255, 255, 255, 0.92);
            --ink: #182433;
            --muted: #6a7284;
            --line: rgba(24, 36, 51, 0.10);
            --navy: #16385f;
            --navy-deep: #112843;
            --teal: #0f8b8d;
            --amber: #d3a24e;
            --rose: #d2675d;
            --success: #1e7d59;
            --shadow-lg: 0 26px 60px rgba(17, 40, 67, 0.12);
            --shadow-md: 0 16px 36px rgba(17, 40, 67, 0.08);
            --radius-xl: 30px;
            --radius-lg: 22px;
            --radius-md: 16px;
        }

        @keyframes fadeUp {
            from {
                opacity: 0;
                transform: translateY(16px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes floatGlow {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-8px); }
        }

        html, body, [class*="css"] {
            font-family: 'Manrope', sans-serif;
            color: var(--ink);
        }

        .stApp {
            background:
                radial-gradient(circle at 0% 0%, rgba(15, 139, 141, 0.13), transparent 24%),
                radial-gradient(circle at 100% 0%, rgba(211, 162, 78, 0.18), transparent 24%),
                linear-gradient(180deg, #f8f3ea 0%, #f2ecdf 54%, #eee5d7 100%);
        }

        .main .block-container {
            max-width: 1340px;
            padding-top: 1.4rem;
            padding-bottom: 3rem;
        }

        .main .block-container > div {
            row-gap: 0.45rem;
        }

        h1, h2, h3, .hero-title, .section-title {
            font-family: 'Sora', sans-serif !important;
            color: var(--navy-deep) !important;
            letter-spacing: -0.035em;
        }

        p, label, .stCaption, .stMarkdown, .stText {
            color: var(--ink);
        }

        section[data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(10, 27, 47, 0.98) 0%, rgba(19, 50, 83, 0.98) 100%) !important;
            border-right: 1px solid rgba(255,255,255,0.06);
        }

        section[data-testid="stSidebar"] * {
            color: #f6f8fb;
        }

        .side-brand {
            position: relative;
            overflow: hidden;
            background: linear-gradient(160deg, rgba(255,255,255,0.12), rgba(255,255,255,0.04));
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 26px;
            padding: 1.25rem 1rem;
            margin-bottom: 1rem;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
        }

        .side-brand::after {
            content: "";
            position: absolute;
            top: -30px;
            right: -40px;
            width: 140px;
            height: 140px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(211,162,78,0.35), transparent 65%);
            animation: floatGlow 6s ease-in-out infinite;
        }

        .side-brand .eyebrow {
            font-size: 0.72rem;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: rgba(246, 248, 251, 0.72);
            font-weight: 700;
        }

        .side-brand .title {
            font-family: 'Sora', sans-serif;
            font-size: 1.45rem;
            margin-top: 0.4rem;
            color: #ffffff;
        }

        .side-brand .desc {
            margin-top: 0.55rem;
            color: rgba(246, 248, 251, 0.74);
            line-height: 1.55;
            font-size: 0.92rem;
        }

        .sidebar-note {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 18px;
            padding: 0.95rem 1rem;
            color: rgba(246, 248, 251, 0.88);
            font-size: 0.87rem;
            line-height: 1.6;
        }

        .side-map {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin: 0.65rem 0 1rem;
        }

        .side-map-chip {
            padding: 0.44rem 0.7rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
            color: rgba(246, 248, 251, 0.84);
            font-size: 0.76rem;
            font-weight: 700;
        }

        div[role="radiogroup"] > label {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 15px;
            padding: 0.72rem 0.9rem;
            margin-bottom: 0.45rem;
            transition: all 0.18s ease;
        }

        div[role="radiogroup"] > label:hover {
            background: rgba(255,255,255,0.10);
            border-color: rgba(255,255,255,0.18);
            transform: translateX(2px);
        }

        .app-shell {
            position: relative;
            padding: 1.1rem 1.25rem 1.35rem;
            border-radius: 32px;
            background: linear-gradient(180deg, rgba(255,255,255,0.40), rgba(255,255,255,0.18));
            border: 1px solid rgba(22, 56, 95, 0.08);
            backdrop-filter: blur(16px);
            box-shadow: var(--shadow-lg);
            margin-bottom: 1.2rem;
            animation: fadeUp 0.55s ease;
        }

        .app-shell::before {
            content: "";
            position: absolute;
            inset: 0;
            border-radius: 32px;
            pointer-events: none;
            background:
                linear-gradient(110deg, rgba(255,255,255,0.26), transparent 28%),
                radial-gradient(circle at top right, rgba(15,139,141,0.10), transparent 24%);
        }

        .topbar {
            position: sticky;
            top: 0.35rem;
            z-index: 20;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            padding: 0.9rem 1rem;
            margin-bottom: 1rem;
            border-radius: 22px;
            background: rgba(255,255,255,0.54);
            backdrop-filter: blur(14px);
            border: 1px solid rgba(22, 56, 95, 0.08);
            box-shadow: var(--shadow-md);
            animation: fadeUp 0.45s ease;
        }

        .topbar-brand {
            display: flex;
            align-items: center;
            gap: 0.9rem;
        }

        .topbar-mark {
            width: 42px;
            height: 42px;
            border-radius: 14px;
            background: linear-gradient(135deg, var(--navy), var(--teal));
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Sora', sans-serif;
            font-size: 0.95rem;
            font-weight: 800;
            box-shadow: 0 12px 26px rgba(17, 40, 67, 0.18);
        }

        .topbar-title {
            font-family: 'Sora', sans-serif;
            font-weight: 700;
            font-size: 1rem;
            color: var(--navy-deep);
        }

        .topbar-subtitle {
            font-size: 0.84rem;
            color: var(--muted);
            margin-top: 0.12rem;
        }

        .topbar-status {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            justify-content: flex-end;
        }

        .topbar-chip {
            padding: 0.48rem 0.82rem;
            border-radius: 999px;
            background: rgba(22, 56, 95, 0.06);
            border: 1px solid rgba(22, 56, 95, 0.09);
            color: var(--navy);
            font-size: 0.8rem;
            font-weight: 700;
        }

        .nav-shell {
            margin-bottom: 1rem;
            animation: fadeUp 0.5s ease;
        }

        .nav-caption {
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.18em;
            color: var(--muted);
            font-weight: 800;
            margin-bottom: 0.55rem;
        }

        div[data-testid="stHorizontalBlock"] .top-nav-host {
            width: 100%;
        }

        .top-nav-host [role="radiogroup"] {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            padding: 0.45rem;
            border-radius: 24px;
            background: rgba(255,255,255,0.42);
            border: 1px solid rgba(22, 56, 95, 0.08);
            backdrop-filter: blur(14px);
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.03);
        }

        /* Hide the primitive radio circles and default Streamlit styling */
        .top-nav-host [role="radiogroup"] [data-testid="stSelectionControlActive"],
        .top-nav-host [role="radiogroup"] [data-testid="stSelectionControlInactive"],
        .top-nav-host [role="radiogroup"] [data-testid="stWidgetLabel"] {
            display: none !important;
        }

        .top-nav-host [role="radiogroup"] > label {
            flex: 1 1 auto;
            min-width: 140px;
            margin: 0 !important;
            padding: 0.85rem 1rem !important;
            border-radius: 18px !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1) !important;
            cursor: pointer !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }

        /* Ensure the text container inside the label is styled correctly */
        .top-nav-host [role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p {
            margin: 0 !important;
            font-weight: 700 !important;
            font-size: 0.92rem !important;
            letter-spacing: 0.01em !important;
            color: var(--navy) !important;
            transition: color 0.22s ease !important;
        }

        .top-nav-host [role="radiogroup"] > label:hover {
            transform: translateY(-1px);
            background: rgba(22, 56, 95, 0.06) !important;
            border-color: rgba(22, 56, 95, 0.12) !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
        }

        /* Style for the active/selected navigation item */
        .top-nav-host [role="radiogroup"] label:has(input:checked) {
            background: linear-gradient(135deg, var(--navy), var(--teal)) !important;
            border-color: transparent !important;
            box-shadow: 0 12px 24px rgba(22, 56, 95, 0.22) !important;
            transform: translateY(-1px);
        }

        .top-nav-host [role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p {
            color: #ffffff !important;
        }

        /* Fallback for versions where :has is not preferred or data attributes are used */
        .top-nav-host [role="radiogroup"] > label[data-selected="true"] {
            background: linear-gradient(135deg, var(--navy), var(--teal)) !important;
            border-color: transparent !important;
            box-shadow: 0 12px 24px rgba(22, 56, 95, 0.22) !important;
        }

        .hero-shell {
            position: relative;
            overflow: hidden;
            padding: 1.85rem 2rem;
            border-radius: var(--radius-xl);
            background:
                linear-gradient(135deg, rgba(255,255,255,0.92), rgba(248,243,235,0.78)),
                radial-gradient(circle at top right, rgba(15,139,141,0.16), transparent 28%);
            border: 1px solid rgba(22, 56, 95, 0.08);
            box-shadow: var(--shadow-md);
            margin-bottom: 1rem;
            animation: fadeUp 0.55s ease;
        }

        .hero-shell::after {
            content: "";
            position: absolute;
            top: -44px;
            right: -24px;
            width: 240px;
            height: 240px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(211,162,78,0.22), transparent 68%);
            pointer-events: none;
        }

        .hero-kicker {
            display: inline-block;
            font-size: 0.72rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: var(--teal);
            font-weight: 800;
            margin-bottom: 0.65rem;
        }

        .hero-title {
            font-size: 2.35rem !important;
            line-height: 1.02;
            margin: 0;
            max-width: 760px;
        }

        .hero-description {
            max-width: 800px;
            color: var(--muted);
            margin-top: 0.8rem;
            line-height: 1.7;
            font-size: 1rem;
        }

        .pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 1rem;
        }

        .stat-pill {
            background: rgba(22, 56, 95, 0.06);
            border: 1px solid rgba(22, 56, 95, 0.09);
            color: var(--navy);
            border-radius: 999px;
            padding: 0.48rem 0.82rem;
            font-size: 0.82rem;
            font-weight: 700;
        }

        .section-card,
        .metric-card,
        .glass-panel {
            background: var(--panel);
            border: 1px solid rgba(22, 56, 95, 0.08);
            backdrop-filter: blur(12px);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-md);
            animation: fadeUp 0.6s ease;
        }

        .section-card {
            padding: 1.2rem 1.25rem;
            margin-top: 0.8rem;
        }

        .section-title {
            font-size: 1.16rem;
            margin-bottom: 0.22rem;
        }

        .section-subtitle {
            color: var(--muted);
            margin-bottom: 1rem;
            line-height: 1.58;
            font-size: 0.94rem;
        }

        .metric-card {
            padding: 1.15rem 1.2rem;
            min-height: 142px;
            position: relative;
            overflow: hidden;
            transition: transform 0.22s ease, box-shadow 0.22s ease;
        }

        .metric-card:hover,
        .section-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 20px 40px rgba(17, 40, 67, 0.12);
        }

        .bento-card {
            position: relative;
            overflow: hidden;
        }

        .bento-card::after {
            content: "";
            position: absolute;
            inset: auto -50px -80px auto;
            width: 160px;
            height: 160px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(15,139,141,0.09), transparent 68%);
            pointer-events: none;
        }

        .bento-tall {
            min-height: 100%;
        }

        .metric-card::before {
            content: "";
            position: absolute;
            inset: 0 auto auto 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, var(--navy), var(--teal), var(--amber));
        }

        .metric-card.tone-alert::before {
            background: linear-gradient(90deg, #d2675d, #e6a56b);
        }

        .metric-card.tone-growth::before {
            background: linear-gradient(90deg, #0f8b8d, #80c3ae);
        }

        .metric-card.tone-focus::before {
            background: linear-gradient(90deg, #16385f, #5f85bf);
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.74rem;
            font-weight: 800;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            margin-bottom: 0.78rem;
        }

        .metric-value {
            color: var(--navy-deep);
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.08;
        }

        .metric-delta {
            font-size: 0.9rem;
            font-weight: 700;
            margin-top: 0.62rem;
        }

        .metric-caption {
            color: var(--muted);
            font-size: 0.86rem;
            margin-top: 0.55rem;
            line-height: 1.45;
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(186px, 1fr));
            gap: 0.7rem;
            margin-top: 0.35rem;
        }

        .info-tile {
            background: rgba(255,255,255,0.62);
            border: 1px solid rgba(22, 56, 95, 0.08);
            border-radius: 15px;
            padding: 0.95rem 1rem;
        }

        .info-tile .k {
            color: var(--muted);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            font-weight: 800;
        }

        .info-tile .v {
            margin-top: 0.34rem;
            font-size: 1rem;
            font-weight: 700;
            color: var(--navy-deep);
        }

        .alert-item {
            background: rgba(255,255,255,0.66);
            border: 1px solid rgba(22, 56, 95, 0.08);
            border-left: 4px solid var(--amber);
            border-radius: 14px;
            padding: 0.85rem 0.9rem;
            margin-bottom: 0.62rem;
            transition: transform 0.18s ease, border-color 0.18s ease;
        }

        .alert-item:hover {
            transform: translateX(2px);
        }

        .alert-item[data-severity="CRITICAL"] {
            border-left-color: var(--rose);
        }

        .alert-item[data-severity="HIGH"] {
            border-left-color: var(--amber);
        }

        .alert-topline {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: baseline;
            margin-bottom: 0.34rem;
        }

        .alert-code {
            font-size: 0.79rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--muted);
            font-weight: 800;
        }

        .alert-message {
            color: var(--ink);
            line-height: 1.5;
        }

        .severity-badge {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.28rem 0.72rem;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .severity-critical {
            color: #8c2f2b;
            background: rgba(210,103,93,0.14);
        }

        .severity-high {
            color: #8d6320;
            background: rgba(211,162,78,0.18);
        }

        .severity-medium {
            color: #0c6176;
            background: rgba(15,139,141,0.12);
        }

        .empty-state {
            text-align: left;
            padding: 1.35rem 1.4rem;
            border-radius: var(--radius-lg);
            border: 1px dashed rgba(22, 56, 95, 0.16);
            background: rgba(255,255,255,0.54);
            color: var(--muted);
            line-height: 1.7;
        }

        .empty-state strong {
            display: block;
            color: var(--navy-deep);
            margin-bottom: 0.3rem;
            font-size: 1rem;
        }

        .mini-stat-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.7rem;
            margin-top: 0.7rem;
        }

        .mini-stat {
            padding: 0.86rem 0.92rem;
            border-radius: 15px;
            background: rgba(255,255,255,0.68);
            border: 1px solid rgba(22, 56, 95, 0.08);
            transition: transform 0.18s ease, box-shadow 0.18s ease;
        }

        .mini-stat:hover {
            transform: translateY(-1px);
            box-shadow: 0 12px 26px rgba(17, 40, 67, 0.10);
        }

        .mini-stat-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            color: var(--muted);
            font-weight: 800;
        }

        .mini-stat-value {
            margin-top: 0.45rem;
            color: var(--navy-deep);
            font-family: 'Sora', sans-serif;
            font-size: 1.16rem;
            font-weight: 700;
        }

        .mini-stat-meta {
            margin-top: 0.28rem;
            color: var(--muted);
            font-size: 0.8rem;
            line-height: 1.35;
        }

        .note-pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.72rem;
        }

        .note-pill {
            border-radius: 999px;
            padding: 0.42rem 0.72rem;
            background: rgba(22, 56, 95, 0.06);
            border: 1px solid rgba(22, 56, 95, 0.08);
            color: var(--navy);
            font-size: 0.78rem;
            font-weight: 700;
        }

        .stButton > button,
        .stDownloadButton > button {
            border-radius: 999px !important;
            background: linear-gradient(135deg, var(--navy) 0%, var(--teal) 100%) !important;
            color: #ffffff !important;
            font-weight: 800 !important;
            padding: 0.72rem 1.28rem !important;
            border: none !important;
            box-shadow: 0 14px 30px rgba(22, 56, 95, 0.18) !important;
            transition: transform 0.18s ease, box-shadow 0.18s ease !important;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 18px 34px rgba(22, 56, 95, 0.22) !important;
        }

        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox [data-baseweb="select"] > div,
        .stDateInput input,
        .stFileUploader section {
            border-radius: 14px !important;
            border: 1px solid rgba(22, 56, 95, 0.12) !important;
            background: rgba(255,255,255,0.86) !important;
        }

        .stTextInput label,
        .stTextArea label,
        .stSelectbox label,
        .stDateInput label,
        .stFileUploader label {
            font-weight: 700 !important;
            color: var(--navy-deep) !important;
        }

        [data-testid="stDataFrame"],
        [data-testid="stMetric"],
        .stAlert {
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid rgba(22, 56, 95, 0.08);
        }

        [data-testid="stPlotlyChart"] {
            border-radius: 18px;
            overflow: hidden;
            background: linear-gradient(180deg, rgba(255,255,255,0.40), rgba(255,255,255,0.18));
            padding: 0.25rem;
        }

        .js-plotly-plot .plotly .modebar {
            top: 10px !important;
            right: 8px !important;
            background: rgba(255,255,255,0.55) !important;
            border-radius: 999px !important;
            padding: 2px !important;
            backdrop-filter: blur(12px);
        }

        .element-container:has(.topbar),
        .element-container:has(.app-shell) {
            margin-bottom: 0 !important;
        }

        @media (max-width: 900px) {
            .main .block-container {
                padding-top: 1rem;
            }

            .app-shell {
                padding: 0.9rem 0.9rem 1rem;
                border-radius: 24px;
            }

            .topbar {
                flex-direction: column;
                align-items: flex-start;
            }

            .topbar-status {
                justify-content: flex-start;
            }

            .hero-title {
                font-size: 1.85rem !important;
            }

            .top-nav-host [role="radiogroup"] > label {
                min-width: 110px;
            }

            .mini-stat-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
