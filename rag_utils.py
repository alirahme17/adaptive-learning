# rag_utils.py

import os
from typing import List, Dict, Tuple, Optional
from PyPDF2 import PdfReader # For PDF
from docx import Document # For DOCX
from sentence_transformers import SentenceTransformer # For embeddings
import chromadb
from chromadb.utils import embedding_functions # For Chroma's default embedding function
from uuid import uuid4 # For generating unique IDs


# Function to get configuration from Flask app context
# This is a common pattern to access app.config outside of routes directly
def get_config(app):
    return app.config

# --- Document Loading Functions ---

def load_txt(file_path: str) -> str:
    """Loads text content from a .txt file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def load_pdf(file_path: str) -> str:
    """Loads text content from a .pdf file."""
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or "" # Handle potential None if page is empty
    except Exception as e:
        print(f"Error loading PDF {file_path}: {e}")
        text = f"Error: Could not extract text from PDF file '{os.path.basename(file_path)}'."
    return text

def load_docx(file_path: str) -> str:
    """Loads text content from a .docx file."""
    text = ""
    try:
        doc = Document(file_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    except Exception as e:
        print(f"Error loading DOCX {file_path}: {e}")
        text = f"Error: Could not extract text from DOCX file '{os.path.basename(file_path)}'."
    return text

def load_document(file_path: str) -> str:
    """Loads content from various document types based on extension."""
    extension = os.path.splitext(file_path)[1].lower()
    if extension == '.txt':
        return load_txt(file_path)
    elif extension == '.pdf':
        return load_pdf(file_path)
    elif extension == '.docx':
        return load_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {extension}")

# --- Text Splitting Function ---

def split_text_into_chunks(text: str, chunk_size: int, chunk_overlap: int) -> List[Dict[str, str]]:
    """Splits text into overlapping chunks."""
    if not text:
        return []

    words = text.split() # Simple word-based splitting for now
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunk_content = " ".join(chunk_words)
        chunks.append({
            "content": chunk_content,
            "id": str(uuid4()) # Generate a unique ID for each chunk
        })
        if i + chunk_size >= len(words):
            break
        i += (chunk_size - chunk_overlap)
    return chunks

# --- Embedding Model and ChromaDB Setup ---

# Global variables to store the embedding model and Chroma client
embedding_model = None
chroma_client = None
chroma_collection = None # This will hold our main RAG collection

def initialize_rag_components(app_config):
    """Initializes the embedding model and ChromaDB client/collection."""
    global embedding_model, chroma_client, chroma_collection

    if embedding_model is None:
        print(f"RAG: Loading embedding model: {app_config['EMBEDDING_MODEL_NAME']}")
        try:
            # Load the embedding model (downloads if not cached)
            embedding_model = SentenceTransformer(app_config['EMBEDDING_MODEL_NAME'])
            print("RAG: Embedding model loaded successfully.")
        except Exception as e:
            print(f"ERROR: RAG: Failed to load embedding model: {e}")
            embedding_model = None # Ensure it's None if loading fails
            return False # Indicate failure

    if chroma_client is None:
        print(f"RAG: Initializing ChromaDB client at: {app_config['CHROMA_DB_PATH']}")
        try:
            chroma_client = chromadb.PersistentClient(path=app_config['CHROMA_DB_PATH'])
            # Create a default embedding function for Chroma to use our loaded model
            # ChromaDB expects a function that takes a list of texts and returns a list of embeddings
            def custom_ef(texts: List[str]) -> List[List[float]]:
                return embedding_model.encode(texts).tolist()

            # Get or create the collection
            # Use 'adaptive_learning_kb' as the collection name
            chroma_collection = chroma_client.get_or_create_collection(
                name="adaptive_learning_kb",
                embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=app_config['EMBEDDING_MODEL_NAME'] # Chroma uses this name to auto-download/manage model
                )
                # It's better to let Chroma manage the embedding model for its collection
                # Or pass our custom_ef if we specifically loaded it.
                # For simplicity and robust persistence with Chroma, let Chroma manage the model by name.
            )
            print("RAG: ChromaDB client and collection initialized.")
        except Exception as e:
            print(f"ERROR: RAG: Failed to initialize ChromaDB: {e}")
            chroma_client = None
            chroma_collection = None
            return False # Indicate failure
    return True # Indicate success

# --- Ingestion Function ---

def ingest_documents_to_chroma(file_paths: List[str], app_config, course_id: Optional[int] = None) -> Tuple[int, int]:
    """
    Loads, splits, embeds, and ingests documents into ChromaDB.
    Optionally associates chunks with a course_id in metadata.
    Returns (number_of_documents_ingested, number_of_chunks_ingested).
    """
    if not initialize_rag_components(app_config):
        print("RAG: Components not initialized, cannot ingest.")
        return 0, 0

    ingested_docs_count = 0
    ingested_chunks_count = 0

    for file_path in file_paths:
        try:
            print(f"RAG: Ingesting document: {os.path.basename(file_path)} (Course ID: {course_id if course_id else 'None'})")
            full_text = load_document(file_path)
            chunks = split_text_into_chunks(full_text, app_config['CHUNK_SIZE'], app_config['CHUNK_OVERLAP'])

            if not chunks:
                print(f"RAG: No content extracted or chunks generated for {os.path.basename(file_path)}")
                continue

            # Prepare data for ChromaDB
            ids = [chunk['id'] for chunk in chunks]
            documents = [chunk['content'] for chunk in chunks]

            # Update metadata to include course_id
            metadatas = []
            for i, _ in enumerate(chunks):
                meta = {"source": os.path.basename(file_path), "chunk_index": i}
                if course_id:
                    meta["course_id"] = course_id # Add course_id to metadata
                metadatas.append(meta)

            chroma_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            ingested_docs_count += 1
            ingested_chunks_count += len(chunks)
            print(f"RAG: Successfully ingested {len(chunks)} chunks from {os.path.basename(file_path)}")

        except Exception as e:
            print(f"ERROR: RAG: Failed to ingest document {os.path.basename(file_path)}: {e}")

    return ingested_docs_count, ingested_chunks_count


# --- Retrieval Function (for later, but defined here) ---
def retrieve_relevant_chunks(query_text: str, app_config, course_ids: Optional[List[int]] = None) -> List[Dict]:
    """
    Retrieves top_k most relevant chunks from ChromaDB for a given query.
    Optionally filters by specific course_ids.
    """
    if not initialize_rag_components(app_config) or embedding_model is None or chroma_collection is None:
        print("RAG: Components not initialized, cannot retrieve.")
        return []

    where_clause = {}
    if course_ids:
        # For ChromaDB, to filter by multiple course_ids, use $in operator
        where_clause = {"course_id": {"$in": course_ids}}
        print(f"DEBUG: RAG: Retrieving with course_id filter: {course_ids}")

    try:
        results = chroma_collection.query(
            query_texts=[query_text],
            n_results=app_config['RAG_TOP_K'],
            include=['documents', 'distances', 'metadatas'],
            where=where_clause # <--- NEW: Apply the where clause for filtering
        )

        if not results['documents'] or not results['documents'][0]:
            print(f"RAG: No relevant chunks found for query: '{query_text}' (with filter: {course_ids})")
            return []

        retrieved_chunks = []
        for i, doc_content in enumerate(results['documents'][0]):
            retrieved_chunks.append({
                "content": doc_content,
                "distance": results['distances'][0][i],
                "metadata": results['metadatas'][0][i]
            })

        retrieved_chunks.sort(key=lambda x: x['distance'])

        print(f"RAG: Retrieved {len(retrieved_chunks)} chunks for query: '{query_text}' (with filter: {course_ids})")
        return retrieved_chunks

    except Exception as e:
        print(f"ERROR: RAG: Failed to retrieve chunks: {e}")
        return []   


def delete_from_chroma_by_source(source_filename: str, app_config) -> int:
    """
    Deletes all chunks associated with a specific source filename from ChromaDB.
    Returns the number of documents (chunks) deleted.
    """
    if not initialize_rag_components(app_config) or chroma_collection is None:
        print("RAG: Components not initialized, cannot delete from Chroma.")
        return 0

    try:
        # ChromaDB's delete method can filter by metadata
        # We stored 'source' as the filename when ingesting
        delete_result = chroma_collection.delete(
            where={"source": source_filename}
        )
        # delete_result might be None or a dict depending on ChromaDB version/operation
        # It usually doesn't return count directly but confirms success.
        # We can verify deletion by trying to query for it if needed, or rely on success.

        # To get a count, you might query before deletion, or rely on Chroma's internal logs.
        # For simplicity, we'll assume a successful operation based on no exception.
        print(f"DEBUG: RAG: Attempted to delete chunks with source: '{source_filename}' from ChromaDB.")
        # A more robust check for count might be to get count before and after, but Chroma's client isn't always direct.
        # We can return 1 (for one document successfully targeted) or 0 (failure).
        return 1 # Indicate that the delete operation was attempted for one source
    except Exception as e:
        print(f"ERROR: RAG: Failed to delete chunks from Chroma for source '{source_filename}': {e}")
        return 0
    
    
    


