import streamlit as st
import pandas as pd
import os
from datetime import datetime
from dataclasses import asdict
from services.loader import MISLoader
from services.validator import DataValidator
from services.pdf_service import PDFService
from services.exception_engine import ExceptionEngine
from services.document_service import DocumentService, DocumentEntry, Signatory
from utils.theme import apply_theme
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="IOB Dindigul - Correspondence Engine",
    page_icon="assets/favicon.svg",
    layout="wide"
)
apply_theme()

# --- INITIALIZATION ---
FACTS_PATH = 'data/facts.parquet'
BRANCHES_PATH = 'data/branches.csv'
EXCEPTIONS_PATH = 'data/exceptions.parquet'

if not os.path.exists('data'):
    os.makedirs('data')

@st.cache_data
def load_branches():
    if os.path.exists(BRANCHES_PATH):
        df = pd.read_csv(BRANCHES_PATH)
        df['code'] = df['code'].astype(str).str.zfill(4)
        return df
    return pd.DataFrame()

@st.cache_data
def load_facts():
    if os.path.exists(FACTS_PATH):
        return pd.read_parquet(FACTS_PATH)
    return pd.DataFrame()

@st.cache_data
def load_exceptions():
    if os.path.exists(EXCEPTIONS_PATH):
        return pd.read_parquet(EXCEPTIONS_PATH)
    return pd.DataFrame()

# --- SERVICES ---
@st.cache_resource
def get_pdf_service():
    return PDFService()

@st.cache_resource
def get_doc_service():
    return DocumentService()

pdf_service = get_pdf_service()
doc_service = get_doc_service()

def get_ro_details():
    """Retrieves standard Regional Office metadata."""
    branches = load_branches()
    ro_df = branches[branches['type'] == 'REGIONAL OFFICE']
    if not ro_df.empty:
        ro_rec = ro_df.iloc[0]
        return {
            "name": ro_rec['nameEn'],
            "contact": ro_rec['phone'],
            "email": ro_rec['email'],
            "address_en": ro_rec['address'].replace('Pensioner Street, ', 'Pensioner Street, <br/>'),
            "address_ta": ro_rec['addressTa'].replace('பென்ஷனர் தெரு, ', 'பென்ஷனர் தெரு, <br/>'),
            "address_hi": ro_rec['addressHi'].replace('पेंशनर स्ट्रीट, ', 'पेंशनर स्ट्रीट, <br/>')
        }
    return {
        "name": "Dindigul", "contact": "0451-2423456", "email": "roplanning@iob.in",
        "address_en": "80 Feet Road, Dindigul - 624002",
        "address_ta": "80 அடி சாலை, திண்டுக்கல் - 624002",
        "address_hi": "80 फीट रोड, डिंडीगुल - 624002"
    }

# --- APP LAYOUT ---
st.title("🏦 Dindigul Banking Portal")
st.markdown("### Operational Risk & MIS Intelligence System")

tabs = st.tabs(["📊 Dashboard", "📝 Office Notes", "⚠️ Exceptions", "📥 Ingest Data", "📄 Risk Letters", "⚙️ Config"])

