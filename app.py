# app.py

import os
from flask import Flask, render_template, session, g
from config import Config
from database import init_db
from models import User, Quiz, Question, Course, StudentGrade, StudentEnrolledCourse, DoctorSupervisedCourse, CourseYouTubeLink, ChatMessage, QuizAnswer, QuizAttempt
from routes import main_bp
from llama_cpp import Llama
from rag_utils import initialize_rag_components
import chromadb

app = Flask(__name__)
app.config.from_object(Config)

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['KNOWLEDGE_BASE_DIR']): 
    os.makedirs(app.config['KNOWLEDGE_BASE_DIR'])
if not os.path.exists(app.config['CHROMA_DB_PATH']): 
    os.makedirs(app.config['CHROMA_DB_PATH'])

# Initialize database and create tables
with app.app_context():
    init_db(app)
    print("DEBUG: Initializing database connection and attempting to create tables...")

    try:
        User.create_table()
        print("DEBUG: 'users' table created/verified.")
    except Exception as e:
        print(f"ERROR: Failed to create/verify 'users' table: {e}")

    try:
        Quiz.create_table()    
        print("DEBUG: 'quizzes' table created/verified.")
    except Exception as e:
        print(f"ERROR: Failed to create/verify 'quizzes' table: {e}")

    try:
        Question.create_table()
        print("DEBUG: 'questions' table created/verified.")
    except Exception as e:
        print(f"ERROR: Failed to create/verify 'questions' table: {e}")

    try:
        Course.create_table()      # NEW
        print("DEBUG: 'courses' table created/verified.")
    except Exception as e:
        print(f"ERROR: Failed to create/verify 'courses' table: {e}")

    try:
        StudentGrade.create_table() 
        print("DEBUG: 'student_grades' table created/verified.")
    except Exception as e:
        print(f"ERROR: Failed to create/verify 'student_grades' table: {e}")
        
    try: 
        StudentEnrolledCourse.create_table()
        print("DEBUG: 'student_enrolled_courses' table created/verified.")
    except Exception as e:
        print(f"ERROR: Failed to create/verify 'student_enrolled_courses' table: {e}")

    try: 
        DoctorSupervisedCourse.create_table()
        print("DEBUG: 'doctor_supervised_courses' table created/verified.")
    except Exception as e:
        print(f"ERROR: Failed to create/verify 'doctor_supervised_courses' table: {e}")

    try: 
        CourseYouTubeLink.create_table()
        print("DEBUG: 'course_youtube_links' table created/verified.")
    except Exception as e:
        print(f"ERROR: Failed to create/verify 'course_youtube_links' table: {e}")
        
    try: # ChatMessage table
        ChatMessage.create_table()
        print("DEBUG: 'chat_messages' table created/verified.")
    except Exception as e:
        print(f"ERROR: Failed to create/verify 'chat_messages' table: {e}")

    try: # QuizAttempt table
        QuizAttempt.create_table()
        print("DEBUG: 'quiz_attempts' table created/verified.")
    except Exception as e:
        print(f"ERROR: Failed to create/verify 'quiz_attempts' table: {e}")

    try: # QuizAnswer table
        QuizAnswer.create_table()
        print("DEBUG: 'quiz_answers' table created/verified.")
    except Exception as e:
        print(f"ERROR: Failed to create/verify 'quiz_answers' table: {e}")
    
    

# Global variable to store the LLM instance
llm_model = None

# Function to load the LLM model
def load_llm_model():
    global llm_model
    if llm_model is None:
        try:
            print(f"Loading LLM model from: {app.config['LLM_MODEL_PATH']}")
            llm_model = Llama(
                model_path=app.config['LLM_MODEL_PATH'],
                n_ctx=app.config['LLM_N_CTX'],
                n_batch=app.config['LLM_N_BATCH'],
                n_gpu_layers=app.config['LLM_N_GPU_LAYERS'],
                n_threads=app.config.get('LLM_N_THREADS', os.cpu_count()),
                verbose=True
            )
            print("LLM model loaded successfully!")
        except Exception as e:
            print(f"Error loading LLM model: {e}")
            llm_model = None
    
# Call LLM and RAG component initialization functions when the app starts
with app.app_context():
    load_llm_model()
    # Initialize RAG components (embedding model and ChromaDB)
    if app.config['RAG_ENABLED']:
        print("Initializing RAG components...")
        rag_initialized = initialize_rag_components(app.config)
        if not rag_initialized:
            print("WARNING: RAG components failed to initialize. RAG functionality will be unavailable.")
            app.config['RAG_ENABLED'] = False
    else:
        print("RAG is disabled in config.py.")

# Register blueprints
app.register_blueprint(main_bp)

# Before first request, ensure session is secure
@app.before_request
def make_session_permanent():
    session.permanent = True

# Make LLM accessible in routes using Flask's `g` object
@app.before_request
def before_request():
    g.llm_model = llm_model 

if __name__ == '__main__':
    app.run(debug=True)