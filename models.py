# models.py

# models.py

from database import get_db
from werkzeug.security import generate_password_hash, check_password_hash
import json # For storing options as JSON

class User:
    def __init__(self, user_id=None, name=None, email=None, password_hash=None, role=None,
                 year_of_study=None, major=None): # <--- NEW: year_of_study, major
        self.id = user_id
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.year_of_study = year_of_study # <--- NEW
        self.major = major             # <--- NEW

    @staticmethod
    def create_table():
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('student', 'doctor') NOT NULL, -- <--- CHANGED: 'teacher' to 'doctor'
                year_of_study VARCHAR(50), -- <--- NEW: For students (e.g., "1st Year", "Sophomore", "PhD")
                major VARCHAR(255)       -- <--- NEW: For students (e.g., "Computer Science", "Biology")
            )
        ''')
        db.connection.commit()
        cursor.close()

    def save(self): # Added save method for User to update new fields post-registration if needed, or in register route
        db = get_db()
        cursor = db.connection.cursor()
        try:
            # This method would be used for updating user profiles.
            # For initial registration, the 'register' static method is used.
            # We'll adapt the 'register' method and potentially 'profile' update later.
            pass
        finally:
            cursor.close()

    @staticmethod
    def register(name, email, password_hash, role, year_of_study=None, major=None): # <--- UPDATED: year_of_study, major
        db = get_db()
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (name, email, password_hash, role, year_of_study, major) VALUES (%s, %s, %s, %s, %s, %s)",
                (name, email, password_hash, role, year_of_study, major)
            )
            db.connection.commit()
            return cursor.lastrowid # Return the new user's ID
        except Exception as e:
            print(f"Error registering user: {e}")
            db.connection.rollback()
            return None
        finally:
            cursor.close()

    @staticmethod
    def find_by_email(email):
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user_data = cursor.fetchone()
        cursor.close()
        if user_data:
            return User(
                user_id=user_data['id'],
                name=user_data['name'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                role=user_data['role'],
                year_of_study=user_data['year_of_study'], # <--- NEW
                major=user_data['major']             # <--- NEW
            )
        return None

    @staticmethod
    def find_by_id(user_id):
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        cursor.close()
        if user_data:
            return User(
                user_id=user_data['id'],
                name=user_data['name'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                role=user_data['role'],
                year_of_study=user_data['year_of_study'], # <--- NEW
                major=user_data['major']             # <--- NEW
            )
        return None

# --- New Quiz Models ---
class Quiz:
    def __init__(self, quiz_id=None, title=None, description=None, created_by_user_id=None,
                 source_documents=None, created_at=None):
        self.id = quiz_id
        self.title = title
        self.description = description
        self.created_by_user_id = created_by_user_id
        self.source_documents = source_documents # Stored as JSON string (list of filenames)
        self.created_at = created_at

    @staticmethod
    def create_table():
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quizzes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                created_by_user_id INT NOT NULL,
                source_documents JSON, -- Store array of filenames as JSON string
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        db.connection.commit()
        cursor.close()

    def save(self):
        db = get_db()
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO quizzes (title, description, created_by_user_id, source_documents) VALUES (%s, %s, %s, %s)",
                (self.title, self.description, self.created_by_user_id, json.dumps(self.source_documents))
            )
            db.connection.commit()
            self.id = cursor.lastrowid # Get the ID of the newly inserted quiz
            return self.id
        except Exception as e:
            print(f"Error saving quiz: {e}")
            db.connection.rollback()
            return None
        finally:
            cursor.close()

    @staticmethod
    def get_all_quizzes():
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute("SELECT q.id, q.title, q.description, u.name AS created_by, q.source_documents, q.created_at FROM quizzes q JOIN users u ON q.created_by_user_id = u.id ORDER BY q.created_at DESC")
        quizzes_data = cursor.fetchall()
        cursor.close()
        # Deserialize source_documents from JSON string to list
        for quiz in quizzes_data:
            if quiz['source_documents']:
                quiz['source_documents'] = json.loads(quiz['source_documents'])
            else:
                quiz['source_documents'] = []
        return quizzes_data

    @staticmethod
    def get_quiz_by_id(quiz_id):
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute("SELECT q.id, q.title, q.description, u.name AS created_by, q.source_documents, q.created_at FROM quizzes q JOIN users u ON q.created_by_user_id = u.id WHERE q.id = %s", (quiz_id,))
        quiz_data = cursor.fetchone()
        cursor.close()
        if quiz_data:
            if quiz_data['source_documents']:
                quiz_data['source_documents'] = json.loads(quiz_data['source_documents'])
            else:
                quiz_data['source_documents'] = []
        return quiz_data

class Question:
    def __init__(self, question_id=None, quiz_id=None, question_text=None, question_type=None,
                 options=None, correct_answer=None):
        self.id = question_id
        self.quiz_id = quiz_id
        self.question_text = question_text
        self.question_type = question_type # e.g., 'mcq', 'true_false', 'short_answer'
        self.options = options # Stored as JSON string (list of strings for MCQ)
        self.correct_answer = correct_answer # Stored as string

    @staticmethod
    def create_table():
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                quiz_id INT NOT NULL,
                question_text TEXT NOT NULL,
                question_type ENUM('mcq', 'true_false', 'short_answer') NOT NULL,
                options JSON, -- Store array of strings for MCQ options as JSON string
                correct_answer TEXT,
                FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
            )
        ''')
        db.connection.commit()
        cursor.close()

    def save(self):
        db = get_db()
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer) VALUES (%s, %s, %s, %s, %s)",
                (self.quiz_id, self.question_text, self.question_type, json.dumps(self.options) if self.options else None, self.correct_answer)
            )
            db.connection.commit()
            self.id = cursor.lastrowid
            return self.id
        except Exception as e:
            print(f"Error saving question: {e}")
            db.connection.rollback()
            return None
        finally:
            cursor.close()

    @staticmethod
    def get_questions_by_quiz_id(quiz_id):
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute("SELECT id, quiz_id, question_text, question_type, options, correct_answer FROM questions WHERE quiz_id = %s", (quiz_id,))
        questions_data = cursor.fetchall()
        cursor.close()
        # Deserialize options from JSON string to list
        for question in questions_data:
            if question['options']:
                question['options'] = json.loads(question['options'])
            else:
                question['options'] = []
        return questions_data
    