# --- TAB 1: DASHBOARD ---
with tabs[0]:
    st.header("Strategic Overview")
    facts = load_facts()
    if facts.empty:
        st.info("No data available. Please upload MIS files in the 'Ingest Data' tab.")
    else:
        latest_date = facts['date'].max()
        current_data = facts[facts['date'] == latest_date]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_bus = current_data[current_data['metric'] == 'Bus']['value'].sum()
            st.metric("Total Business", f"₹ {total_bus/100:,.2f} Cr")
        with col2:
            total_dep = current_data[current_data['metric'] == 'Total Dep']['value'].sum()
            st.metric("Total Deposits", f"₹ {total_dep/100:,.2f} Cr")
        with col3:
            total_adv = current_data[current_data['metric'] == 'Adv']['value'].sum()
            st.metric("Total Advances", f"₹ {total_adv/100:,.2f} Cr")
        with col4:
            npa = current_data[current_data['metric'] == 'NPA']['value'].sum()
            st.metric("Gross NPA", f"₹ {npa:,.2f} L", delta_color="inverse")

        # Enhanced Trend Chart: Stacked Business Composition (Crores)
        trend_metrics = ['Total Dep', 'Adv']
        trend_data = facts[facts['metric'].isin(trend_metrics)].groupby(['date', 'metric'])['value'].sum().reset_index()
        trend_data['value'] = trend_data['value'] / 100 # Normalize to Crores
        
        fig = px.area(trend_data, x='date', y='value', color='metric', 
                     title="System-wide Business Composition & Growth",
                     labels={'value': 'Volume (₹ Crores)', 'date': 'Date', 'metric': 'Component'},
                     color_discrete_map={'Total Dep': '#00338d', 'Adv': '#00a9e0'})
        
        fig.update_layout(
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=30, b=0, l=0, r=0)
        )
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: OFFICE NOTES WIZARD (NEW) ---
with tabs[1]:
    st.header("Premium Document Wizard")

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1. Document Context")
        doc_type = st.radio("Document Type", ["Internal Note", "Visit Observation", "Circular", "Memo", "Special Report", "Financial Return"], horizontal=True)
        dept = st.text_input("Department", value="PLANNING")
        
        ref_col1, ref_col2 = st.columns([3, 1])
        with ref_col1:
            ref_no = st.text_input("Reference Number", value=doc_service.generate_ref_no(doc_type, dept))
        with ref_col2:
            st.write("") # Spacer
            if st.button("🔄"): st.rerun()

        doc_date = st.date_input("Document Date", datetime.now())
        subject = st.text_area("Subject / Title", placeholder="Enter the subject of the note...")

    with col2:
        st.subheader("2. Signatories")
        # Multi-signatory builder
        st.info("Initiator is usually the creator. Reviewers appear at the bottom.")
        
        init_name = st.text_input("Initiator Name", value="Dindigul Regional Office")
        init_rank = st.text_input("Initiator Designation", value="Manager")
        
        has_reviewers = st.toggle("Add Reviewers / Approvers", value=False)
        reviewers = []
        if has_reviewers:
            num_rev = st.number_input("Number of Reviewers", 1, 3, 1)
            for i in range(num_rev):
                with st.expander(f"Reviewer {i+1}"):
                    r_name = st.text_input(f"Name {i+1}", key=f"rn_{i}")
                    r_rank = st.text_input(f"Designation {i+1}", key=f"rd_{i}")
                    reviewers.append({"name_en": r_name, "designation_en": r_rank})

    st.divider()
    st.subheader("3. Document Content")
    
    # Dynamic Content Inputs based on Doc Type
    template_name = "internal_note.html"
    extra_data = {}
    
    if doc_type == "Visit Observation":
        template_name = "visit_observation.html"
        v_col1, v_col2 = st.columns(2)
        with v_col1:
            branches = load_branches()
            branch_choice = st.selectbox("Target Branch", branches['name'].tolist() if not branches.empty else ["None"])
            visit_date = st.date_input("Visit Date", datetime.now())
        with v_col2:
            deadline = st.text_input("Compliance Deadline", value="7 working days")
            
        observations = st.text_area("Observations", height=200, placeholder="1. Cash management issues...\n2. Locker register not updated...")
        
        # Resolve branch code
        b_code = branches[branches['name'] == branch_choice]['code'].values[0] if not branches.empty else "0000"
        extra_data = {
            "branch_name": branch_choice,
            "branch_code": b_code,
            "visit_date": visit_date.strftime("%d-%m-%Y"),
            "deadline": deadline,
            "observations": observations.replace("\n", "<br>"),
            "visitor_name": init_name,
            "visitor_designation": init_rank
        }
        # Update subject for visit observation
        subject = f"Observations made during Management Visit on {visit_date.strftime('%d-%m-%Y')} - Reg."
        st.info(f"Subject Auto-generated: {subject}")
    elif doc_type == "Special Report":
        template_name = "special_report.html"
        st.info("This will generate a multi-parameter ranking report based on the latest MIS facts.")
        metric_configs = [
            {'id': 'CASA_PCT', 'label': 'CASA Mix (%)', 'higher_is_better': True},
            {'id': 'CD_Ratio', 'label': 'CD Ratio (%)', 'higher_is_better': False},
            {'id': 'SB', 'label': 'Savings Bank (SB)', 'higher_is_better': True},
            {'id': 'Adv', 'label': 'Gross Advances', 'higher_is_better': True}
        ]
        extra_data = {"is_special": True, "metric_configs": metric_configs}
    elif doc_type == "Financial Return":
        template_name = "consolidated_return.html"
        st.info("Generating regional consolidated financial position.")
        # Sample structured data for the return
        categories = [
            {
                "name": "Deposits (₹ in Crores)",
                "params": [
                    {"displayName": "Savings Bank", "val_current": 1245.20, "val_fy_start": 1120.50, "growth_fy": 124.70, "budget_month": 1300.00},
                    {"displayName": "Current Deposits", "val_current": 156.80, "val_fy_start": 140.20, "growth_fy": 16.60, "budget_month": 170.00},
                    {"displayName": "Term Deposits", "val_current": 2450.00, "val_fy_start": 2380.00, "growth_fy": 70.00, "budget_month": 2600.00}
                ]
            },
            {
                "name": "Key Ratios (%)",
                "params": [
                    {"displayName": "CASA %", "isRatio": True, "val_current": 42.50, "val_fy_start": 40.10, "growth_fy": 2.40},
                    {"displayName": "CD Ratio", "isRatio": True, "val_current": 68.20, "val_fy_start": 70.50, "growth_fy": -2.30}
                ]
            }
        ]
        extra_data = {"categories": categories}
    else:
        content_html = st.text_area("Body Content (HTML supported)", height=300, 
                                   placeholder="<p>Enter your content here...</p>")
        extra_data = {"body_html": content_html}

    if st.button("🚀 Generate & Register Document"):
        if not subject:
            st.error("Subject is required.")
        else:
            with st.spinner("Rendering Premium PDF..."):
                # Construct data
                doc_data = {
                    "ref_no": ref_no,
                    "date": doc_date.strftime("%d-%m-%Y"),
                    "title_en": subject,
                    "subject": subject,
                    "initiator": {"name_en": init_name, "designation_en": init_rank},
                    "reviewers": reviewers,
                    **extra_data
                }
                
                # Render
                if doc_type == "Special Report":
                    facts_df = load_facts()
                    pdf_bytes, _ = pdf_service.render_special_report(
                        facts_df=facts_df,
                        metric_configs=extra_data['metric_configs'],
                        ref_no=ref_no,
                        date=doc_date
                    )
                else:
                    pdf_bytes, _ = pdf_service.render_standard_document(
                        template_name, 
                        doc_data,
                        office_details=get_ro_details()
                    )
                
                # Register
                entry = DocumentEntry(
                    ref_no=ref_no,
                    date=doc_date.strftime("%Y-%m-%d"),
                    doc_type=doc_type,
                    subject=subject,
                    department=dept,
                    created_by=init_name,
                    content=doc_data
                )
                doc_service.register_document(entry)
                
                st.success(f"Document registered successfully with Ref: {ref_no}")
                st.download_button(
                    label="📥 Download Registered PDF",
                    data=pdf_bytes,
                    file_name=f"{ref_no.replace('/', '_')}.pdf",
                    mime="application/pdf"
                )

    st.divider()
    st.subheader("📋 Dispatch Register")
    history = doc_service.get_all_entries()
    if history:
        history_df = pd.DataFrame([asdict(e) for e in history])
        st.dataframe(history_df[['ref_no', 'date', 'doc_type', 'subject', 'department', 'created_by']], use_container_width=True)
    else:
        st.info("No documents registered yet.")

