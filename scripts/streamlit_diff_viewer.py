import streamlit as st
import json
from pathlib import Path

# Simple auth
def check_password():
    def password_entered():
        if st.session_state["password"] == "clara2026automation":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.caption("Demo credentials: password=clara2026automation")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()

# Main app
st.title("Clara AI - Agent Diff Viewer")
st.markdown("---")

# Account selector
accounts = list(Path("outputs/accounts").iterdir()) if Path("outputs/accounts").exists() else []
account_names = [acc.name for acc in accounts if acc.is_dir()]

if not account_names:
    st.warning("No accounts found in outputs/accounts/")
    st.stop()

selected_account = st.selectbox("📁 Select Account", account_names)

# Load data
v1_path = Path(f"outputs/accounts/{selected_account}/v1/v1.json")
v2_path = Path(f"outputs/accounts/{selected_account}/v2/v2.json")

if not v1_path.exists() or not v2_path.exists():
    st.error("v1 or v2 not found")
    st.stop()

with open(v1_path) as f:
    v1_data = json.load(f)
with open(v2_path) as f:
    v2_data = json.load(f)

# Summary metrics
st.subheader("Summary")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Version", "v1 → v2")
with col2:
    changes = sum(1 for k in v1_data if k != "questions_or_unknowns" and v1_data.get(k) != v2_data.get(k))
    st.metric("Fields Changed", changes)
with col3:
    st.metric("Account ID", selected_account)

st.markdown("---")

# Field comparison
st.subheader("Field-by-Field Comparison")

def format_value(val):
    """Pretty format JSON values"""
    if val is None:
        return "🔴 null"
    elif isinstance(val, (dict, list)):
        return json.dumps(val, indent=2)
    else:
        return str(val)

def compare_field(key, v1_val, v2_val):
    """Compare and display field"""
    v1_str = format_value(v1_val)
    v2_str = format_value(v2_val)
    
    changed = v1_str != v2_str
    
    # Skip questions_or_unknowns
    if key == "questions_or_unknowns":
        return
    
    with st.container():
        st.markdown(f"### `{key}`")
        
        if changed:
            st.markdown("**🔴 CHANGED**")
        else:
            st.markdown("**✅ No change**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**v1 (Demo)**")
            if changed and v1_val is None:
                st.error(v1_str)
            else:
                st.code(v1_str, language="json")
        
        with col2:
            st.markdown("**v2 (Onboarding)**")
            if changed:
                st.success(v2_str)
            else:
                st.code(v2_str, language="json")
        
        st.markdown("---")

# Compare all fields
for key in v1_data.keys():
    compare_field(key, v1_data.get(key), v2_data.get(key))

# Changelog
st.subheader("What Changed?")
changelog_path = Path(f"outputs/accounts/{selected_account}/changelog.txt")
if changelog_path.exists():
    with open(changelog_path) as f:
        changes = f.read().strip().split('\n')
        for change in changes:
            if "UPDATED" in change:
                field = change.split(":")[1].split("(")[0].strip()
                st.success(f"✅ {field}")

# Agent prompts side by side
st.subheader("Agent System Prompts")

v1_spec_path = Path(f"outputs/accounts/{selected_account}/v1/agent_spec.json")
v2_spec_path = Path(f"outputs/accounts/{selected_account}/v2/agent_spec.json")

if v1_spec_path.exists() and v2_spec_path.exists():
    with open(v1_spec_path) as f:
        spec1 = json.load(f)
    with open(v2_spec_path) as f:
        spec2 = json.load(f)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**v1 Prompt**")
        st.text_area("", spec1.get("system_prompt", ""), height=300, key="v1_prompt")
    
    with col2:
        st.markdown("**v2 Prompt**")
        st.text_area("", spec2.get("system_prompt", ""), height=300, key="v2_prompt")
    
    # Full spec download
    st.markdown("---")
    st.subheader("📥 Download Complete Specs")
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download v1 Agent Spec",
            json.dumps(spec1, indent=2),
            f"{selected_account}_v1_agent_spec.json"
        )
    with col2:
        st.download_button(
            "Download v2 Agent Spec",
            json.dumps(spec2, indent=2),
            f"{selected_account}_v2_agent_spec.json"
        )
