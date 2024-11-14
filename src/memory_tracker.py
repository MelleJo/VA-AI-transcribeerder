# src/memory_tracker.py
import streamlit as st
import gc
import logging
from typing import Optional
import threading
import time

logger = logging.getLogger(__name__)

class MemoryTracker:
    def __init__(self):
        self._start_monitoring()

    def _start_monitoring(self):
        """Start background memory monitoring"""
        def monitor():
            while True:
                try:
                    self.cleanup()
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    logger.error(f"Error in memory monitor: {e}")
                
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

    def cleanup(self):
        """Perform memory cleanup"""
        try:
            # Clear audio processing temporary data
            if 'temp_audio' in st.session_state:
                del st.session_state.temp_audio
            
            # Clear file processing temporary data
            if 'temp_file' in st.session_state:
                del st.session_state.temp_file
            
            # Clear old transcripts if they exist
            if 'old_transcripts' in st.session_state:
                del st.session_state.old_transcripts
            
            # Force garbage collection
            gc.collect()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    @staticmethod
    def clear_session():
        """Clear session state except essential variables"""
        essential_keys = {'step', 'selected_prompt', 'base_prompt'}
        keys_to_clear = set(st.session_state.keys()) - essential_keys
        
        for key in keys_to_clear:
            try:
                del st.session_state[key]
            except:
                pass
        
        gc.collect()

# Initialize the memory tracker as a singleton
@st.cache_resource
def get_memory_tracker():
    return MemoryTracker()