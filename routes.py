# routes.py

import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app, g, Response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import User, Quiz, Question, Course, StudentGrade, StudentEnrolledCourse, DoctorSupervisedCourse, CourseYouTubeLink # All models
from rag_utils import ingest_documents_to_chroma, retrieve_relevant_chunks, initialize_rag_components, delete_from_chroma_by_source # Removed load_document
import glob
import json
import re
from youtube_utils import search_youtube_videos, recommend_youtube_videos

main_bp = Blueprint('main', __name__)

# Allowed extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'docx'}
ALLOWED_RAG_EXTENSIONS = {'pdf', 'txt', 'docx'} # Allowed extensions for RAG documents

def allowed_file(filename, allowed_set=ALLOWED_EXTENSIONS): # Now accepts optional 'allowed_set'
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_set

@main_bp.route('/')
def index():
    return render_template('index.html', title='Adaptive Learning')

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    all_courses = Course.get_all_courses()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        year_of_study = request.form.get('year_of_study') if role == 'student' else None
        major = request.form.get('major') if role == 'student' else None
        selected_course_ids = request.form.getlist('selected_courses')

        if not name or not email or not password or not role:
            flash('All core fields (Name, Email, Password, Role) are required!', 'danger')
            return redirect(url_for('main.register'))

        # Minimum Course Selection Validation
        if role == 'student':
            if len(selected_course_ids) < 5:
                flash('Students must select at least 5 courses.', 'danger')
                return render_template('register.html', courses=all_courses)
        elif role == 'doctor':
            if len(selected_course_ids) < 3:
                flash('Doctors must select at least 3 courses they supervise.', 'danger')
                return render_template('register.html', courses=all_courses)

        if User.find_by_email(email):
            flash('Email already registered!', 'danger')
            return redirect(url_for('main.register'))

        hashed_password = generate_password_hash(password)

        user_id = User.register(name, email, hashed_password, role, year_of_study, major)

        if user_id:
            courses_saved_count = 0
            if selected_course_ids:
                for course_id_str in selected_course_ids:
                    try:
                        course_id = int(course_id_str)
                        if role == 'student':
                            enrollment = StudentEnrolledCourse(user_id=user_id, course_id=course_id)
                            if enrollment.save():
                                courses_saved_count += 1
                        elif role == 'doctor':
                            supervision = DoctorSupervisedCourse(user_id=user_id, course_id=course_id)
                            if supervision.save():
                                courses_saved_count += 1
                    except ValueError:
                        print(f"DEBUG: Invalid course ID received: {course_id_str}")
                        flash(f"Invalid course selected: {course_id_str}. Skipped.", 'warning')
                    except Exception as e:
                        if "Duplicate entry" in str(e) and ("UNIQUE" in str(e) or "student_enrolled_courses" in str(e) or "doctor_supervised_courses" in str(e)):
                            print(f"DEBUG: Course {course_id_str} already associated for user {user_id}. Skipping duplicate.")
                        else:
                            print(f"ERROR: Failed to save course association for user {user_id}, course {course_id_str}: {e}")
                            flash(f"Failed to associate some courses. Error: {e}", 'warning')

            flash_message = f'Registration successful! (Associated {courses_saved_count} courses)'

            # --- AUTO-LOGIN NEWLY REGISTERED USER ---
            newly_registered_user = User.find_by_id(user_id) # Fetch the full user object
            if newly_registered_user:
                session['user_id'] = newly_registered_user.id
                session['user_email'] = newly_registered_user.email
                session['user_name'] = newly_registered_user.name
                session['user_role'] = newly_registered_user.role
                session['chat_history'] = [] # Clear chat history for new user
                flash(f'{flash_message}. You are now logged in.', 'success') # Update flash message
            else:
                flash('Registration successful, but failed to auto-login. Please log in manually.', 'warning')
                return redirect(url_for('main.login')) # Fallback to manual login

            # --- REDIRECTION BASED ON ROLE ---
            if role == 'doctor':
                # No need for session['just_registered_doctor'] flag, as they are now logged in.
                return redirect(url_for('main.doctor_initial_setup'))
            else: # For students
                return redirect(url_for('main.dashboard')) # Students go directly to dashboard

        else:
            flash('Registration failed. Please try again.', 'danger')
            return render_template('register.html', courses=all_courses) # Ensure courses are passed back

    return render_template('register.html', courses=all_courses)


