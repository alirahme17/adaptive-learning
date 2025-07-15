# config.py

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a7b3c9d1e5f2g4h6i8j0k2l4m6n8o0p2q4r6s8t0u2v4w6x8y0z2'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'Ali@70673304'  # Replace with your actual MySQL password
    MYSQL_DB = 'adaptive_learning'
    MYSQL_CURSORCLASS = 'DictCursor' # Returns rows as dictionaries, which is convenient

    UPLOAD_FOLDER = 'uploads' # Folder to store uploaded images/documents
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 16 MB max upload size

    # llama-cpp-python Configuration
    # Ensure this path is correct relative to your app.py or is an absolute path
    LLM_MODEL_PATH = "C:/Users/user/.cache/huggingface/hub/models--TheBloke--Mistral-7B-Instruct-v0.2-GGUF/snapshots/3a6fbf4a41a1d52e415a4958cde6856d34b2db93/mistral-7b-instruct-v0.2.Q2_K.gguf"
    LLM_N_CTX = 4096  # Context window size (optimized for 16GB RAM)
    LLM_N_BATCH = 256  # Batch size for prompt processing (optimized for i5 13th gen)
    LLM_N_GPU_LAYERS = 0  # Number of layers to offload to GPU (0 for CPU only, Iris Xe not suitable for LLM)
    LLM_N_THREADS = 12 # Number of threads to use for inference. Try setting this to number of physical CPU cores.
    
    
    # RAG Configuration
    KNOWLEDGE_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'knowledge_base')
    CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chroma_db') # Path for ChromaDB persistence
    EMBEDDING_MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2' # A good, small, general-purpose embedding model
    CHUNK_SIZE = 500 # Size of text chunks for embedding
    CHUNK_OVERLAP = 50 # Overlap between chunks
    RAG_TOP_K = 3 # Number of top relevant documents to retrieve for RAG
    RAG_ENABLED = True # Flag to easily enable/disable RAG functionality
    
    # YouTube API Configuration
    YOUTUBE_API_KEY = 'AIzaSyD3L3TvxKsyWFcxPoDynigzey-cWyAjakE' # <--- NEW: Replace with your actual API key
    YOUTUBE_MAX_RESULTS = 3 # Number of videos to suggest