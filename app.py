import streamlit as st
import pandas as pd
import os
from datetime import datetime
from services.loader import MISLoader
from services.validator import DataValidator
from services.pdf_service import PDFService
from services.exception_engine import ExceptionEngine
from services.reference_service import ReferenceService
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

# --- APP LAYOUT ---
st.title("🏦 Dindigul Banking Portal")
st.markdown("### Operational Risk & MIS Intelligence System")

tabs = st.tabs(["📊 Dashboard", "⚠️ Exceptions", "📥 Ingest Data", "📄 Risk Letters", "⚙️ Config"])

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

        # Trend Chart
        trend_data = facts[facts['metric'] == 'Bus'].groupby('date')['value'].sum().reset_index()
        fig = px.area(trend_data, x='date', y='value', title="System-wide Business Growth", 
                     color_discrete_sequence=['#00338d'])
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: EXCEPTIONS (NEW) ---
with tabs[1]:
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
with tabs[2]:
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
with tabs[3]:
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
                
                # Generate unique reference
                ref_no = ReferenceService.generate("OP_RISK")
                
                # Enrich with branch and office details
                # Fetch RO details from registry
                ro_df = branches[branches['type'] == 'REGIONAL OFFICE']
                if not ro_df.empty:
                    ro_rec = ro_df.iloc[0]
                    office_details = {
                        "name": ro_rec['nameEn'],
                        "contact": ro_rec['phone'],
                        "email": ro_rec['email'],
                        "address_en": ro_rec['address'].replace('Pensioner Street, ', 'Pensioner Street, <br/>'),
                        "address_ta": ro_rec['addressTa'].replace('பென்ஷனர் தெரு, ', 'பென்ஷனர் தெரு, <br/>'),
                        "address_hi": ro_rec['addressHi'].replace('पेंशनर स्ट्रीट, ', 'पेंशनर स्ट्रीट, <br/>')
                    }
                else:
                    office_details = {
                        "name": "Dindigul",
                        "contact": "0451-2423456",
                        "email": "roplanning@iob.in",
                        "address_en": "80 Feet Road, Dindigul - 624002",
                        "address_ta": "80 அடி சாலை, திண்டுக்கல் - 624002",
                        "address_hi": "80 फीट रोड, डिंडीगुल - 624002"
                    }
                
                branch_details = selected_branch.to_dict()

                pdf_service = PDFService()
                pdf_bytes = pdf_service.render_risk_advisory(
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
                
                st.success(f"Document Registered: {ref_no}")
                st.download_button(
                    label="📥 Download Registered PDF",
                    data=pdf_bytes,
                    file_name=f"Risk_Advisory_{sol}_{pd.to_datetime(selected_date).strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )

# --- TAB 5: CONFIG ---
with tabs[4]:
    st.header("System Settings")
    st.dataframe(load_branches(), use_container_width=True)
    if st.button("Purge All Data (Factory Reset)"):
        for p in [FACTS_PATH, EXCEPTIONS_PATH, ReferenceService.REGISTRY_PATH]:
            if os.path.exists(p): os.remove(p)
        st.success("System reset complete.")
        st.cache_data.clear()