@main_bp.route('/doctor_initial_setup', methods=['GET', 'POST'])
def doctor_initial_setup():
    if 'user_id' not in session:
        flash('Please log in.', 'warning')
        return redirect(url_for('main.login'))

    user_id = session['user_id']
    user_role = session.get('user_role')

    # This page is specifically for doctors right after registration
    if user_role != 'doctor':
        flash('This page is for doctor initial setup only.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Get the courses this doctor supervises
    supervised_courses = DoctorSupervisedCourse.get_supervised_courses(user_id)

    if request.method == 'POST':
        # This is where we process multiple file inputs, one for each course
        uploaded_count = 0
        failed_count = 0

        # Loop through each supervised course and check for its specific file input
        for course_dict in supervised_courses:
            course_id = course_dict['id']
            course_name = course_dict['name']

            # Form input name will be like 'document_for_course_1', 'document_for_course_2', etc.
            file_input_name = f'document_for_course_{course_id}'
            uploaded_file = request.files.get(file_input_name)

            if uploaded_file and allowed_file(uploaded_file.filename, ALLOWED_RAG_EXTENSIONS):
                filename = secure_filename(uploaded_file.filename)
                file_path = os.path.join(current_app.config['KNOWLEDGE_BASE_DIR'], filename)

                try:
                    uploaded_file.save(file_path)
                    # Ingest with the specific course_id
                    ingested_docs, ingested_chunks = ingest_documents_to_chroma([file_path], current_app.config, course_id=course_id)

                    if ingested_docs > 0:
                        flash(f"Successfully uploaded and ingested '{filename}' for '{course_name}'.", 'success')
                        uploaded_count += 1
                    else:
                        flash(f"Failed to ingest '{filename}' for '{course_name}'.", 'danger')
                        failed_count += 1

                   

                except Exception as e:
                    flash(f"Error processing file '{filename}' for '{course_name}': {e}", 'danger')
                    print(f"ERROR: Doctor initial setup - file processing for {filename}: {e}")
                    failed_count += 1
            else:
                # No file uploaded for this course, or file type not allowed
                flash(f"No valid document provided for '{course_name}' or file type not allowed. Please upload a PDF, TXT, or DOCX.", 'warning')

        if uploaded_count > 0:
            flash(f"Initial document setup complete for {uploaded_count} course(s).", 'success')
            return redirect(url_for('main.dashboard')) # Redirect to dashboard after setup
        else:
            flash("No documents were successfully uploaded. Please try again.", 'danger')
            # If they didn't upload any, keep them on this page to try again
            return render_template('doctor_initial_setup.html', supervised_courses=supervised_courses)

    # GET request: Display the form
    return render_template('doctor_initial_setup.html', supervised_courses=supervised_courses)

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.find_by_email(email)

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['user_name'] = user.name
            session['user_role'] = user.role
            # Clear previous chat history on login
            session['chat_history'] = []
            flash('Login successful!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@main_bp.route('/chatbot')
def chatbot():
    if 'user_id' not in session:
        flash('Please log in to access the chatbot.', 'warning')
        return redirect(url_for('main.login'))
    return render_template('chatbot.html', user_name=session.get('user_name'), chat_history=session.get('chat_history', []))

@main_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_email', None)
    session.pop('user_name', None)
    session.pop('user_role', None)
    #session.pop('chat_history', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@main_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('main.login'))

    user_role = session.get('user_role')
    user_name = session.get('user_name')

    if user_role == 'doctor':
        # doctor might see a summary or direct links to teacher-specific tools
        return render_template('teacher_dashboard.html', user_name=user_name, user_role=user_role)
    elif user_role == 'student':
        # Students might see links to quizzes, learning paths, etc.
        return render_template('student_dashboard.html', user_name=user_name, user_role=user_role)
    else:
        flash('Unknown user role.', 'danger')
        return redirect(url_for('main.logout')) # Log out if role is unknown


# --- START OF ORIGINAL STREAMING LOGIC ---

@main_bp.route('/api/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_message = request.form.get('message')
    uploaded_file = request.files.get('file')

    # Get chat history (this will only contain user messages from previous turns as per last fix)
    chat_history_from_session = session.get('chat_history', [])

    llm = g.llm_model
    if llm is None:
        return jsonify({'error': 'Chatbot model not loaded. Please contact support.'}), 500

    # --- RAG Logic Integration ---
    retrieved_context = []
    rag_enabled = current_app.config.get('RAG_ENABLED', False)

    if rag_enabled:
        # Retrieve relevant chunks based on the user's current message
        print(f"RAG: Attempting retrieval for query: '{user_message}'")
        retrieved_chunks = retrieve_relevant_chunks(user_message, current_app.config)

        if retrieved_chunks:
            # Concatenate retrieved content into a single context string
            # You might want to format this more nicely for the LLM
            context_strings = [chunk['content'] for chunk in retrieved_chunks]
            retrieved_context = "\n\n".join(context_strings)
            print(f"RAG: Retrieved context:\n{retrieved_context[:200]}...") # Print first 200 chars for debug
        else:
            print("RAG: No relevant context retrieved.")

    # Prepare messages for LLM, now incorporating RAG context
    messages_for_llm = []

    # Add historical context from session for conversational memory
    for msg in chat_history_from_session:
        messages_for_llm.append({"role": msg['role'], "content": msg['content']})

    # Add the current user message
    current_message_content = user_message if user_message else ""
    current_message_llm = {"role": "user", "content": current_message_content}

    file_path = None
    if uploaded_file and allowed_file(uploaded_file.filename):
        try:
            filename = secure_filename(uploaded_file.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(file_path)

            file_extension = filename.rsplit('.', 1)[1].lower()

            if file_extension in {'png', 'jpg', 'jpeg', 'gif'}:
                current_message_llm['content'] += (
                    f"\n\n[INFO: An image file '{filename}' was uploaded. "
                    "Please note that the current model (Mistral) is text-only and cannot directly 'see' the image content. "
                    "If you have a question about the image, please describe it in your message.]"
                )
            elif file_extension == 'pdf':
                current_message_llm['content'] += (
                    f"\n\n--- Content from PDF '{filename}' ---\n"
                    "[[PDF content extraction not fully implemented. "
                    "You need a library like 'pdfminer.six' to extract text from PDFs.]]"
                    "\n--- End PDF Content ---"
                )
            elif file_extension == 'txt':
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    current_message_llm['content'] += f"\n\n--- Content from TXT '{filename}' ---\n{file_content}\n--- End TXT Content ---"
                except Exception as e:
                    print(f"Error reading TXT file: {e}")
                    current_message_llm['content'] += f"\n\n[WARNING: Could not read TXT file '{filename}'. Error: {e}]"
            elif file_extension == 'docx':
                current_message_llm['content'] += (
                    f"\n\n--- Content from DOCX '{filename}' ---\n"
                    "[[DOCX content extraction not fully implemented. "
                    "You need a library like 'python-docx' to extract text from DOCX files.]]"
                    "\n--- End DOCX Content ---"
                )
            else:
                current_message_llm['content'] += f"\n\n[INFO: A file of type .{file_extension} was uploaded.]"

        except Exception as e:
            print(f"Error saving/processing file: {e}")
            return jsonify({'error': 'File upload failed.'}), 500
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

    # --- Construct the final prompt for the LLM ---
    # This is where the magic happens: context is added to the prompt
    final_user_prompt = current_message_llm['content']
    if retrieved_context:
        # Instruct the LLM to use the provided context
        system_instruction = (
            "You are an intelligent assistant. Answer the user's question ONLY based on the provided context. "
            "If the answer cannot be found in the context, state that you don't have enough information "
            "from the provided context and then try to answer based on your general knowledge if possible. "
            "Be concise and helpful.\n\n"
            "Context:\n" + retrieved_context + "\n\n"
            "Question: "
        )
        messages_for_llm = [{"role": "system", "content": system_instruction}] + messages_for_llm
        # The user's direct question might now be at the end of the system instruction or as a separate user message.
        # Given Mistral's chat template, it usually works best with "user" role.
        # So, we append the RAG context to the *current user message* content.
        current_message_llm['content'] = final_user_prompt
    else:
        # If no context, just a general instruction (or none if model handles it)
        system_instruction = "You are an intelligent assistant. Answer the user's question directly and concisely."
        messages_for_llm = [{"role": "system", "content": system_instruction}] + messages_for_llm
        current_message_llm['content'] = final_user_prompt # Still include original message

    messages_for_llm.append(current_message_llm) # Add the current user message (with context if applicable)

    # Create a copy of the app context for use in the generator
    app = current_app._get_current_object()

    def generate_response_stream():
        full_bot_response = ""
        try:
            stream = llm.create_chat_completion(
                messages=messages_for_llm,
                max_tokens=app.config['LLM_N_CTX'] - len(current_message_llm['content']) - 100,
                temperature=0.7,
                top_p=0.9,
                stream=True
            )

            for chunk in stream:
                delta_content = chunk['choices'][0]['delta'].get('content', '')
                full_bot_response += delta_content
                yield delta_content

        except Exception as e:
            print(f"ERROR: generate_response_stream: LLM generation error during streaming: {e}")
            yield f"\n\n[ERROR: An error occurred during chatbot generation: {e}]"
        finally:
            # Update session after streaming is complete
            with app.app_context():
                chat_history = session.get('chat_history', [])
                chat_history.append({'role': 'assistant', 'content': full_bot_response})
                session['chat_history'] = chat_history
                session.modified = True

    return Response(generate_response_stream(), mimetype='text/plain')

@main_bp.route('/api/clear_chat', methods=['POST'])
def clear_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    session['chat_history'] = []
    session.modified = True # Explicitly mark session as modified
    flash('Chat history cleared successfully!', 'success') # Optional flash message
    return jsonify({'message': 'Chat history cleared'}), 200


@main_bp.route('/ingest_documents', methods=['GET', 'POST'])
def ingest_documents():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('main.login'))

    # Only allow doctors to access this page
    if session.get('user_role') != 'doctor':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.chatbot')) # Redirect non-doctors to chatbot

    if not current_app.config['RAG_ENABLED']:
        flash('RAG functionality is disabled in configuration. Cannot ingest documents.', 'danger')
        return redirect(url_for('main.chatbot'))


    if request.method == 'POST':
        if 'documents' not in request.files:
            flash('No document files selected!', 'danger')
            return redirect(request.url) # Redirect back to the form

        uploaded_files = request.files.getlist('documents')
        if not uploaded_files or uploaded_files[0].filename == '': # Check if the list is empty or contains an empty file input
            flash('No selected files', 'danger')
            return redirect(request.url)

        files_to_ingest = []
        saved_filenames = []

        for uploaded_file in uploaded_files:
            if uploaded_file and allowed_file(uploaded_file.filename, ALLOWED_RAG_EXTENSIONS):
                filename = secure_filename(uploaded_file.filename)
                # Save the uploaded file to the KNOWLEDGE_BASE_DIR
                file_path = os.path.join(current_app.config['KNOWLEDGE_BASE_DIR'], filename)
                try:
                    uploaded_file.save(file_path)
                    files_to_ingest.append(file_path)
                    saved_filenames.append(filename)
                except Exception as e:
                    flash(f"Failed to save file {filename}: {e}", 'danger')
                    print(f"Error saving file {filename}: {e}")
            else:
                flash(f"File type not allowed for {uploaded_file.filename}. Only PDF, TXT, DOCX are supported.", 'warning')

        if files_to_ingest:
            ingested_docs, ingested_chunks = ingest_documents_to_chroma(files_to_ingest, current_app.config)
            flash(f"Successfully ingested {ingested_docs} document(s) with {ingested_chunks} chunks.", 'success')
        else:
            flash('No valid documents were uploaded for ingestion.', 'warning')

        return redirect(url_for('main.ingest_documents')) # Redirect to GET to show status and list

    # GET request: Display the form and list existing documents
    existing_documents = []
    try:
        # List files in the knowledge_base directory
        for ext in ALLOWED_RAG_EXTENSIONS:
            existing_documents.extend(glob.glob(os.path.join(current_app.config['KNOWLEDGE_BASE_DIR'], f'*.{ext}')))
        existing_documents = [os.path.basename(doc) for doc in existing_documents] # Get just filenames
    except Exception as e:
        print(f"Error listing knowledge base documents: {e}")
        flash('Could not list existing documents.', 'danger')

    return render_template('ingest_documents.html', existing_documents=existing_documents)


@main_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please log in to view your profile.', 'warning')
        return redirect(url_for('main.login'))

    user = User.find_by_id(session['user_id']) # Retrieve user object (not dict)
    
    if not user:
        flash('User not found. Please log in again.', 'danger')
        session.pop('user_id', None) # Clear invalid session
        return redirect(url_for('main.login'))

    # Fetch associated courses
    if user.role == 'student':
        associated_courses = StudentEnrolledCourse.get_enrolled_courses(user.id)
    elif user.role == 'doctor':
        associated_courses = DoctorSupervisedCourse.get_supervised_courses(user.id)
    else:
        associated_courses = []

    if request.method == 'POST':
        new_name = request.form.get('name')
        new_email = request.form.get('email')
        new_password = request.form.get('password')
        
        # New fields for students
        new_year_of_study = request.form.get('year_of_study') if user.role == 'student' else user.year_of_study
        new_major = request.form.get('major') if user.role == 'student' else user.major

        if not new_name or not new_email:
            flash('Name and Email are required!', 'danger')
            return redirect(url_for('main.profile'))

        if new_email != user.email:
            existing_user = User.find_by_email(new_email)
            if existing_user and existing_user.id != user.id: # Check if email belongs to *another* user
                flash('That email is already in use by another account.', 'danger')
                return redirect(url_for('main.profile'))

        # Update user in database
        db = get_db()
        cursor = db.connection.cursor()
        
        update_sql = "UPDATE users SET name = %s, email = %s, year_of_study = %s, major = %s"
        update_params = [new_name, new_email, new_year_of_study, new_major]

        if new_password:
            hashed_password = generate_password_hash(new_password)
            update_sql += ", password_hash = %s"
            update_params.append(hashed_password)

        update_sql += " WHERE id = %s"
        update_params.append(user.id)

        try:
            cursor.execute(update_sql, tuple(update_params))
            db.connection.commit()
            flash('Profile updated successfully!', 'success')

            # Update session data with new values
            session['user_name'] = new_name
            session['user_email'] = new_email
            # No need to update user.year_of_study / user.major directly in the object here,
            # as the template will fetch from DB on next GET request.

        except Exception as e:
            print(f"Error updating profile: {e}")
            db.connection.rollback()
            flash('Failed to update profile. Please try again.', 'danger')
        finally:
            cursor.close()

        return redirect(url_for('main.profile')) # Redirect to GET to show updated data

    # GET request: Pass current user data and associated courses
    return render_template('profile.html', user=user, associated_courses=associated_courses)

@main_bp.route('/generate_quiz', methods=['GET', 'POST'])
def generate_quiz():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('main.login'))

    if session.get('user_role') != 'doctor':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    user_id = session['user_id']
    supervised_courses = DoctorSupervisedCourse.get_supervised_courses(user_id)

    if not supervised_courses:
        flash('You do not supervise any courses. Please update your profile or ensure courses are added.', 'warning')
        return redirect(url_for('main.dashboard')) # Redirect if no supervised courses

    if request.method == 'POST':
        # Retrieve form data
        selected_course_id = request.form.get('course_id')
        lesson_name = request.form.get('lesson_name')
        quiz_title = request.form.get('quiz_title')
        quiz_description = request.form.get('quiz_description') # Optional
        num_questions = int(request.form.get('num_questions', 3)) # Default to 3 questions
        question_type = request.form.get('question_type') # e.g., 'mcq', 'true_false', 'short_answer'

        # Basic validation for new fields
        if not selected_course_id or not lesson_name or not quiz_title or not question_type:
            flash('Please select a course, enter a lesson name, provide a quiz title, and choose question type.', 'danger')
            return render_template('generate_quiz.html', supervised_courses=supervised_courses) # Render again with error
        
        try:
            selected_course_id = int(selected_course_id)
            selected_course_info = Course.get_course_by_id(selected_course_id)
            if not selected_course_info:
                flash('Selected course not found. Please choose from your supervised courses.', 'danger')
                return render_template('generate_quiz.html', supervised_courses=supervised_courses)
        except ValueError:
            flash('Invalid course selection.', 'danger')
            return render_template('generate_quiz.html', supervised_courses=supervised_courses)


        # --- RAG Integration for Quiz Context (Re-enabled for doctors) ---
        retrieved_context = ""
        rag_enabled = current_app.config.get('RAG_ENABLED', False) 
        source_doc_names = ["General LLM Knowledge"] # Default source if no RAG or no context retrieved

        if rag_enabled:
            # Query ChromaDB for relevant chunks based on lesson name and filtered by course_id
            print(f"DEBUG: Doctor Quiz: Attempting RAG retrieval for course_id={selected_course_id}, lesson='{lesson_name}'")
            retrieved_chunks = retrieve_relevant_chunks(
                f"{lesson_name} {selected_course_info['name']}", # Query combines lesson and course name for better relevance
                current_app.config,
                course_ids=[selected_course_id] # <--- Filter by the selected course ID
            )

            if retrieved_chunks:
                context_strings = [chunk['content'] for chunk in retrieved_chunks]
                retrieved_context = "\n\n".join(context_strings)
                # Collect actual source filenames from metadata
                source_doc_names = list(set([c['metadata']['source'] for c in retrieved_chunks if 'source' in c['metadata']]))
                print(f"DEBUG: Doctor Quiz: Retrieved context for quiz: {retrieved_context[:200]}...")
            else:
                print("DEBUG: Doctor Quiz: No relevant context retrieved for quiz generation.")
        
        # --- LLM Call to Generate Quiz Questions ---
        llm = g.llm_model
        if llm is None:
            flash('LLM model not loaded. Cannot generate quiz.', 'danger')
            return render_template('generate_quiz.html', supervised_courses=supervised_courses)

        # Construct LLM prompt for quiz generation, including context if retrieved
        prompt_template = f"""
You are an expert educator and quiz creator. Your task is to generate {num_questions} {question_type} question(s) on the topic of "{lesson_name}" within the course "{selected_course_info['name']}".

{'Here is relevant context for the quiz:' if retrieved_context else ''}
{retrieved_context if retrieved_context else ''}
{'---' if retrieved_context else ''}

Generate the questions in a clear, structured format. Each question must start with "Question:" on a new line, followed by the question text itself.

For multiple-choice questions (type 'mcq'):
Provide the question, exactly 4 options (A, B, C, D) each on a new line, and the single correct answer letter (e.g., A, B, C, or D).
Example:
Question: What is the capital of France?
A) Berlin
B) Madrid
C) Paris
D) Rome
Correct Answer: C <--- IMPORTANT: Provide ONLY the single letter (A, B, C, or D) for MCQ answers, with no additional text or explanation.

For true/false questions (type 'true_false'):
Provide the question and whether it's True or False.
Example:
Question: The Earth is flat.
Correct Answer: False <--- IMPORTANT: Provide ONLY 'True' or 'False', with no additional text or explanation.

For short-answer questions (type 'short_answer'):
Provide the question and the expected correct answer.
Example:
Question: What is photosynthesis?
Correct Answer: The process by which green plants and some other organisms convert light energy into chemical energy.

Ensure the correct answer is provided on a single line and contains ONLY the exact answer (letter, True/False, or short phrase) with no additional explanation or ambiguity.
Please generate the {num_questions} {question_type} question(s) now:
"""
        
        messages_for_llm_quiz = [
            {"role": "system", "content": "You are an expert quiz creator. Generate questions based on the provided context or general knowledge."},
            {"role": "user", "content": prompt_template}
        ]

        generated_quiz_text = ""
        try:
            print("DEBUG: Doctor Quiz Generation: Calling llm.create_chat_completion...")
            response = llm.create_chat_completion(
                messages=messages_for_llm_quiz,
                max_tokens=current_app.config['LLM_N_CTX'] - len(prompt_template) - 100,
                temperature=0.7,
                top_p=0.9,
                stream=False
            )
            generated_quiz_text = response['choices'][0]['message']['content']
            print(f"DEBUG: Doctor Quiz: Generated Text:\n", generated_quiz_text)

        except Exception as e:
            print(f"ERROR: Doctor Quiz: LLM failed to generate quiz: {e}")
            flash('Failed to generate quiz questions. Please try again.', 'danger')
            return render_template('generate_quiz.html', supervised_courses=supervised_courses)

        # --- Parsing Logic ---
        parsed_questions = []
        q_blocks = re.split(r'Question\s*(?:\d+)?(?::)?\s*', generated_quiz_text.strip(), flags=re.IGNORECASE)
        q_blocks = [block.strip() for block in q_blocks if block.strip()]

        print(f"DEBUG: Doctor Quiz: Total question blocks found by regex: {len(q_blocks)}")
        
        for block_idx, block in enumerate(q_blocks):
            block = block.strip()
            if not block: continue
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if not lines: continue

            question_text = lines[0]
            
            correct_answer_line_idx = -1
            raw_correct_answer_text = ""
            for i, line in enumerate(lines):
                if re.match(r'^(Correct\s+)?Answer\s*:', line, re.IGNORECASE):
                    correct_answer_line_idx = i
                    raw_correct_answer_text = line
                    break
            
            if correct_answer_line_idx == -1:
                print(f"DEBUG: Doctor Quiz: Block {block_idx}: 'Correct Answer:' or 'Answer:' not found. Lines: {lines}")
                continue

            correct_answer_value = re.sub(r'^(Correct\s+)?Answer\s*:', '', raw_correct_answer_text, flags=re.IGNORECASE).strip()
            
            if question_type in ['mcq', 'true_false']:
                correct_answer_parsed = correct_answer_value.split(' ')[0].strip()
            else:
                correct_answer_parsed = correct_answer_value
            
            options_lines = lines[1:correct_answer_line_idx]

            cleaned_options = []
            if question_type == 'mcq':
                for opt_line in options_lines:
                    match = re.match(r'^[A-D]\s*[).]\s*(.*)', opt_line)
                    if match:
                        cleaned_options.append(match.group(1).strip())
                    else:
                        cleaned_options.append(opt_line.strip())
                
                if len(cleaned_options) != 4:
                    print(f"DEBUG: Doctor Quiz: Block {block_idx}: Did not find exactly 4 options for MCQ ({len(cleaned_options)} found). Options: {cleaned_options}")
                    continue

            if not question_text or not correct_answer_parsed:
                print(f"DEBUG: Doctor Quiz: Block {block_idx}: Failed essential parse: Question='{question_text}', Answer='{correct_answer_parsed}'")
                continue

            if question_type == 'mcq' and not cleaned_options:
                print(f"DEBUG: Doctor Quiz: Block {block_idx}: No options parsed for MCQ question: {question_text}")
                continue


            parsed_questions.append({
                "question_text": question_text,
                "question_type": question_type,
                "options": cleaned_options,
                "correct_answer": correct_answer_parsed
            })
            print(f"DEBUG: Doctor Quiz: Successfully parsed question {block_idx}.")

        if not parsed_questions:
            print("DEBUG: Doctor Quiz: No questions were successfully parsed after all blocks. Final parsed_questions is empty.")
            flash('LLM generated no questions or parsing failed. Please check the model\'s output format.', 'warning')
            return render_template('generate_quiz.html', supervised_courses=supervised_courses)

        # Save Quiz to Database
        new_quiz = Quiz(
            title=quiz_title,
            description=quiz_description,
            created_by_user_id=user_id,
            source_documents=source_doc_names # Save actual doc names if RAG was used
        )
        quiz_id = new_quiz.save()

        if quiz_id:
            questions_saved_count = 0
            for q_data in parsed_questions:
                new_question = Question(
                    quiz_id=quiz_id,
                    question_text=q_data['question_text'],
                    question_type=q_data['question_type'],
                    options=q_data['options'],
                    correct_answer=q_data['correct_answer']
                )
                if new_question.save():
                    questions_saved_count += 1
            flash(f"Quiz '{quiz_title}' generated and saved with {questions_saved_count} questions!", 'success')
        else:
            flash('Failed to save the quiz to the database.', 'danger')

        return redirect(url_for('main.generate_quiz'))

    # GET request: Render the form
    return render_template('generate_quiz.html', supervised_courses=supervised_courses)


@main_bp.route('/recommend_videos', methods=['GET', 'POST'])
def recommend_videos():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('main.login'))

    if session.get('user_role') != 'student': # Only students can request recommendations
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))

    courses = Course.get_all_courses() # Get list of courses for the form

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        chapter_name = request.form.get('chapter_name')
        exam_mark = request.form.get('exam_mark')

        if not course_id or not chapter_name or not exam_mark:
            flash('All fields are required: Course, Chapter, and Exam Mark.', 'danger')
            return redirect(url_for('main.recommend_videos'))

        try:
            course_id = int(course_id)
            exam_mark = float(exam_mark)
            if not (0 <= exam_mark <= 100):
                raise ValueError("Mark must be between 0 and 100.")
        except ValueError as e:
            flash(f"Invalid input for Course ID or Exam Mark: {e}", 'danger')
            return redirect(url_for('main.recommend_videos'))

        # Save the grade to the database (optional, but good for tracking student data)
        new_grade = StudentGrade(
            user_id=session['user_id'],
            course_id=course_id,
            chapter_name=chapter_name,
            exam_mark=exam_mark
        )
        if not new_grade.save():
            flash("Failed to save your grade. Recommendations might be less accurate.", 'warning')

        # Call the recommendation utility function
        llm_instance = g.llm_model # Use the main LLM for recommendations
        if llm_instance is None:
            flash('LLM model not loaded. Cannot generate recommendations.', 'danger')
            return redirect(url_for('main.recommend_videos'))

        explanation, videos = recommend_youtube_videos(
            user_id=session['user_id'],
            course_id=course_id,
            chapter_name=chapter_name,
            exam_mark=exam_mark,
            llm_instance=llm_instance,
            app_config=current_app.config # Pass app.config for API key etc.
        )

        if not videos and "Error:" in explanation: # Check if error message from LLM contains "Error"
             flash(explanation, 'danger') # Display LLM-generated error as flash
             return redirect(url_for('main.recommend_videos'))

        return render_template('youtube_recommend_results.html', explanation=explanation, videos=videos)

    # GET request: Display the form
    return render_template('youtube_recommend_form.html', courses=courses)