# --- TAB 2: EXCEPTIONS (NEW) ---
with tabs[2]:
    st.header("Risk Monitoring Console")
    exceptions = load_exceptions()
    if exceptions.empty:
        st.success("No critical exceptions identified in the current batch.")
    else:
        # Summary widgets
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Exceptions", len(exceptions))
        with col2:
            critical_count = len(exceptions[exceptions['severity'] == 'CRITICAL'])
            st.metric("Critical Alerts", critical_count)
        with col3:
            types = exceptions['type'].nunique()
            st.metric("Risk Categories", types)

        # Filtering
        severity_filter = st.multiselect("Filter Severity", ["CRITICAL", "HIGH", "MEDIUM"], default=["CRITICAL", "HIGH"])
        filtered_ex = exceptions[exceptions['severity'].isin(severity_filter)]
        
        st.dataframe(filtered_ex[['date', 'sol', 'type', 'severity', 'message']], use_container_width=True)
        
        if st.button("Generate All Critical Letters"):
            st.warning("Bulk generation is being implemented. Please use the 'Risk Letters' tab for individual reports.")

# --- TAB 3: INGEST DATA ---
with tabs[3]:
    st.header("MIS Ingestion Pipeline")
    uploaded_file = st.file_uploader("Upload MIS Excel/CSV", type=['xlsx', 'csv'])
    
    if uploaded_file:
        with st.spinner("Processing file..."):
            new_facts, errors = MISLoader.process_file(uploaded_file)
            
            if not new_facts.empty:
                valid, validation_errors = DataValidator.validate_ingestion(new_facts)
                
                # RUN EXCEPTION ENGINE
                branches = load_branches()
                new_exceptions = ExceptionEngine.scan(new_facts, branches)
                
                st.success(f"Processed {len(new_facts)} fact entries and identified {len(new_exceptions)} exceptions.")
                
                if st.button("Finalize Ingestion"):
                    # Save Facts
                    existing_facts = load_facts()
                    if not existing_facts.empty:
                        keys = ['sol', 'date', 'metric']
                        existing_facts = existing_facts.set_index(keys)
                        new_facts_idx = new_facts.set_index(keys)
                        existing_facts = existing_facts.drop(new_facts_idx.index, errors='ignore').reset_index()
                    
                    pd.concat([existing_facts, new_facts], ignore_index=True).to_parquet(FACTS_PATH)
                    
                    # Save Exceptions
                    existing_ex = load_exceptions()
                    if not existing_ex.empty:
                        keys = ['sol', 'date', 'type']
                        existing_ex = existing_ex.set_index(keys)
                        new_ex_idx = new_exceptions.set_index(keys)
                        existing_ex = existing_ex.drop(new_ex_idx.index, errors='ignore').reset_index()
                    
                    pd.concat([existing_ex, new_exceptions], ignore_index=True).to_parquet(EXCEPTIONS_PATH)
                    
                    st.success("Central Registry & Exception Logs updated!")
                    st.cache_data.clear()
            else:
                for err in errors: st.error(err)

