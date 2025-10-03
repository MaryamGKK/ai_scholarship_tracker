# Streamlit admin UI to review and approve candidate scholarships
import streamlit as st
import json, os
from pathlib import Path
DATA_FILE = Path('data/candidates.json')

st.title('Scholarship Tracker — Admin Review')

if not DATA_FILE.exists():
    st.info('No candidate file found. Run the tracker to generate candidates.')
else:
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        items = json.load(f)
    approved = []
    for i, it in enumerate(items):
        with st.expander(f"{it.get('title') or 'Untitled'} — {it.get('source')}"):
            st.write(it)
            col1, col2 = st.columns(2)
            if col1.button('Approve', key=f'app_{i}'):
                approved.append(it)
            if col2.button('Reject', key=f'rej_{i}'):
                pass
    if st.button('Export approved and send email'):
        # write approved to file for main process to pick up
        out = {'approved': approved}
        Path('data').mkdir(parents=True, exist_ok=True)
        with open('data/approved.json', 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        st.success('Approved items exported to data/approved.json') 
