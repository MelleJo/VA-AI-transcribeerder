def convert_summaries_to_dict_format(st):
    if 'summaries' in st.session_state:
        for i, summary in enumerate(st.session_state.summaries):
            if isinstance(summary, str):
                st.session_state.summaries[i] = {
                    "type": "samenvatting",
                    "content": summary
                }
    
    # Convert old actiepunten and main points to new format
    for old_key in ['actiepunten_versions', 'main_points_versions']:
        if old_key in st.session_state:
            for item in st.session_state[old_key]:
                st.session_state.summaries.append({
                    "type": "actiepunten" if old_key.startswith("actiepunten") else "hoofdpunten",
                    "content": item
                })
            del st.session_state[old_key]