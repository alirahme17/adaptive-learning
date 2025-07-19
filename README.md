# Adaptive Learning Platform: Personalized Education with Local AI

![Platform Screenshot Placeholder](images/platform_screenshot.png) 
*(You can replace this with an actual screenshot of your application's dashboard or chatbot interface.)*

## Table of Contents
1.  [About the Project](#about-the-project)
2.  [Video Demonstration](#video-demonstration)
3.  [Key Features](#key-features)
4.  [Technologies Used](#technologies-used)
5.  [Setup and Installation](#setup-and-installation)
    * [Prerequisites](#prerequisites)
    * [Database Setup](#database-setup)
    * [API Keys](#api-keys)
    * [Model Downloads](#model-downloads)
    * [Installation Steps](#installation-steps)
    * [Initial Data Seeding](#initial-data-seeding)
6.  [Project Structure](#project-structure)
7.  [Usage](#usage)
8.  [Challenges Faced](#challenges-faced)
9.  [Future Enhancements](#future-enhancements)
10. [Contributing](#contributing)
11. [License](#license)
12. [Contact](#contact)

---

## 1. About the Project

The **Adaptive Learning Platform** is an innovative web application designed to personalize the educational journey for students, providing dynamic content and assessments tailored to their individual needs. Leveraging the power of local Artificial Intelligence, the platform ensures privacy and offline functionality, making advanced learning tools accessible on standard hardware. It serves as a comprehensive educational companion for students and a content management tool for doctors (teachers).

**Purpose:**
In response to the generic "one-size-fits-all" approach in traditional education, this platform aims to deliver a highly customizable learning experience. It empowers students with intelligent resources and enables educators to manage and deliver targeted content and assessments efficiently.

---

## 2. Video Demonstration

Experience the Adaptive Learning Platform in action! This video provides a comprehensive overview of its functionalities, showcasing the seamless interaction between the user interface and the integrated AI components.

**Video Description:**
* **Introduction:** Quick overview of the platform's mission.
* **User Registration & Login:** Demonstrates the personalized onboarding for Students and Doctors, including course selection.
* **Doctor Initial Setup:** Shows a Doctor uploading initial learning documents to populate the knowledge base.
* **Chatbot Interaction:** Highlights the real-time, streaming AI chatbot, its RAG capabilities, and how it answers questions from ingested documents.
* **Image-based Question Answering (OCR):** A student uploading an image with a question, and the chatbot extracting text via OCR to provide an answer.
* **AI-Generated Quizzes:**
    * A Doctor generating a contextualized quiz based on a supervised course and lesson.
    * A Student generating a private quiz for self-practice and immediately taking it.
* **Quiz Taking & Results:** Demonstrates the interactive quiz interface, submission, and the immediate display of graded results with feedback.
* **Personalized Video Recommendations:** A student receiving tailored YouTube tutorial suggestions based on their course, chapter, and exam mark.
* **User Profile & Navigation:** Brief tour of the updated UI with the left sidebar navigation.

**Watch the Demo Video:**
[🔗 **Access the Demo Video on Google Drive**](https://drive.google.com/drive/u/1/folders/15tCM4a2RPbcWCgF0g7ZGL5pDq91L1R0Q)

---

## 3. Key Features

* **Role-Based User Management:** Distinct functionalities for Students and Doctors with personalized registration fields.
* **Intelligent Local Chatbot:**
    * Powered by a **Mistral-7B LLM** running entirely on CPU (via `llama_cpp-python`).
    * **Offline Operation:** No internet required for AI inference after initial setup.
    * **Streaming Responses:** Real-time, word-by-word chatbot output.
    * **Persistent Chat History:** Conversations are saved and loaded from MySQL database.
    * **Image-to-Text (OCR):** Extract questions from images using `EasyOCR` for AI processing.
* **Retrieval Augmented Generation (RAG):**
    * **Custom Knowledge Base:** Built from uploaded PDF, TXT, DOCX learning materials, stored in `ChromaDB`.
    * **Contextual Answers:** Chatbot provides accurate, grounded responses from specific documents, filtered by student's enrolled courses.
    * **Document Management:** Doctors can ingest and delete knowledge base documents.
* **Adaptive Assessment (Quiz Management):**
    * **AI-Generated Quizzes:** LLM creates contextualized (course/lesson) MCQs, True/False, and Short Answer questions.
    * **Doctor-Initiated:** Public quizzes generated for all students.
    * **Student-Initiated:** Private quizzes generated for self-practice.
    * **Interactive Quiz Taking:** Submit answers and view immediate results with basic grading.
    * **Quiz Results Persistence:** Attempts and individual answers are saved to MySQL.
* **Personalized Video Recommendations:**
    * Students receive tailored YouTube tutorial suggestions based on their academic context (course, chapter, exam mark).
    * LLM generates precise search queries, executed via YouTube Data API.
    * Results displayed with video thumbnails in a responsive card layout.
* **Enhanced UI/UX:** Clean, intuitive design with a left sidebar navigation, centered forms, and consistent styling across all pages (implemented with pure CSS).

---

## 4. Technologies Used

* **Backend Framework:** `Python 3.x`, `Flask`
* **Database:** `MySQL` (with `Flask-MySQLdb`)
* **Large Language Model (LLM):** `Mistral-7B-Instruct-v0.2` (GGUF, Q2_K quantization)
* **LLM Runtime:** `llama_cpp-python`
* **Text Embeddings:** `sentence-transformers` (`all-MiniLM-L6-v2`)
* **Vector Database:** `ChromaDB`
* **Optical Character Recognition (OCR):** `EasyOCR`
* **External API:** `Google API Python Client` (for YouTube Data API v3)
* **Frontend:** `HTML5`, `CSS3` (Custom), `JavaScript` (`marked.js`)
* **Password Hashing:** `Werkzeug`

---

## 5. Setup and Installation

Follow these steps to get the Adaptive Learning Platform running on your local machine.

### Prerequisites
* `Python 3.8+` (ensure you're using a version compatible with `llama_cpp-python` and other libraries)
* `pip` (Python package installer)
* `MySQL Server` installed and running on your machine.
* `git` (optional, for cloning the repository)

### Database Setup
1.  **Create MySQL Database:**
    Open your MySQL client (e.g., MySQL Workbench, command line) and execute:
    ```sql
    CREATE DATABASE adaptive_learning_db;
    CREATE USER 'adaptive_learning_user'@'localhost' IDENTIFIED BY 'your_password';
    GRANT ALL PRIVILEGES ON adaptive_learning_db.* TO 'adaptive_learning_user'@'localhost';
    FLUSH PRIVILEGES;
    ```
    **Remember to replace `your_password` with a strong password.**
2.  **Update `config.py`:**
    Open `config.py` in the project root and update the MySQL connection details:
    ```python
    # config.py
    # ...
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'adaptive_learning_user'
    MYSQL_PASSWORD = 'your_password' # Use the password you set above
    MYSQL_DB = 'adaptive_learning_db'
    # ...
    ```

### API Keys
1.  **YouTube Data API Key:**
    * Go to [Google Cloud Console](https://console.cloud.google.com/).
    * Create a new project.
    * Navigate to `APIs & Services > Library`, search for "YouTube Data API v3", and **Enable** it.
    * Go to `APIs & Services > Credentials`, click `+ CREATE CREDENTIALS` and choose `API Key`.
    * **Restrict** the API key to "YouTube Data API v3" under "API restrictions". For local testing, you can leave "Application restrictions" as "None".
    * Update `config.py` with your new key:
        ```python
        # config.py
        # ...
        YOUTUBE_API_KEY = 'YOUR_ACTUAL_YOUTUBE_API_KEY_HERE'
        # ...
        ```

### Model Downloads
1.  **Mistral-7B LLM:**
    The application uses `Mistral-7B-Instruct-v0.2.Q2_K.gguf` for LLM inference.
    * Create a directory named `llm_models/` in your project root.
    * Download the model file: [mistral-7b-instruct-v0.2.Q2_K.gguf from TheBloke/Mistral-7B-Instruct-v0.2-GGUF](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/blob/main/mistral-7b-instruct-v0.2.Q2_K.gguf)
    * Place the downloaded `.gguf` file into the `llm_models/` directory.
2.  **Sentence-Transformers Embedding Model:**
    The application uses `sentence-transformers/all-MiniLM-L6-v2` for embeddings. This model will be **automatically downloaded and cached** by the `sentence-transformers` library the first time you run the app (requires internet for this first download).

### Installation Steps
1.  **Clone the Repository (if applicable) or navigate to project folder:**
    ```bash
    git clone [https://github.com/yourusername/adaptive-learning-platform.git](https://github.com/yourusername/adaptive-learning-platform.git)
    cd adaptive-learning-platform
    ```
2.  **Create a Python Virtual Environment:**
    ```bash
    python -m venv venv
    ```
3.  **Activate the Virtual Environment:**
    * **Windows:** `.\venv\Scripts\activate`
    * **macOS/Linux:** `source venv/bin/activate`
    *(Your terminal prompt should now show `(venv)` or similar.)*
4.  **Install Required Python Packages:**
    ```bash
    pip install Flask Flask-MySQLdb Werkzeug chromadb sentence-transformers pypdf python-docx google-api-python-client easyocr
    ```
5.  **Clean Cache (Recommended before first run):**
    Delete any `__pycache__` folders in your project directory (e.g., `adaptive_learning_app/__pycache__`, `models/__pycache__`). This helps avoid conflicts from previous debug sessions.

### Running the Application
1.  **Ensure Virtual Environment is Active.**
2.  **Run Flask Server:**
    ```bash
    python app.py
    ```
    * The first time running, `EasyOCR` and `sentence-transformers` will download their models. This requires internet.
    * Observe your terminal for `DEBUG:` messages confirming table creation and LLM/RAG component loading.
3.  Open your web browser and go to: `http://127.0.0.1:5000/`

### Initial Data Seeding
After running `python app.py` for the first time (which creates the database tables), you'll need to seed some initial data:

1.  **Register a Doctor User:**
    * Go to `http://127.0.0.1:5000/register`
    * Register a user with role `Doctor` (e.g., `doctor@example.com`, password `testpass`). Select at least 3 courses.
    * Complete the initial document upload page.
2.  **Seed Default Courses:**
    * **In a NEW terminal window**, activate your virtual environment.
    * Navigate to your project root.
    * Run `flask shell`.
    * Carefully paste the following script (replace `doctor@example.com` with your doctor's email if different):
        ```python
        from app import app
        from models import Course, User
        with app.app_context():
            doctor_user_obj = User.find_by_email('doctor@example.com') 
            doctor_user_id = None
            if doctor_user_obj:
                doctor_user_id = doctor_user_obj.id
            
            if not doctor_user_id:
                print("--- WARNING: Doctor user not found. Please register one first. ---")
            else:
                print(f"--- Found doctor user ID: {doctor_user_id}. Proceeding with course creation. ---")
                default_courses_data = [
                    {'name': 'Calculus I', 'description': 'Limits, derivatives, and integrals of functions.'},
                    {'name': 'Linear Algebra', 'description': 'Vectors, matrices, and linear transformations.'},
                    {'name': 'Data Structures & Algorithms', 'description': 'Fundamental concepts of data organization and efficient algorithms.'},
                    {'name': 'Object-Oriented Programming', 'description': 'Principles of OOP using Python/Java.'},
                    {'name': 'Web Development Fundamentals', 'description': 'HTML, CSS, JavaScript basics.'},
                    {'name': 'Database Systems', 'description': 'Relational databases, SQL, and database design.'},
                    {'name': 'Thermodynamics', 'description': 'Study of heat and its relation to other forms of energy.'},
                    {'name': 'Organic Chemistry I', 'description': 'Introduction to the structure, properties, and reactions of organic compounds.'},
                    {'name': 'Quantum Physics', 'description': 'Principles of quantum mechanics and its applications.'},
                    {'name': 'Machine Learning Basics', 'description': 'Introduction to supervised and unsupervised learning algorithms.'},
                ]
                print("\nAttempting to save default courses:")
                for course_data in default_courses_data:
                    course = Course(name=course_data['name'], description=course_data['description'], created_by_user_id=doctor_user_id)
                    if course.save():
                        print(f"- {course_data['name']} added.")
                    else:
                        print(f"- Failed to add {course_data['name']} (might already exist or DB error).")
                print("\nAll courses currently in DB:")
                print(Course.get_all_courses())
        ```
    * Press `Enter` twice after pasting.
    * Type `exit()` and press `Enter` to leave the shell.

---

## 6. Project Structure
adaptive_learning_app/
├── app.py                      # Main Flask application
├── config.py                   # Configuration variables
├── database.py                 # Database connection setup
├── models.py                   # Database models (User, Quiz, Question, Course, ChatMessage, QuizAttempt, etc.)
├── routes.py                   # Flask routes and view functions
├── rag_utils.py                # RAG-specific utilities (document processing, embeddings, ChromaDB interaction)
├── youtube_utils.py            # YouTube API interaction and video recommendation logic
├── test_youtube_api.py         # Standalone script for testing YouTube API (optional)
├── venv/                       # Python Virtual Environment
├── pycache/                # Python bytecode cache (can be deleted)
├── uploads/                    # Temporary storage for uploaded files
├── llm_models/                 # Stores downloaded GGUF LLM models
│   └── mistral-7b-instruct-v0.2.Q2_K.gguf
├── knowledge_base/             # Stores original source documents for RAG
├── chroma_db/                  # ChromaDB persistent storage directory
├── templates/                  # HTML template files
│   ├── base.html               # Base template for consistent layout
│   ├── index.html              # Landing page
│   ├── login.html              # User login form
│   ├── register.html           # User registration form
│   ├── doctor_dashboard.html   # Specific dashboard content for Doctor role
│   ├── student_dashboard.html  # Specific dashboard content for Student role
│   ├── profile.html            # User profile viewing and editing
│   ├── ingest_documents.html   # Doctor: upload RAG documents
│   ├── doctor_initial_setup.html # Doctor: forced initial document upload
│   ├── generate_quiz.html      # Doctor: quiz generation form
│   ├── student_generate_quiz_form.html # Student: quiz generation form
│   ├── youtube_recommend_form.html # Student: video recommendations form
│   ├── youtube_recommend_results.html # Displays video recommendations
│   ├── list_quizzes.html       # Lists quizzes
│   ├── take_quiz.html          # Student: quiz-taking page
│   ├── quiz_results.html       # Displays quiz results
│   └── chatbot.html            # Main chatbot interface
└── static/                     # Static assets (CSS, JS)
├── css/
│   └── style.css           # Custom CSS for pure CSS design
├── js/
│   └── chatbot.js          # JavaScript for chatbot interactivity


## 7. Usage

* **Access the App:** Open `http://127.0.0.1:5000/` in your browser.
* **Register:** Create a new Student or Doctor account.
* **Explore Dashboards:** Navigate through role-specific dashboards.
* **Chatbot:** Engage in conversations, upload images for OCR, or files for context.
* **Doctor Features:** Ingest documents, generate public quizzes.
* **Student Features:** Generate private quizzes, take quizzes, get video recommendations.

---

## 8. Challenges Faced

Developing this platform involved overcoming several complex challenges:

* **CPU-Only LLM Performance:** Managing responsiveness with a large model on limited hardware.
* **Database Schema Evolution:** Handling frequent changes to MySQL tables and foreign key constraints.
* **LLM Output Parsing:** Extracting structured data from free-form AI text using robust regex.
* **External API Integration:** Ensuring correct interaction with YouTube Data API and handling API key issues.
* **Frontend Design:** Implementing a clean, responsive layout using custom CSS without frameworks.
* **Flask Context Management:** Debugging interactions between streaming responses and database sessions.

For a detailed breakdown of these challenges and their solutions, please refer to the [Report (Section 5: Testing & Evaluation, Subsection 5.3: Limitations & Challenges Faced)](#).

---

## 9. Future Enhancements

* **Advanced Quiz Grading:** Implement more sophisticated LLM-based grading for short answers.
* **Student Progress Tracking & Analytics:** Comprehensive dashboards for students to view their learning journey.
* **AI-Powered Feedback:** Provide personalized, AI-generated feedback on quiz answers.
* **Teacher Content Management:** Robust UI for doctors to manage courses, lessons, and learning materials.
* **Dockerization:** Containerize the entire application for easy deployment.
* **Real-time Collaborations:** Potentially allow doctors and students to interact directly.

---

## 10. Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.

---