# --- TAB 4: RISK LETTERS ---
with tabs[4]:
    st.header("Advisory Document Generator")
    branches = load_branches()
    facts = load_facts()
    exceptions = load_exceptions()
    
    if branches.empty or facts.empty:
        st.warning("System data missing.")
    else:
        # Highlight branches with exceptions
        branches_with_ex = exceptions['sol'].unique()
        
        col1, col2 = st.columns(2)
        with col1:
            # Add indicator for high-risk branches
            branch_options = branches.copy()
            branch_options['display'] = branch_options.apply(
                lambda x: f"⚠️ {x['nameEn']}" if x['code'] in branches_with_ex else x['nameEn'], axis=1
            )
            selected_display = st.selectbox("Select Target Branch", branch_options['display'].sort_values())
            selected_branch = branch_options[branch_options['display'] == selected_display].iloc[0]
            sol = selected_branch['code']
            
        with col2:
            available_dates = facts[facts['sol'] == str(sol)]['date'].unique()
            if len(available_dates) == 0:
                st.error("No MIS records.")
                available_dates = [datetime.now()]
            selected_date = st.selectbox("Business Date", sorted(available_dates, reverse=True))

        # Show branch exceptions
        branch_ex = exceptions[(exceptions['sol'] == str(sol)) & (exceptions['date'] == selected_date)]
        if not branch_ex.empty:
            with st.expander("Detected Risks for this period", expanded=True):
                for _, ex in branch_ex.iterrows():
                    st.write(f"- **[{ex['severity']}]** {ex['message']}")

        if st.button("Generate & Register Document"):
            with st.spinner("Compiling advisory payload..."):
                branch_facts = facts[(facts['sol'] == str(sol))]
                cur_metrics = branch_facts[branch_facts['date'] == selected_date].set_index('metric')['value'].to_dict()
                
                prev_dates = [d for d in available_dates if d < selected_date]
                prev_date = max(prev_dates) if prev_dates else selected_date
                prev_metrics = branch_facts[branch_facts['date'] == prev_date].set_index('metric')['value'].to_dict()
                
                # Generate unique reference via unified registry
                ref_no = doc_service.generate_ref_no("Risk Advisory", "OPRISK")
                
                # Enrich with branch and office details
                # Fetch RO details via helper
                office_details = get_ro_details()
                
                branch_details = selected_branch.to_dict()

                pdf_bytes, _ = pdf_service.render_risk_advisory(
                    sol=str(sol),
                    branch_name=selected_branch['nameEn'],
                    date=pd.to_datetime(selected_date),
                    metrics=cur_metrics,
                    prev_metrics=prev_metrics,
                    ref_no=ref_no,
                    office_details=office_details,
                    branch_details=branch_details,
                    prev_date=pd.to_datetime(prev_date)
                )

                # Register in audit trail
                doc_service.register_document(DocumentEntry(
                    ref_no=ref_no,
                    date=selected_date.strftime("%d-%m-%Y") if hasattr(selected_date, 'strftime') else str(selected_date),
                    doc_type="Risk Advisory",
                    subject=f"Operational Risk Advisory - {selected_branch['nameEn']}",
                    department="OPRISK",
                    created_by="System Auto-gen",
                    content={"sol": sol, "metrics": cur_metrics}
                ))
                
                st.success(f"Document Registered: {ref_no}")
                st.download_button(
                    label="📥 Download Registered PDF",
                    data=pdf_bytes,
                    file_name=f"Risk_Advisory_{sol}_{pd.to_datetime(selected_date).strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )

# --- TAB 5: CONFIG ---
with tabs[5]:
    st.header("System Settings")
    st.dataframe(load_branches(), use_container_width=True)
    if st.button("Purge All Data (Factory Reset)"):
        for p in [FACTS_PATH, EXCEPTIONS_PATH, "data/document_register.db"]:
            if os.path.exists(p): os.remove(p)
        st.success("System reset complete.")
        st.cache_data.clear()
