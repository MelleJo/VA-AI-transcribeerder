import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
import gc
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self):
        self.max_file_size_mb = 500
        
    def check_file_size(self, file: UploadedFile) -> Tuple[bool, Optional[str]]:
        """Check if file size is within acceptable limits"""
        try:
            file_size = file.size  # Streamlit's UploadedFile has size attribute
            size_mb = file_size / (1024 * 1024)
            
            if size_mb > self.max_file_size_mb:
                return False, f"File too large ({size_mb:.1f}MB). Maximum size is {self.max_file_size_mb}MB"
                
            return True, None
        except Exception as e:
            logger.error(f"Error checking file size: {e}")
            return False, "Error checking file size"
    
    def cleanup(self) -> bool:
        """Force garbage collection and cleanup"""
        try:
            # Clear any large objects from memory
            if 'temp_audio' in st.session_state:
                del st.session_state.temp_audio
            if 'temp_file' in st.session_state:
                del st.session_state.temp_file
                
            # Force garbage collection
            gc.collect()
            
            return True
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return False

    @staticmethod
    def get_chunked_reader(file: UploadedFile, chunk_size: int = 8192):
        """Get a chunked reader for large files"""
        while True:
            data = file.read(chunk_size)
            if not data:
                break
            yield data