# --- New Course and Student Grade Models ---
class Course:
    def __init__(self, course_id=None, name=None, description=None, created_by_user_id=None):
        self.id = course_id
        self.name = name
        self.description = description
        self.created_by_user_id = created_by_user_id # Link to teacher who created it

    @staticmethod
    def create_table():
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                description TEXT,
                created_by_user_id INT NOT NULL,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        db.connection.commit()
        cursor.close()

    def save(self):
        db = get_db()
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO courses (name, description, created_by_user_id) VALUES (%s, %s, %s)",
                (self.name, self.description, self.created_by_user_id)
            )
            db.connection.commit()
            self.id = cursor.lastrowid
            return True
        except Exception as e:
            print(f"Error saving course: {e}")
            db.connection.rollback()
            return False
        finally:
            cursor.close()

    @staticmethod
    def get_all_courses():
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute("SELECT id, name, description FROM courses ORDER BY name ASC")
        courses_data = cursor.fetchall()
        cursor.close()
        return courses_data

    @staticmethod
    def get_course_by_id(course_id):
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute("SELECT id, name, description FROM courses WHERE id = %s", (course_id,))
        course_data = cursor.fetchone()
        cursor.close()
        return course_data

class StudentGrade:
    def __init__(self, grade_id=None, user_id=None, course_id=None, chapter_name=None, exam_mark=None, recorded_at=None):
        self.id = grade_id
        self.user_id = user_id
        self.course_id = course_id
        self.chapter_name = chapter_name
        self.exam_mark = exam_mark # e.g., a percentage or score
        self.recorded_at = recorded_at

    @staticmethod
    def create_table():
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_grades (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                course_id INT NOT NULL,
                chapter_name VARCHAR(255) NOT NULL,
                exam_mark DECIMAL(5,2) NOT NULL, -- e.g., 99.99
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')
        db.connection.commit()
        cursor.close()

    def save(self):
        db = get_db()
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO student_grades (user_id, course_id, chapter_name, exam_mark) VALUES (%s, %s, %s, %s)",
                (self.user_id, self.course_id, self.chapter_name, self.exam_mark)
            )
            db.connection.commit()
            self.id = cursor.lastrowid
            return True
        except Exception as e:
            print(f"Error saving student grade: {e}")
            db.connection.rollback()
            return False
        finally:
            cursor.close()

    @staticmethod
    def get_grades_by_user_course(user_id, course_id):
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute("SELECT chapter_name, exam_mark FROM student_grades WHERE user_id = %s AND course_id = %s ORDER BY recorded_at DESC", (user_id, course_id))
        grades_data = cursor.fetchall()
        cursor.close()
        return grades_data
    
    
