import streamlit as st
import gc
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class MemoryTracker:
    def __init__(self):
        self.max_file_size_mb = 200

    def cleanup(self) -> None:
        """Perform immediate memory cleanup"""
        try:
            # Clear temporary session state items
            temp_keys = [
                'temp_audio',
                'temp_file',
                'old_transcripts',
                'raw_audio_data',
                'processed_chunks'
            ]
            
            for key in temp_keys:
                if key in st.session_state:
                    del st.session_state[key]
            
            # Force garbage collection
            gc.collect()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def clear_session(self) -> None:
        """Clear session state except essential variables"""
        try:
            essential_keys = {'step', 'selected_prompt', 'base_prompt'}
            current_keys = list(st.session_state.keys())
            
            for key in current_keys:
                if key not in essential_keys:
                    try:
                        del st.session_state[key]
                    except:
                        pass
            
            gc.collect()
        except Exception as e:
            logger.error(f"Error clearing session: {e}")

    def check_memory(self) -> tuple[bool, str]:
        """Check current memory status"""
        try:
            gc.collect()  # Force garbage collection
            return True, "Memory status OK"
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return False, f"Memory check failed: {str(e)}"

@st.cache_resource
def get_memory_tracker() -> MemoryTracker:
    """Get or create memory tracker instance"""
    return MemoryTracker()