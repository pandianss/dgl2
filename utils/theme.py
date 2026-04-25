import streamlit as st

def apply_theme():
    """
    Applies custom CSS for a premium banking look.
    """
    st.markdown("""
        <style>
        /* Main Container */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* Cards */
        .metric-card {
            background: white;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            border-left: 5px solid #00338d;
            margin-bottom: 1rem;
        }
        
        /* Sidebar */
        .css-1d391kg {
            background-color: #f8fafc;
        }
        
        /* Headers */
        h1, h2, h3 {
            color: #00338d;
            font-weight: 800;
        }
        
        /* Custom Table Styling */
        .styled-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
            border-radius: 8px;
            overflow: hidden;
        }
        
        /* Glassmorphism Effect */
        .glass-panel {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
            padding: 20px;
        }
        </style>
    """, unsafe_allow_html=True)