class StudentEnrolledCourse:
    def __init__(self, enrollment_id=None, user_id=None, course_id=None):
        self.id = enrollment_id
        self.user_id = user_id
        self.course_id = course_id

    @staticmethod
    def create_table():
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_enrolled_courses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                course_id INT NOT NULL,
                UNIQUE(user_id, course_id), -- Ensure a student enrolls in a course only once
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')
        db.connection.commit()
        cursor.close()

    def save(self):
        db = get_db()
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO student_enrolled_courses (user_id, course_id) VALUES (%s, %s)",
                (self.user_id, self.course_id)
            )
            db.connection.commit()
            self.id = cursor.lastrowid
            return True
        except Exception as e:
            print(f"Error saving student enrollment: {e}")
            db.connection.rollback()
            return False
        finally:
            cursor.close()

    @staticmethod
    def get_enrolled_courses(user_id):
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute("SELECT c.id, c.name, c.description FROM student_enrolled_courses sec JOIN courses c ON sec.course_id = c.id WHERE sec.user_id = %s", (user_id,))
        enrolled_courses = cursor.fetchall()
        cursor.close()
        return enrolled_courses


class DoctorSupervisedCourse:
    def __init__(self, supervision_id=None, user_id=None, course_id=None):
        self.id = supervision_id
        self.user_id = user_id
        self.course_id = course_id

    @staticmethod
    def create_table():
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS doctor_supervised_courses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                course_id INT NOT NULL,
                UNIQUE(user_id, course_id), -- Ensure a doctor supervises a course only once
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')
        db.connection.commit()
        cursor.close()

    def save(self):
        db = get_db()
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO doctor_supervised_courses (user_id, course_id) VALUES (%s, %s)",
                (self.user_id, self.course_id)
            )
            db.connection.commit()
            self.id = cursor.lastrowid
            return True
        except Exception as e:
            print(f"Error saving doctor supervision: {e}")
            db.connection.rollback()
            return False
        finally:
            cursor.close()

    @staticmethod
    def get_supervised_courses(user_id):
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute("SELECT c.id, c.name, c.description FROM doctor_supervised_courses dsc JOIN courses c ON dsc.course_id = c.id WHERE dsc.user_id = %s", (user_id,))
        supervised_courses = cursor.fetchall()
        cursor.close()
        return supervised_courses


class CourseYouTubeLink:
    def __init__(self, link_id=None, course_id=None, title=None, url=None, added_by_user_id=None, added_at=None):
        self.id = link_id
        self.course_id = course_id
        self.title = title
        self.url = url
        self.added_by_user_id = added_by_user_id
        self.added_at = added_at

    @staticmethod
    def create_table():
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS course_youtube_links (
                id INT AUTO_INCREMENT PRIMARY KEY,
                course_id INT NOT NULL,
                title VARCHAR(255) NOT NULL,
                url VARCHAR(255) UNIQUE NOT NULL, -- Ensure unique URLs
                added_by_user_id INT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                FOREIGN KEY (added_by_user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        db.connection.commit()
        cursor.close()

    def save(self):
        db = get_db()
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO course_youtube_links (course_id, title, url, added_by_user_id) VALUES (%s, %s, %s, %s)",
                (self.course_id, self.title, self.url, self.added_by_user_id)
            )
            db.connection.commit()
            self.id = cursor.lastrowid
            return True
        except Exception as e:
            print(f"Error saving YouTube link: {e}")
            db.connection.rollback()
            return False
        finally:
            cursor.close()

    @staticmethod
    def get_links_by_course_id(course_id):
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute("SELECT id, title, url, added_by_user_id, added_at FROM course_youtube_links WHERE course_id = %s ORDER BY added_at DESC", (course_id,))
        links = cursor.fetchall()
        cursor.close()
        return links
    
    

class ChatMessage:
    def __init__(self, message_id=None, user_id=None, role=None, content=None, timestamp=None):
        self.id = message_id
        self.user_id = user_id
        self.role = role # 'user' or 'assistant'
        self.content = content
        self.timestamp = timestamp

    @staticmethod
    def create_table():
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        db.connection.commit()
        cursor.close()

    def save(self):
        db = get_db()
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO chat_messages (user_id, role, content) VALUES (%s, %s, %s)",
                (self.user_id, self.role, self.content)
            )
            db.connection.commit()
            self.id = cursor.lastrowid
            return True
        except Exception as e:
            print(f"Error saving chat message: {e}")
            db.connection.rollback()
            return False
        finally:
            cursor.close()
    
    @staticmethod
    def get_messages_by_user_id(user_id, limit=50): # Limit to last 50 messages for performance
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute("SELECT role, content FROM chat_messages WHERE user_id = %s ORDER BY timestamp ASC LIMIT %s", (user_id, limit))
        messages = cursor.fetchall()
        cursor.close()
        return messages

    @staticmethod
    def clear_messages_by_user_id(user_id):
        db = get_db()
        cursor = db.connection.cursor()
        try:
            cursor.execute("DELETE FROM chat_messages WHERE user_id = %s", (user_id,))
            db.connection.commit()
            return True
        except Exception as e:
            print(f"Error clearing chat messages for user {user_id}: {e}")
            db.connection.rollback()
            return False
        finally:
            cursor.close()
                       