@main_bp.route('/delete_knowledge_base_document', methods=['POST'])
def delete_knowledge_base_document():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    if session.get('user_role') != 'doctor': # Only doctors can delete documents
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    filename_to_delete = request.form.get('filename')
    if not filename_to_delete:
        return jsonify({'success': False, 'message': 'No filename provided'}), 400

    file_path = os.path.join(current_app.config['KNOWLEDGE_BASE_DIR'], filename_to_delete)

    # 1. Delete from ChromaDB
    chroma_deleted_count = 0
    try:
        chroma_deleted_count = delete_from_chroma_by_source(filename_to_delete, current_app.config)
        if chroma_deleted_count == 0: # If the function returns 0 (our internal error code)
             print(f"WARNING: No chunks reported deleted from ChromaDB for {filename_to_delete}. It might not have been indexed or an error occurred.")
             # Continue to delete file anyway, as it's the source of truth for presence in KB.
    except Exception as e:
        print(f"ERROR: Failed to delete from ChromaDB for {filename_to_delete}: {e}")
        return jsonify({'success': False, 'message': f'Failed to remove from database index: {e}'}), 500

    # 2. Delete from file system
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"DEBUG: Successfully deleted file: {file_path}")
            flash(f"'{filename_to_delete}' successfully removed from knowledge base.", 'success')
            return jsonify({'success': True, 'message': 'Document successfully removed.'}), 200
        except Exception as e:
            print(f"ERROR: Failed to delete file {file_path}: {e}")
            return jsonify({'success': False, 'message': f'Failed to delete file from server: {e}'}), 500
    else:
        flash(f"File '{filename_to_delete}' not found on server, but attempted to remove from DB index.", 'warning')
        print(f"WARNING: File not found on disk: {file_path}")
        return jsonify({'success': True, 'message': 'File not found on server, but removed from database index.'}), 200 # Consider it success if DB delete worked