class QuizAttempt:
    def __init__(self, attempt_id=None, quiz_id=None, user_id=None, score=None, total_questions=None, submitted_at=None):
        self.id = attempt_id
        self.quiz_id = quiz_id
        self.user_id = user_id
        self.score = score
        self.total_questions = total_questions
        self.submitted_at = submitted_at

    @staticmethod
    def create_table():
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                quiz_id INT NOT NULL,
                user_id INT NOT NULL,
                score INT,
                total_questions INT,
                submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        db.connection.commit()
        cursor.close()

    def save(self):
        db = get_db()
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO quiz_attempts (quiz_id, user_id, score, total_questions) VALUES (%s, %s, %s, %s)",
                (self.quiz_id, self.user_id, self.score, self.total_questions)
            )
            db.connection.commit()
            self.id = cursor.lastrowid
            return self.id
        except Exception as e:
            print(f"Error saving quiz attempt: {e}")
            db.connection.rollback()
            return None
        finally:
            cursor.close()
    
    @staticmethod
    def get_attempts_by_user_quiz(user_id, quiz_id):
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute("SELECT score, total_questions, submitted_at FROM quiz_attempts WHERE user_id = %s AND quiz_id = %s ORDER BY submitted_at DESC", (user_id, quiz_id))
        attempts = cursor.fetchall()
        cursor.close()
        return attempts

    @staticmethod
    def get_recent_attempts_by_user(user_id, limit=5):
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute("""
            SELECT qa.id, q.title, qa.score, qa.total_questions, qa.submitted_at 
            FROM quiz_attempts qa
            JOIN quizzes q ON qa.quiz_id = q.id
            WHERE qa.user_id = %s
            ORDER BY qa.submitted_at DESC
            LIMIT %s
        """, (user_id, limit))
        attempts = cursor.fetchall()
        cursor.close()
        return attempts

class QuizAnswer:
    def __init__(self, answer_id=None, attempt_id=None, question_id=None, student_answer=None, is_correct=None):
        self.id = answer_id
        self.attempt_id = attempt_id
        self.question_id = question_id
        self.student_answer = student_answer
        self.is_correct = is_correct

    @staticmethod
    def create_table():
        db = get_db()
        cursor = db.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quiz_answers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                attempt_id INT NOT NULL,
                question_id INT NOT NULL,
                student_answer TEXT,
                is_correct BOOLEAN,
                FOREIGN KEY (attempt_id) REFERENCES quiz_attempts(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            )
        ''')
        db.connection.commit()
        cursor.close()

    def save(self):
        db = get_db()
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO quiz_answers (attempt_id, question_id, student_answer, is_correct) VALUES (%s, %s, %s, %s)",
                (self.attempt_id, self.question_id, self.student_answer, self.is_correct)
            )
            db.connection.commit()
            self.id = cursor.lastrowid
            return True
        except Exception as e:
            print(f"Error saving quiz answer: {e}")
            db.connection.rollback()
            return False
        finally:
            cursor.close()       