@main_bp.route('/quizzes')
def list_quizzes():
    if 'user_id' not in session:
        flash('Please log in to view quizzes.', 'warning')
        return redirect(url_for('main.login'))
    
    quizzes = Quiz.get_all_quizzes() # Get all quizzes from the database

    return render_template('list_quizzes.html', quizzes=quizzes)

@main_bp.route('/student/generate_quiz', methods=['GET', 'POST'])
def student_generate_quiz():
    if 'user_id' not in session:
        flash('Please log in to generate a quiz.', 'warning')
        return redirect(url_for('main.login'))

    if session.get('user_role') != 'student':
        flash('This page is for students to generate quizzes.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    user_id = session['user_id']
    enrolled_courses = StudentEnrolledCourse.get_enrolled_courses(user_id)

    if not enrolled_courses:
        flash('You are not enrolled in any courses. Please check your profile or contact a doctor.', 'warning')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        selected_course_id = request.form.get('course_id')
        lesson_name = request.form.get('lesson_name')
        
        if not selected_course_id or not lesson_name:
            flash('Please select a course and enter a lesson/topic.', 'danger')
            return render_template('student_generate_quiz_form.html', courses=enrolled_courses)
        
        try:
            selected_course_id = int(selected_course_id)
            selected_course_info = Course.get_course_by_id(selected_course_id)
            if not selected_course_info:
                flash('Selected course not found. Please choose from the list.', 'danger')
                return render_template('student_generate_quiz_form.html', courses=enrolled_courses)
        except ValueError:
            flash('Invalid course selection.', 'danger')
            return render_template('student_generate_quiz_form.html', courses=enrolled_courses)
        
        # --- RAG Integration for Quiz Context ---
        retrieved_context = ""
        rag_enabled = current_app.config.get('RAG_ENABLED', False)
        source_doc_names = ["General LLM Knowledge"] # Default source

        if rag_enabled:
            # Retrieve documents for the selected course.
            # Currently, our RAG system only filters by course_id, not specific lessons within a course.
            # The LLM will try to use the lesson_name as a guide within the course's docs.
            print(f"DEBUG: Student Quiz: Attempting RAG retrieval for course_id={selected_course_id}, lesson='{lesson_name}'")
            retrieved_chunks = retrieve_relevant_chunks(
                f"{lesson_name} {selected_course_info['name']}", # Query combines lesson and course name
                current_app.config,
                course_ids=[selected_course_id] # Filter by selected course ID
            )

            if retrieved_chunks:
                context_strings = [chunk['content'] for chunk in retrieved_chunks]
                retrieved_context = "\n\n".join(context_strings)
                source_doc_names = list(set([c['metadata']['source'] for c in retrieved_chunks if 'source' in c['metadata']])) # Collect source filenames
                print(f"DEBUG: Student Quiz: Retrieved context for quiz: {retrieved_context[:200]}...")
            else:
                print("DEBUG: Student Quiz: No relevant context retrieved for quiz generation.")
        
        # --- LLM Call to Generate 3 Questions ---
        llm = g.llm_model # Use the main LLM (Mistral)
        if llm is None:
            flash('LLM model not loaded. Cannot generate quiz.', 'danger')
            return render_template('student_generate_quiz_form.html', courses=enrolled_courses)

        num_questions = 3 # Fixed number of questions for student quiz
        question_type = 'mcq' # Let's default to MCQ for simplicity for students initially, can add choice later

        # --- Construct LLM prompt for quiz generation (similar to doctor's, but specific) ---
        prompt_template = f"""
You are an AI tutor and quiz creator. Your task is to generate {num_questions} {question_type} question(s) on the topic of "{lesson_name}" within the course "{selected_course_info['name']}".

{'Here is relevant context for the quiz:' if retrieved_context else ''}
{retrieved_context if retrieved_context else ''}
{'---' if retrieved_context else ''}

Generate the questions in a clear, structured format. Each question must start with "Question:" on a new line, followed by the question text itself.

For 'mcq' (multiple-choice):
Provide the question, exactly 4 options (A, B, C, D) each on a new line, and the single correct answer letter (e.g., A, B, C, or D).
Example:
Question: What is the capital of France?
A) Berlin
B) Madrid
C) Paris
D) Rome
Correct Answer: C

For true/false questions (type 'true_false'):
Provide the question and whether it's True or False.
Example:
Question: The Earth is flat.
Correct Answer: False

For short-answer questions (type 'short_answer'):
Provide the question and the expected correct answer.
Example:
Question: What is photosynthesis?
Correct Answer: The process by which green plants and some other organisms convert light energy into chemical energy.

Ensure the correct answer is provided on a single line and contains ONLY the exact answer (letter, True/False, or short phrase) with no additional explanation or ambiguity.
Please generate the {num_questions} {question_type} question(s) now:
"""
        
        messages_for_llm_quiz = [
            {"role": "system", "content": "You are an expert quiz creator. Generate questions based on the provided context or general knowledge."},
            {"role": "user", "content": prompt_template}
        ]

        generated_quiz_text = ""
        try:
            print("DEBUG: Student Quiz Generation: Calling llm.create_chat_completion...")
            response = llm.create_chat_completion(
                messages=messages_for_llm_quiz,
                max_tokens=current_app.config['LLM_N_CTX'] - len(prompt_template) - 100, # Adjust max_tokens
                temperature=0.7,
                top_p=0.9,
                stream=False
            )
            generated_quiz_text = response['choices'][0]['message']['content']
            print(f"DEBUG: Student Quiz: Generated Text:\n", generated_quiz_text)

        except Exception as e:
            print(f"ERROR: Student Quiz: LLM failed to generate quiz: {e}")
            flash('Failed to generate quiz questions. Please try again.', 'danger')
            return render_template('student_generate_quiz_form.html', courses=enrolled_courses)

        # --- Parse LLM Output and Display (Not saving to DB yet for this flow) ---
        # This parsing logic is copied from generate_quiz route.
        parsed_questions = []
        q_blocks = re.split(r'Question\s*(?:\d+)?(?::)?\s*', generated_quiz_text.strip(), flags=re.IGNORECASE)
        q_blocks = [block.strip() for block in q_blocks if block.strip()]

        print(f"DEBUG: Student Quiz: Total question blocks found by regex: {len(q_blocks)}")
        
        for block_idx, block in enumerate(q_blocks):
            block = block.strip()
            if not block: continue
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if not lines: continue

            question_text = lines[0] # This should now be the actual question text
            
            correct_answer_line_idx = -1
            for i, line in enumerate(lines):
                if line.startswith("Correct Answer:"):
                    correct_answer_line_idx = i
                    break
            
            if correct_answer_line_idx == -1:
                print(f"DEBUG: Student Quiz: Block {block_idx}: 'Correct Answer:' not found. Lines: {lines}")
                continue

            raw_correct_answer = lines[correct_answer_line_idx].replace("Correct Answer:", "").strip()
            correct_answer_parsed = raw_correct_answer.split(' ')[0].strip() # For MCQ/T/F, take only first word/char
            
            options_lines = lines[1:correct_answer_line_idx] # All lines between question and correct answer

            cleaned_options = []
            if question_type == 'mcq':
                for opt_line in options_lines:
                    match = re.match(r'^[A-D]\s*[).]\s*(.*)', opt_line)
                    if match:
                        cleaned_options.append(match.group(1).strip())
                    else:
                        cleaned_options.append(opt_line.strip())
                if len(cleaned_options) != 4:
                    print(f"DEBUG: Student Quiz: Block {block_idx}: Did not find exactly 4 options for MCQ ({len(cleaned_options)} found). Options: {cleaned_options}")
                    continue

            if not question_text or not correct_answer_parsed:
                print(f"DEBUG: Student Quiz: Block {block_idx}: Failed essential parse: Question='{question_text}', Answer='{correct_answer_parsed}'")
                continue
            if question_type == 'mcq' and not cleaned_options:
                print(f"DEBUG: Student Quiz: Block {block_idx}: No options parsed for MCQ question: {question_text}")
                continue

            parsed_questions.append({
                "question_text": question_text,
                "question_type": question_type,
                "options": cleaned_options,
                "correct_answer": correct_answer_parsed
            })
            print(f"DEBUG: Student Quiz: Successfully parsed question {block_idx}.")

        if not parsed_questions:
            flash('LLM generated no questions or parsing failed. Please check the model\'s output format.', 'warning')
            return render_template('student_generate_quiz_form.html', courses=enrolled_courses)

        # Render the quiz for the student
        return render_template('take_quiz.html', quiz_questions=parsed_questions, quiz_title=f"Quiz on {selected_course_info['name']} - {lesson_name}")

    # GET request: Render the form
    return render_template('student_generate_quiz_form.html', courses=enrolled_courses)

@main_bp.route('/take_quiz/<int:quiz_id>', methods=['GET']) # Only GET for now, POST for submission will be added later
def take_quiz(quiz_id):
    if 'user_id' not in session:
        flash('Please log in to take a quiz.', 'warning')
        return redirect(url_for('main.login'))

    # Fetch the quiz details
    quiz = Quiz.get_quiz_by_id(quiz_id)
    if not quiz:
        flash('Quiz not found.', 'danger')
        return redirect(url_for('main.list_quizzes'))

    # Fetch the questions for this quiz
    quiz_questions = Question.get_questions_by_quiz_id(quiz_id)
    if not quiz_questions:
        flash('No questions found for this quiz.', 'warning')
        # Optional: Delete quiz if no questions? For now, just redirect.
        return redirect(url_for('main.list_quizzes'))

    # Ensure only students can take the quiz? Or allow everyone to view?
    # For now, if logged in, can take.

    return render_template('take_quiz.html', quiz_title=quiz['title'], quiz_questions=quiz_questions, quiz_id=quiz_id) # Pass quiz_id for potential submission later
