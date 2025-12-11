from flask import Flask, send_from_directory, request, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import joinedload
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, jwt_required, get_jwt, get_jwt_identity, create_access_token, create_refresh_token
from flask_cors import CORS
from datetime import datetime, timedelta
from flask_bcrypt import Bcrypt
from celery import Celery
from celery.schedules import crontab
import numpy as np
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from sentence_transformers import SentenceTransformer
import os, re, io, csv, json, faiss, uuid
from sklearn.metrics.pairwise import cosine_similarity


app = Flask(__name__, static_folder='dist')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ai_tutor.db'
app.config['JWT_SECRET_KEY'] = 'SE_Project_T-39'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(hours=168)

genai.configure(api_key="AIzaSyB2D5nQ3cjdym46LywsernhNylpDIrS0oA")
model = genai.GenerativeModel("gemini-2.0-flash")

VECTOR_DB_PATH = "vector_dbs"
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
index = faiss.IndexFlatL2(768)

app.config.update(
    broker_url="redis://localhost:6379/0",
    result_backend="redis://localhost:6379/0",
    broker_connection_retry_on_startup=True
)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)
celery = Celery(app.name, broker=app.config["broker_url"])
celery.conf.update(app.config)


celery.conf.beat_schedule = {
    "clean-expired-tokens": {
        "task": "clean_expired_blacklisted_tokens",
        "schedule": crontab(hour=0, minute=0)
    }
}
celery.conf.timezone = "UTC"


@celery.task(name="clean_expired_blacklisted_tokens")
def clean_expired_blacklisted_tokens():
    with app.app_context():
        expired_tokens = TokenBlacklist.query.filter(TokenBlacklist.expires < datetime.now()).all()
        if expired_tokens:
            for token in expired_tokens:
                db.session.delete(token)
            db.session.commit()
    return


@celery.task(name="delete_embeddings")
def delete_embeddings(content_ids, is_course_deletion=False):
    for content_id in content_ids:
        faiss_index_path = f"{VECTOR_DB_PATH}/course_{content_id}.faiss"
        id_map_path = f"{VECTOR_DB_PATH}/course_{content_id}_ids.json"
        metadata_path = f"{VECTOR_DB_PATH}/course_{content_id}_metadata.json"
        for file_path in [faiss_index_path, id_map_path, metadata_path]:
            if os.path.exists(file_path):
                os.remove(file_path)
        message= f"Course Content deleted successfully...for content {content_id}"
    if is_course_deletion:
        message = "Entire-Course content Embeddings deleted successfully..."
    return {'message': message}
    

def generate_and_store_embeddings(content_id, text):
    """Generates and stores embeddings for a given content ID."""
    try:
        # Fetch course content from DB
        content = db.session.query(CourseContent).options(joinedload(CourseContent.course)).filter_by(id=content_id).first()
        if not content:
            return {'error': f"Content ID {content_id} not found"}
        if not text.strip():
            return {'error': f"No transcript found for content {content_id}"}
        # Split text into chunks
        chunk_size = 256
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        if not chunks:
            return {'error': f"No valid text chunks for content {content_id}"}
        # Define file paths
        faiss_index_path = f"{VECTOR_DB_PATH}/course_{content_id}.faiss"
        id_map_path = f"{VECTOR_DB_PATH}/course_{content_id}_ids.json"
        metadata_path = f"{VECTOR_DB_PATH}/course_{content_id}_metadata.json"
        # Ensure directory exists
        os.makedirs(VECTOR_DB_PATH, exist_ok=True)
        # **Delete old files if they exist**
        for file_path in [faiss_index_path, id_map_path, metadata_path]:
            if os.path.exists(file_path):
                os.remove(file_path)
        # Generate embeddings in a batch
        embeddings = embed_model.encode(chunks)  # Batch encoding
        # Create FAISS index
        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)
        # Store new embeddings
        id_map = []
        metadata = {}
        for chunk, embedding in zip(chunks, embeddings):
            chunk_id = str(uuid.uuid4())
            index.add(np.array(embedding).reshape(1, -1))
            id_map.append(chunk_id)
            metadata[chunk_id] = {
                "content_id": content.id,
                "course_name": content.course.name,
                "title": content.title,
                "week": content.week,
                "chunk": chunk,
            }
        # Save FAISS index
        faiss.write_index(index, faiss_index_path)
        with open(id_map_path, "w") as f:
            json.dump(id_map, f)
        # Save metadata
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)
        return {'message': f"Embeddings generated and stored successfully for content {content.id}"}
    except Exception as e:
        return {'error': f"Error processing embeddings: {str(e)} for content {content_id}"}


@celery.task(name="extract_video_transcripts")
def extract_video_transcripts(content_id):
    with app.app_context():
        content = db.session.get(CourseContent, content_id)
        if not content:
            return {"error": "Course content not found"}
        # Extract video ID from YouTube URL
        video_id_match = re.search(r"v=([a-zA-Z0-9_-]+)", content.video_link)
        if not video_id_match:
            return {"error": "Invalid YouTube URL"}
        video_id = video_id_match.group(1)
        try:
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = " ".join([t["text"] for t in transcript_data])
        except Exception as e:
            return {"error": f"Transcript extraction failed: {str(e)}"}
        existing_transcript = CourseTranscript.query.filter_by(content_id=content.id).first()
        if existing_transcript:
            existing_transcript.transcript_text = transcript_text
        else:
            new_transcript = CourseTranscript(course_id=content.course_id, content_id=content.id, transcript_text=transcript_text)
            db.session.add(new_transcript)
        db.session.commit()
        generate_and_store_embeddings(content_id, transcript_text)
        return {"message": "Transcript extracted and stored successfully"}
    
    
def schedule_grading_task(assignment_id, due_date):
    eta = due_date
    check_answers.apply_async(args=[assignment_id], eta=eta)


@celery.task(name="evaluate_assignments")
def check_answers(assignment_id):
    with app.app_context():
        assignment = Assignment.query.get(assignment_id)
        if not assignment:
            return {'error': 'Assignment not found'}
        questions = AssignmentQuestion.query.filter_by(assignment_id=assignment_id).all()
        answers = StudentAnswer.query.filter_by(assignment_id=assignment_id).all()
        correct_answers = {q.id: q.correct_answer for q in questions}
        for answer in answers:
            if answer.question_id in correct_answers:
                answer.is_correct = (answer.selected_answer == correct_answers[answer.question_id])
        db.session.commit()
        return {'message': 'Student answers evaluated successfully'}


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # student, support_staff, admin, manager, developer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    enrollments = db.relationship('StudentEnrollment', back_populates='student', cascade="all, delete-orphan")
    support_courses = db.relationship('SupportStaff', back_populates='staff', cascade="all, delete-orphan")
    chat_sessions = db.relationship('ChatSession', back_populates='user', cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def generate_access_token(self):
        return create_access_token(identity=str(self.id))
    
    def generate_refresh_token(self):
        return create_refresh_token(identity=str(self.id))
    

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    prof = db.Column(db.String(100), nullable=False)
    
    contents = db.relationship('CourseContent', back_populates='course', cascade="all, delete-orphan")
    enrollments = db.relationship('StudentEnrollment', back_populates='course', cascade="all, delete-orphan")
    support_staff = db.relationship('SupportStaff', back_populates='course', cascade="all, delete-orphan")
    transcripts = db.relationship('CourseTranscript', back_populates='course', cascade="all, delete-orphan")
    assignments = db.relationship('Assignment', back_populates='course', cascade="all, delete-orphan")
    

class CourseContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    week = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    video_link = db.Column(db.String(200), nullable=False)

    course = db.relationship('Course', back_populates='contents')
    transcripts = db.relationship('CourseTranscript', back_populates='content', cascade="all, delete-orphan")


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    week = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)

    course = db.relationship('Course', back_populates='assignments')
    questions = db.relationship('AssignmentQuestion', back_populates='assignment', cascade="all, delete-orphan")
    answers = db.relationship('StudentAnswer', back_populates='assignment', cascade="all, delete-orphan")


class AssignmentQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # "mcq", "string"
    
    # Only used for MCQ-type questions
    choices = db.Column(db.JSON, nullable=True)  # Stores choices as JSON array
    correct_answer = db.Column(db.Text, nullable=True)

    assignment = db.relationship('Assignment', back_populates='questions')
    answers = db.relationship('StudentAnswer', back_populates='question', cascade="all, delete-orphan")


class StudentAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('assignment_question.id'), nullable=False)
    selected_answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True)

    student = db.relationship('User', backref='answers')
    assignment = db.relationship('Assignment', back_populates='answers')
    question = db.relationship('AssignmentQuestion', back_populates='answers')


class StudentEnrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved = db.Column(db.Boolean, default=False)
    approved_at = db.Column(db.DateTime)
    
    student = db.relationship('User', back_populates='enrollments')
    course = db.relationship('Course', back_populates='enrollments')
    

class SupportStaff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved = db.Column(db.Boolean, default=False)
    approved_at = db.Column(db.DateTime)
    
    staff = db.relationship('User', back_populates='support_courses')
    course = db.relationship('Course', back_populates='support_staff')
    

class CourseTranscript(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('course_content.id'), nullable=False)
    transcript_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship('Course', back_populates='transcripts')
    content = db.relationship('CourseContent', back_populates='transcripts')


class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    messages = db.relationship('ChatMessage', back_populates='session', cascade="all, delete-orphan")
    user = db.relationship('User', back_populates='chat_sessions')


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'))
    sender = db.Column(db.String(6), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    session = db.relationship('ChatSession', back_populates='messages')


class TokenBlacklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(50), unique=True, nullable=False)
    token_type = db.Column(db.String(20), nullable=False)
    expires = db.Column(db.DateTime, nullable=False)
    blacklisted_on = db.Column(db.DateTime, default=datetime.utcnow)

    
def is_token_blacklisted(jti):
    return TokenBlacklist.query.filter_by(jti=jti).first() is not None


@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload):
    return is_token_blacklisted(jwt_payload["jti"])


@jwt.revoked_token_loader
def revoked_token_response(jwt_header, jwt_payload):
    return jsonify({"msg": "Token has been revoked"}), 401


@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    new_access_token = user.generate_access_token()
    return jsonify({"access_token": new_access_token}), 200
    
    
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    # If the request is for a static file (CSS/JS), serve it normally
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # For all other paths, serve the index.html so Vue Router can handle it
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        access_token = user.generate_access_token()
        refresh_token = user.generate_refresh_token()
        return jsonify({ "user": { "name": user.name, "email": user.email, "role": user.role }, "access_token": access_token, "refresh_token": refresh_token, "message": 'Login successful!'}), 200
    return jsonify({"error": "Invalid username or password."}), 401
    

def is_valid_email(email):
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(email_regex, email) is not None


def is_valid_password(password):
    password_regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
    return re.match(password_regex, password) is not None


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('retypePassword')
    role = data.get('role')
    
    
    if not email or len(email) > 100 or not is_valid_email(email):
        return jsonify({"error": "Invalid or missing 'email'. Must be a valid email address and 100 characters or less."}), 400
    if not password or len(password) < 8 or not is_valid_password(password):
        return jsonify({"error": "Invalid or missing 'password'. Must be at least 8 characters long."}), 400
    if not password or len(confirm_password) < 8 or not is_valid_password(confirm_password):
        return jsonify({"error": "Invalid or missing 'password'. Must be at least 8 characters long."}), 400
    if not name or len(name) > 100:
        return jsonify({"error": "Invalid or missing 'name'. Must be 100 characters or less."}), 400
    if role not in ['student', 'support_staff', 'admin', 'manager', 'developer']:
        return jsonify({"error": "Invalid 'role'. Must be one of ['student', 'support_staff']."}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Username already exists."}), 400
    if password != confirm_password:
        return jsonify({"message": "Password and Confirm Password must be same."}), 400

    new_user = User(name=name, email=email, role=role)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    
    user = User.query.filter_by(email=email).first()
    access_token = user.generate_access_token()
    refresh_token = user.generate_refresh_token()    
    return jsonify({"user": { "name": user.name, "email": user.email, "role": user.role }, "access_token": access_token, "refresh_token": refresh_token, "message": "User registered successfully!"}), 201


@app.route('/logout_refresh', methods=['POST'], endpoint='loggig_out_user_refresh_token_invalidation')
@jwt_required(refresh=True)
def logout_refresh():
    jti = get_jwt()["jti"]
    token_type = get_jwt()["type"]
    expires = datetime.fromtimestamp(get_jwt()["exp"])
    if expires > datetime.now():
        revoked_token = TokenBlacklist(jti=jti, token_type=token_type, expires=expires)
        db.session.add(revoked_token)
        db.session.commit()          
    return jsonify({"message": "Refresh token revoked"}), 200

@app.route('/logout', methods=['POST'], endpoint='loggig_out_user_access_token_invalidation')
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    token_type = get_jwt()["type"]
    expires = datetime.fromtimestamp(get_jwt()["exp"])
    if expires > datetime.now():
        revoked_token = TokenBlacklist(jti=jti, token_type=token_type, expires=expires)
        db.session.add(revoked_token)
        db.session.commit()         
    return jsonify({"message": "Successfully logged out"}), 200

@app.route('/profile', methods=['PUT'])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user.role == 'admin':
        return jsonify({"error": "Unautorized Request Denied."}),403
    data = request.json
    if 'name' in data and data['name'].strip():
        user.name = data['name'].strip()
    else:
        return jsonify({"error": "Name is required"}), 400
    db.session.commit()
    return jsonify({"message": "Profile updated successfully", "name": user.name}), 200


@app.route('/approve/support_staffs', methods=['PUT'], endpoint='approve_support_staffs')
@jwt_required()
def approve_staff():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role != 'admin':
        return jsonify({"error": "Unauthorized request denied."}), 403
    data = request.json
    staff_id = data.get('staff_id')
    course_id = data.get('course_id')
    action = data.get('action')
    if not staff_id or not course_id or action not in ["approve", "reject"]:
        return jsonify({"error": "staff_id, course_id, and valid action are required"}), 400
    instructor = SupportStaff.query.filter_by(staff_id=staff_id, course_id=course_id).first()  
    if not instructor:
        return jsonify({"error": "Support Staff not found"}), 404
    if action == "approve":
        instructor.approved = True
        instructor.approved_at = datetime.utcnow()
        message = "Support Staff approved successfully."
    else:
        db.session.delete(instructor)
        message = "Support Staff rejected successfully."
    db.session.commit()
    return jsonify({"message": message}), 200


@app.route('/apply/support_staff', methods=['POST'])
@jwt_required()
def apply_support_staff():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role != 'support_staff':
        return jsonify({"error": "Unauthorized request. Only staff can apply to assist courses."}), 403
    data = request.json
    course_id = data.get('course_id')
    if not course_id:
        return jsonify({"error": "course_id is required"}), 400
    existing_application = SupportStaff.query.filter_by(staff_id=user_id, course_id=course_id).first()
    if existing_application:
        return jsonify({"error": "You have already applied to be support staff for this course."}), 400
    application = SupportStaff(staff_id=user_id, course_id=course_id, applied_at=datetime.utcnow(), approved=False)
    db.session.add(application)
    db.session.commit()
    return jsonify({"message": "Support staff application submitted successfully. Pending approval."}), 201


@app.route('/approve/course_enrollment', methods=['PUT'], endpoint='approve_course_enrollment')
@jwt_required()
def approve_enrollment():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role not in ['support_staff', 'admin']:
        return jsonify({"error": "Unauthorized request denied."}), 403
    data = request.json
    student_id = data.get('student_id')
    course_id = data.get('course_id')
    action = data.get('action')
    if not student_id or not course_id or action not in ["approve", "reject"]:
        return jsonify({"error": "student_id, course_id, and valid action are required"}), 400
    enrollment = StudentEnrollment.query.filter_by(student_id=student_id, course_id=course_id).first()
    if not enrollment:
        return jsonify({"error": "Student enrollment not found"}), 404
    if user.role == 'support_staff':
        is_assigned = SupportStaff.query.filter_by(staff_id=user_id, course_id=course_id, approved=True).first()
        if not is_assigned:
            return jsonify({"error": "You are not authorized to manage this enrollment."}), 403
    if action == "approve":
        enrollment.approved = True
        enrollment.approved_at = datetime.utcnow()
        message = "Student enrollment approved successfully."
    else:
        db.session.delete(enrollment)
        message = "Student enrollment rejected successfully."
    db.session.commit()
    return jsonify({"message": message}), 200



@app.route('/register/course', methods=['POST'])
@jwt_required()
def register_course():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role != 'student':
        return jsonify({"error": "Unauthorized request. Only students can register for courses."}), 403
    data = request.json
    course_id = data.get('course_id')
    if not course_id:
        return jsonify({"error": "course_id is required"}), 400
    existing_enrollment = StudentEnrollment.query.filter_by(student_id=user_id, course_id=course_id).first()
    if existing_enrollment:
        return jsonify({"error": "You are already registered for this course."}), 400
    enrollment = StudentEnrollment(student_id=user_id, course_id=course_id, registered_at=datetime.utcnow(), approved=False)
    db.session.add(enrollment)
    db.session.commit()
    return jsonify({"message": "Course registration submitted successfully. Pending approval."}), 201


@app.route('/delete_course/course/<int:course_id>', methods=['DELETE'])
@jwt_required()
def delete_course(course_id):
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role != 'admin':
        return jsonify({"error": "Unauthorized request. Only admin can delete entire course."}), 403
    try:
        course = db.session.get(Course, course_id)    
        if not course:
            return jsonify({"error": f"No course found with course id {course_id}."}), 404
        contents = CourseContent.query.filter_by(course_id=course_id).all()
        content_ids = [content.id for content in contents]
        delete_embeddings.delay(content_ids, is_course_deletion=True)
        db.session.delete(course)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500    
    return jsonify({"message": f"Course with course id {course_id} deleted successfully."}), 200


@app.route('/add/new_course', methods=['POST'])
@jwt_required()
def add_new_course():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role != 'admin':
        return jsonify({"error": "Unauthorized request. Only admin can add new courses."}), 403
    data = request.json
    name = data.get('name')
    prof = data.get('prof')
    if not name or len(name) > 100:
        return jsonify({"error": "Invalid or missing 'course name'. Must be 100 characters or less."}), 400
    if not prof or len(prof) > 100:
        return jsonify({"error": "Invalid or missing 'prof. name'. Must be 100 characters or less."}), 400    
    new_course = Course(name=name, prof=prof)
    db.session.add(new_course)
    db.session.commit()
    return jsonify({"message": "New course added successfully..."}), 201
    
    
@app.route('/add_or_update/course_contents', methods=['POST'])
@jwt_required()
def add_or_update_course_contents():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role not in ['admin', 'support_staff']:
        return jsonify({"error": "Unauthorized request. Only admin or support staff can add course contents."}), 403
    data = request.json
    required_fields = ['course_id', 'week', 'title', 'description', 'video_link']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields: course_id, week, title, description, video_link"}), 400
    course_id = data['course_id']
    week = data['week']
    title = data['title']
    description = data['description']
    video_link = data['video_link']
    
    if not isinstance(week, int) or week < 1 or week > 52:
        return jsonify({"error": "Invalid week. Must be an integer between 1 and 52."}), 400
    if not isinstance(title, str) or len(title) > 100:
        return jsonify({"error": "Invalid title. Must be a string with max 100 characters."}), 400
    if not isinstance(description, str):
        return jsonify({"error": "Invalid description. Must be a string.."}), 400
    
    url_pattern = re.compile(r'^(https?://)?(www\.)?(youtube\.com|youtu\.be|vimeo\.com|drive\.google\.com)/.+')
    if not isinstance(video_link, str) or not re.match(url_pattern, video_link):
        return jsonify({"error": "Invalid video link. Must be a valid YouTube, Vimeo, or Google Drive link."}), 400

    course = db.session.get(Course, course_id)
    if not course:
        return jsonify({"error": "Course not found. Select another course."}), 404
    existing_content = CourseContent.query.filter_by(course_id=course_id, week=week, title=title).first()
    new_content = None
    if existing_content:
        existing_content.title = title
        existing_content.description = description
        existing_content.video_link = video_link
        message = "Course content updated successfully."
        content_id = existing_content.id
    else:
        new_content = CourseContent(course_id=course_id, week=week, title=title, description=description, video_link=video_link)
        db.session.add(new_content)
        message = "Course content added successfully."
    db.session.commit()
    if new_content:
        content_id = new_content.id
    extract_video_transcripts.delay(content_id)
    message += " Transcript extraction started."
    return jsonify({"message": message}), 200


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {"csv"}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload_course_contents', methods=['POST'])
@jwt_required()
def upload_course_contents():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role not in ['admin', 'support_staff']:
        return jsonify({"error": "Unauthorized request. Only admin or support staff can upload course contents."}), 403
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded."}), 400
    file = request.files['file']
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Please upload a CSV file."}), 400

    try:
        stream = io.StringIO(file.stream.read().decode("utf-8"))
        csv_reader = csv.DictReader(stream)
        required_columns = {"course_id", "week", "title", "description", "video_link"}
        if not required_columns.issubset(csv_reader.fieldnames):
            return jsonify({"error": "CSV file must contain columns: course_id, week, title, description, video_link"}), 400
        new_contents = []
        for row in csv_reader:
            try:
                course_id = int(row["course_id"])
                week = int(row["week"])
                title = row["title"].strip()
                description = row["description"].strip()
                video_link = row["video_link"].strip()
                  
                course = db.session.get(Course, course_id)
                if not course:
                    return jsonify({"error": f"Course ID {course_id} not found."}), 404
                if week < 1 or week > 52:
                    return jsonify({"error": f"Invalid week {week}. Must be between 1 and 52."}), 400
                if len(title) > 100:
                    return jsonify({"error": f"Title too long for week {week}. Max 100 characters."}), 400

                url_pattern = re.compile(r'^(https?://)?(www\.)?(youtube\.com|youtu\.be|vimeo\.com|drive\.google\.com)/.+')
                if not re.match(url_pattern, video_link):
                    return jsonify({"error": f"Invalid video link for week {week}. Must be YouTube, Vimeo, or Google Drive link."}), 400

                existing_content = CourseContent.query.filter_by(course_id=course_id, week=week, title=title).first()
                if existing_content:
                    existing_content.title = title
                    existing_content.description = description
                    existing_content.video_link = video_link
                    db.session.commit()
                    extract_video_transcripts.delay(existing_content.id)
                else:
                    new_content = CourseContent(course_id=course_id, week=week, title=title, description=description, video_link=video_link)
                    db.session.add(new_content)
                    db.session.flush()  # Flush to get the ID before commit
                    new_contents.append(new_content)  # Store new contents
            except ValueError:
                return jsonify({"error": "Invalid data format in CSV file."}), 400
        if new_contents:
            db.session.commit()
            for content in new_contents:
                extract_video_transcripts.delay(content.id)
        return jsonify({"message": "Course contents uploaded successfully.  Transcript extraction started."}), 200
    except Exception as e:
        return jsonify({"error": f"Error processing CSV file: {str(e)}"}), 500
    
    
@app.route('/delete_course_content/<int:content_id>', methods=['DELETE'])
@jwt_required()
def delete_course_content(content_id):
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role not in ['admin', 'support_staff']:
        return jsonify({"error": "Unauthorized request. Only admin or support staff can delete course content."}), 403
    try:
        content = db.session.get(CourseContent, content_id)    
        if not content:
            return jsonify({"error": f"No content found with content id {content_id}."}), 404
        db.session.delete(content)
        db.session.commit()
        delete_embeddings.delay([content_id])
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500    
    return jsonify({"message": f"Course content with content id {content_id} deleted successfully."}), 200


@app.route('/course_contents/<int:course_id>', methods=['GET'])
@jwt_required()
def course_contents(course_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found."}), 404
    if user.role == 'student':
        course_enrollment = StudentEnrollment.query.filter_by(student_id=user.id, course_id=course_id).first()
        if not course_enrollment or not course_enrollment.approved:
            return jsonify({"message": "You are not enrolled in this course."}), 403
    contents = CourseContent.query.filter_by(course_id=course_id).all()
    course_contents = []
    for content in contents:
        course_contents.append({
            "id": content.id,
            "week": content.week,
            "title": content.title,
            "description": content.description,
            "video_link": content.video_link
        })
    assignments = Assignment.query.filter_by(course_id=course_id).all()
    assignment_data = []
    assignment_data = [{
        "id": assignment.course_id,
        "assignment_id": assignment.id,
        "week": assignment.week,
        "title": assignment.title,
        "due_date": assignment.due_date
    } for assignment in assignments]
    return jsonify({"course_contents": course_contents, "assignments": assignment_data}), 200
    
    
@app.route('/add_assignment/questions', methods=['POST'])    
@jwt_required()
def add_assignment_with_questions():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role not in ['admin', 'support_staff']:
        return jsonify({"error": "Unauthorized request. Only admin or support staff can upload assignments."}), 403
    data = request.form
    title = data.get('title')
    week = data.get('week')
    due_date = data.get('due_date')
    course_id = data.get('course_id')
    file = request.files['file']
    if not (title and week and due_date and course_id and file):
        return jsonify({'error': 'Missing required fields (title, week, due_date, course_id, csv_file)'}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Please upload a CSV file."}), 400
    try:
        due_date = datetime.strptime(due_date, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD HH:MM:SS'}), 400
    new_assignment = Assignment(course_id=course_id, title=title, week=week, due_date=due_date)
    db.session.add(new_assignment)
    db.session.commit()
        
    stream = io.StringIO(file.stream.read().decode("utf-8"))
    csv_reader = csv.DictReader(stream)
    question_list = []    
    for row in csv_reader:
        if len(row) < 3:
            return jsonify({'error': 'Invalid CSV format. Must have at least question_text, question_type, choices, correct_answer'}), 400
        question_text = row.get('question_text')
        question_type = row.get('question_type')
        choices = row.get('choices', None)
        correct_answer = row.get('correct_answer', None)
        # Validate question data
        if not question_text or not question_type or not correct_answer:
            return jsonify({'error': 'Invalid CSV format. Missing required question fields.'}), 400
        # Convert choices to JSON array for MCQs
        if question_type == 'mcq':
            if choices:
                try:
                    choices = json.loads(choices) if choices.startswith("[") and choices.endswith("]")  else [c.strip() for c in choices.split(',')]
                except json.JSONDecodeError:
                    return jsonify({'error': 'Invalid JSON format in choices'}), 400
            else:
                return jsonify({'error': 'MCQ questions must have choices'}), 400
        else:
            choices = None  # Only MCQs have choices
        new_question = AssignmentQuestion(assignment_id=new_assignment.id, question_text=question_text, question_type=question_type, choices=choices, correct_answer=correct_answer)
        question_list.append(new_question)
    db.session.bulk_save_objects(question_list)
    db.session.commit()
    schedule_grading_task(new_assignment.id, due_date)
    return jsonify({'message': 'Assignment and questions added successfully', 'assignment_id': new_assignment.id}), 201


@app.route('/update_assignment/<int:assignment_id>', methods=['PUT'])
@jwt_required()
def update_assignment(assignment_id):
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role not in ['admin', 'support_staff']:
        return jsonify({"error": "Unauthorized request."}), 403
    assignment = Assignment.query.get_or_404(assignment_id)
    old_due_date = assignment.due_date
    data = request.form
    assignment.title = data.get('title', assignment.title)
    assignment.week = data.get('week', assignment.week)
    assignment.due_date = datetime.strptime(data.get('due_date', assignment.due_date.strftime('%Y-%m-%d %H:%M:%S')), '%Y-%m-%d %H:%M:%S')
    db.session.commit()    
    if old_due_date != assignment.due_date:
        schedule_grading_task(assignment.id, assignment.due_date)
    return jsonify({'message': 'Assignment updated successfully'}), 200


@app.route('/delete_assignment/<int:assignment_id>', methods=['DELETE'])
@jwt_required()
def delete_assignment(assignment_id):
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role not in ['admin', 'support_staff']:
        return jsonify({"error": "Unauthorized request."}), 403
    assignment = Assignment.query.get_or_404(assignment_id)
    db.session.delete(assignment)
    db.session.commit()
    return jsonify({'message': 'Assignment deleted successfully'}), 200

@app.route('/add_new_assignment_question/<int:assignment_id>', methods=['POST'])
@jwt_required()
def add_question_to_assignment(assignment_id):
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role not in ['admin', 'support_staff']:
        return jsonify({"error": "Unauthorized request."}), 403
    assignment = Assignment.query.get_or_404(assignment_id)
    data = request.json
    question_text = data.get('question_text')
    question_type = data.get('question_type')
    choices = data.get('choices', None)
    correct_answer = data.get('correct_answer')
    if not question_text or not question_type or not correct_answer:
        return jsonify({'error': 'Missing required question fields'}), 400
    if question_type == 'mcq' and choices:
        try:
            choices = json.loads(choices) if choices.startswith("[") and choices.endswith("]")  else [c.strip() for c in choices.split(',')]
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON format in choices'}), 400
    else:
        choices = None
    new_question = AssignmentQuestion(assignment_id=assignment.id, question_text=question_text, question_type=question_type, choices=choices, correct_answer=correct_answer)
    db.session.add(new_question)
    db.session.commit()
    return jsonify({'message': 'New question added successfully'}), 201


@app.route('/update_assignment_question/<int:question_id>', methods=['PUT'])
@jwt_required()
def update_question(question_id):
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role not in ['admin', 'support_staff']:
        return jsonify({"error": "Unauthorized request."}), 403
    question = AssignmentQuestion.query.get_or_404(question_id)
    data = request.json
    question.question_text = data.get('question_text', question.question_text)
    question.question_type = data.get('question_type', question.question_type)
    question.correct_answer = data.get('correct_answer', question.correct_answer)
    if question.question_type == 'mcq':
        choices = data.get('choices')
        if choices:
            try:
                question.choices = json.loads(choices) if choices.startswith("[") and choices.endswith("]")  else [c.strip() for c in choices.split(',')]
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid JSON format in choices'}), 400
    db.session.commit()
    return jsonify({'message': 'Question updated successfully'}), 200


@app.route('/delete_assignment_question/<int:question_id>', methods=['DELETE'])
@jwt_required()
def delete_question(question_id):
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role not in ['admin', 'support_staff']:
        return jsonify({"error": "Unauthorized request."}), 403
    question = AssignmentQuestion.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    return jsonify({'message': 'Question deleted successfully'}), 200


@app.route('/submit_or_update_answers', methods=['POST'])
@jwt_required()
def submit_or_update_answers():
    user_id = get_jwt_identity()
    student = User.query.get_or_404(user_id)
    if student.role != 'student':
        return jsonify({"error": "Unauthorized request. Only students can submit or update answers."}), 403
    data = request.json
    assignment_id = data.get('assignment_id')
    answers = data.get('answers')  
    if not (assignment_id and answers):
        return jsonify({'error': 'Missing required fields (assignment_id, answers)'}), 400
    assignment = Assignment.query.get(assignment_id)  
    if not assignment:
        return jsonify({'error': 'Assignment has not been found.'}), 404     
    for ans in answers:
        question_id = ans.get('question_id')
        selected_answer = ans.get('selected_answer', None)
        question = AssignmentQuestion.query.filter_by(id=question_id, assignment_id=assignment_id).first()
        if not question:
            return jsonify({'error': 'Question is not valid for this assignment.'}), 404  
        existing_answer = StudentAnswer.query.filter_by(student_id=user_id, assignment_id=assignment_id, question_id=question_id).first()
        if existing_answer:
            existing_answer.selected_answer = selected_answer
        else:
            new_answer = StudentAnswer(student_id=user_id, assignment_id=assignment_id, question_id=question_id, selected_answer=selected_answer)
            db.session.add(new_answer)
    db.session.commit()
    return jsonify({'message': 'Answers processed and submitted successfully'}), 200 


@app.route('/assignment/questions/<int:assignment_id>', methods=['GET'])
@jwt_required()
def get_assignment_questions(assignment_id):
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    
    assignment = Assignment.query.get(assignment_id)    
    if not assignment:
        return jsonify({'error': 'Assignment not found.'}), 404
    questions = AssignmentQuestion.query.filter_by(assignment_id=assignment_id).all()
    submitted_answers = {}
    if user.role == 'student':
        submitted_answers = {answer.question_id: {"selected_answer": answer.selected_answer, "is_correct": answer.is_correct}  for answer in StudentAnswer.query.filter_by(student_id=user_id, assignment_id=assignment_id).all()}

    questions_data = []
    for question in questions:
        question_info = {"question_id": question.id, "question_text": question.question_text, "question_type": question.question_type, "submitted_answer": submitted_answers.get(question.id, {}).get("selected_answer", None), "is_correct": submitted_answers.get(question.id, {}).get("is_correct", None)}
        if question.question_type == "mcq":
            question_info["choices"] = question.choices
        questions_data.append(question_info)

    return jsonify({"questions": questions_data}), 200


@app.route('/dashboard/admin', methods=['GET'], endpoint="admin_dashboard")
@jwt_required()
def admin_dashboard():
    print(get_jwt_identity())
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role != 'admin':
        return jsonify({"error": "Unauthorized request. Only admin can access this path."}), 403    
    courses = Course.query.all()
    courses = [{"id": course.id, "name": course.name} for course in courses]
    pendingApprovals = db.session.query(User, Course).join(SupportStaff, User.id == SupportStaff.staff_id).join(Course, Course.id == SupportStaff.course_id).filter(SupportStaff.approved == False).all()
    pendingApprovals = [{"staff_id": staff.id, "staff_name": staff.name, "staff_email": staff.email , "course_id": course.id, "course_name": course.name} for staff, course in pendingApprovals]
    pendingEnrollments = db.session.query(User, Course).join(StudentEnrollment, User.id == StudentEnrollment.student_id).join(Course, Course.id == StudentEnrollment.course_id).filter(StudentEnrollment.approved == False).all()
    pendingEnrollments = [{"student_id": student.id, "student_name": student.name, "student_email": student.email, "course_id": course.id, "course_name": course.name} for student, course in pendingEnrollments]
    return jsonify({"courses": courses, "pendingApprovals": pendingApprovals, "pendingEnrollments": pendingEnrollments}), 200


@app.route('/dashboard/support_staff', methods=['GET'], endpoint="support_staff_dashboard")
@jwt_required()
def support_staff_dashboard():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role != 'support_staff':
        return jsonify({"error": "Unauthorized request. Only Support Staff can access this path."}), 403    
    courses = Course.query.all()
    courses = [{"id": course.id, "name": course.name} for course in courses]
    support_courses = db.session.query(Course).join(SupportStaff).filter(SupportStaff.staff_id == user.id, SupportStaff.approved == True).all()
    support_courses_ids = {course.id for course in support_courses} 
    support_courses = [{"id": course.id, "name": course.name} for course in support_courses]
    pendingEnrollments = db.session.query(User, Course).join(StudentEnrollment, User.id == StudentEnrollment.student_id).join(Course, Course.id == StudentEnrollment.course_id).filter(StudentEnrollment.approved == False, Course.id.in_(support_courses_ids)).all()
    pendingEnrollments = [{"student_id": student.id, "student_name": student.name, "student_email": student.email, "course_id": course.id, "course_name": course.name} for student, course in pendingEnrollments]
    return jsonify({"courses": courses, "support_courses": support_courses, "pendingEnrollments": pendingEnrollments}), 200


@app.route('/dashboard/student', methods=['GET'], endpoint="student_dashboard")
@jwt_required()
def student_dashboard(): 
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role != 'student':
        return jsonify({"error": "Unauthorized request. Only Student can access this path."}), 403    
    courses = Course.query.all()
    courses = [{"id": course.id, "name": course.name} for course in courses]
    enrolled_courses = db.session.query(Course).join(StudentEnrollment).filter(StudentEnrollment.student_id == user.id, StudentEnrollment.approved == True).all()
    enrolled_courses = [{"id": course.id, "name": course.name} for course in enrolled_courses]
    return jsonify({"courses": courses, "enrolled_courses": enrolled_courses}), 200


def start_session(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != 'student':
        return jsonify({"error": "Unauthorized request. Only Student can access this path."}), 403    
    session = ChatSession(user_id=user_id)
    db.session.add(session)
    db.session.commit()
    return session.id


@app.route("/delete_session/<int:session_id>", methods=["DELETE"])
@jwt_required()
def delete_session(session_id):
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    session = ChatSession.query.get_or_404(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    if user.id != session.user_id:
        return jsonify({"error": "Unauthorized request denied..."}), 403
    db.session.delete(session)
    db.session.commit()
    return jsonify({"message": "Session deleted successfully!"}), 200


def summarize_course_content(course_id, week=None):
    course = Course.query.get(course_id)
    if not course:
        return "Course not found."
    if week:
        contents = CourseContent.query.filter_by(course_id=course_id, week=week).all()
    else:
        contents = CourseContent.query.filter_by(course_id=course_id).all()
    if not contents:
        return "No content found."
    transcripts = []
    for content in contents:
        transcript = CourseTranscript.query.filter_by(content_id=content.id).first()
        if transcript:
            transcripts.append(transcript.transcript_text)
    if not transcripts:
        return "No transcripts available."
    summary_prompt = f"""Summarize the following course content: {' '.join(transcripts)}"""
    response = model.generate_content(summary_prompt)
    return str(response.text)


def classify_query(query):
    """Classifies a query as course-related or general."""
    # Keyword matching
    course_keywords = [course.name.lower() for course in Course.query.all()]
    if any(keyword in query.lower() for keyword in course_keywords):
        return True
    # Embedding similarity with individual content indexes
    query_embedding = embed_model.encode([query])
    for content in CourseContent.query.all():  # Iterate through all contents
        content_id = content.id
        faiss_index_path = f"{VECTOR_DB_PATH}/course_{content_id}.faiss"
        id_map_path = f"{VECTOR_DB_PATH}/course_{content_id}_ids.json"
        metadata_path = f"{VECTOR_DB_PATH}/course_{content_id}_metadata.json"
        if os.path.exists(faiss_index_path) and os.path.exists(id_map_path) and os.path.exists(metadata_path):
            index = faiss.read_index(faiss_index_path)
            with open(id_map_path, "r") as f:
                id_map = json.load(f)
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            _, indices = index.search(query_embedding, 1)
            if indices[0][0] != -1:
                index_to_reconstruct = int(indices[0][0])
                retrieved_chunk_embedding = index.reconstruct(index_to_reconstruct)
                similarity = cosine_similarity(query_embedding, [retrieved_chunk_embedding])[0][0]
                if similarity > 0.6:
                    return True
    return False


@app.route('/chat', methods=['POST'])
@jwt_required()
def chat():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role != 'student':
        return jsonify({"error": "Unauthorized request. Only students can access this path."}), 403
    data = request.json
    session_id = data.get("session_id")
    session_data = []
    if not session_id:
        session_id = start_session(user.id) 
    session = ChatSession.query.get_or_404(session_id)
    session_data = [ {"id": session.id, "user_id": session.user_id, "created_at": session.created_at.strftime("%Y-%m-%d %H:%M:%S")} ]   
    query = data.get("message", "").strip()
    if not query:
        return jsonify({"error": "Message cannot be empty"}), 400

    # Summarization requests
    summary_match = re.search(r'Summarize the course "([^"]+)"(?: for week (\d+))?', query, re.IGNORECASE)
    if summary_match:
        course_name = summary_match.group(1)
        week = summary_match.group(2)
        course = Course.query.filter_by(name=course_name).first()
        if not course:
            return jsonify({"error": f"Course '{course_name}' not found."}), 404
        if week:
            contents = CourseContent.query.filter_by(course_id=course.id, week=week).all()
        else:
            contents = CourseContent.query.filter_by(course_id=course.id).all()
        if not contents:
            return jsonify({"error": f"Course Contents not found for the course '{course_name}'."}), 404
        transcripts = []
        for content in contents:
            transcript = CourseTranscript.query.filter_by(content_id=content.id).first()
            if transcript:
                transcripts.append(transcript.transcript_text)
        if not transcripts:
            return jsonify({"error": f"Course Transcripts not found for the course '{course_name}'."}), 404
        summary_prompt = f"""Summarize the following course content: {' '.join(transcripts)}"""
        response = model.generate_content(summary_prompt)
        response = str(response.text)
        user_chat = ChatMessage(session_id=session_id, sender="user", message=query)
        ai_chat = ChatMessage(session_id=session_id, sender="bot", message=response)
        db.session.add_all([user_chat, ai_chat])
        db.session.commit()
        return jsonify({"response": response, "session": session_data}), 201

    # Question generation requests
    question_match = re.search(r'Generate(?: (\d+))? questions from the course "([^"]+)"(?: from week (\d+))?', query, re.IGNORECASE)
    if question_match:
        num_questions = question_match.group(1)
        course_name = question_match.group(2)
        week = question_match.group(3)
        course = Course.query.filter_by(name=course_name).first()
        if not course:
            return jsonify({"error": f"Course '{course_name}' not found."}), 404
        if week:
            contents = CourseContent.query.filter_by(course_id=course.id, week=int(week)).all()
        else:
            contents = CourseContent.query.filter_by(course_id=course.id).all()

        transcripts = []
        for content in contents:
            transcript = CourseTranscript.query.filter_by(content_id=content.id).first()
            if transcript:
                transcripts.append(transcript.transcript_text)
        if not transcripts:
            return jsonify({"error": "No transcripts available."}), 404

        question_prompt = f"""Generate { num_questions if num_questions else "questions" } questions based on the course content: {' '.join(transcripts)}"""
        response = model.generate_content(question_prompt)
        response = str(response.text)
        user_chat = ChatMessage(session_id=session_id, sender="user", message=query)
        ai_chat = ChatMessage(session_id=session_id, sender="bot", message=response)
        db.session.add_all([user_chat, ai_chat])
        db.session.commit()
        return jsonify({"response": response, "session": session_data}), 201
    
    context = ""
    course_match = re.search(r'course "([^"]+)"', query, re.IGNORECASE)
    week_match = re.search(r'week (\d+)', query, re.IGNORECASE)
    course_name = course_match.group(1) if course_match else None
    week = int(week_match.group(1)) if week_match else None
    if course_name and week:
        print(course_name, week)
        course = Course.query.filter_by(name=course_name).first()
        contents = [content.id for content in CourseContent.query.filter_by(course_id=course.id, week=week).all()]
        transcripts = CourseTranscript.query.filter(CourseTranscript.content_id.in_(contents)).all()
        context = "\n".join([transcript.transcript_text for transcript in transcripts])
    
    references = ""
    is_course_related = classify_query(query)
    if is_course_related and not context:        
        query_embedding = embed_model.encode([query])
        retrieved_chunks = []
        max_chunks_per_content = 100
        total_retrieved = 0
        total_max_retrieved = 10
        for content in CourseContent.query.all():
            if total_retrieved >= total_max_retrieved:
                break
            content_id = content.id
            faiss_index_path = f"{VECTOR_DB_PATH}/course_{content_id}.faiss"
            id_map_path = f"{VECTOR_DB_PATH}/course_{content_id}_ids.json"
            metadata_path = f"{VECTOR_DB_PATH}/course_{content_id}_metadata.json"

            if os.path.exists(faiss_index_path) and os.path.exists(id_map_path) and os.path.exists(metadata_path):
                index = faiss.read_index(faiss_index_path)
                with open(id_map_path, "r") as f:
                    id_map = json.load(f)
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                _, indices = index.search(query_embedding, max_chunks_per_content) # retrieve only top 1 chunk per content.
                if indices[0][0] != -1:
                    retrieved_chunks.append(metadata[id_map[indices[0][0]]])
                    total_retrieved +=1
                if total_retrieved >= total_max_retrieved:
                        break
        # Aggregate the retrieved chunks
        if retrieved_chunks:
            context = "\n".join([chunk["chunk"] for chunk in retrieved_chunks])
            references = "\n".join([f"{chunk['course_name']}, Week {chunk['week']}" for chunk in retrieved_chunks])
    
    chat_history = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp.desc()).limit(10).all()
    chat_history.reverse()
    history_text = "\n".join([f"{msg.sender}: {msg.message}" for msg in chat_history])

    if context:
        prompt = f"""
                        You are an AI assistant. Provide short, indirect responses. Use the following context to guide your response.

                        **Past Chat History:**
                        {history_text}

                        **Relevant Course Content:**
                        {context}

                        **User Query:**
                        {query}
                        
                        **References:** 
                        {references}
                        
                        **Response:** 
                        (Provide a short, indirect answer and include references)
                    """
    else:
        prompt = f"""
                        You are an AI assistant for general conversation.

                        **Past Chat History:**
                        {history_text}

                        **User Query:**
                        {query}

                        Provide a helpful and informative response.
                    """

    try:
        response = model.generate_content(prompt)
    except Exception as e:
        print(e)
        return jsonify({"error": f"AI response failed: {str(e)}"}), 500
    response = str(response.text)
    user_chat = ChatMessage(session_id=session_id, sender="user", message=query)
    ai_chat = ChatMessage(session_id=session_id, sender="bot", message=response)
    db.session.add_all([user_chat, ai_chat])
    db.session.commit()
    return jsonify({"response": response, "session": session_data}), 201


@app.route("/all_chat_sessions", methods=["GET"])
@jwt_required()
def all_chat_session():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    sessions = ChatSession.query.filter_by(user_id=user.id).order_by(ChatSession.created_at.desc()).all()
    session_data = [ {"id": session.id, "user_id": session.user_id, "created_at": session.created_at.strftime("%Y-%m-%d %H:%M:%S")} for session in sessions ]
    return jsonify({"sessions": session_data, "message": "All sessions retrieved successfully!"}), 200


@app.route('/chat/history/<int:session_id>', methods=['GET'])
@jwt_required()
def get_chat_history(session_id):
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    if user.role != 'student':
        return jsonify({"error": "Unauthorized request. Only Student can access this path."}), 403
    session = ChatSession.query.filter_by(id=session_id, user_id=user_id).first()
    if not session:
        return jsonify({"error": "Session not found."}), 404
    chat_history = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp.asc()).all()
    chat_history = [ {"sender": msg.sender, "message": msg.message} for msg in chat_history ]
    return jsonify({"session_id": session_id, "chat_history": chat_history}), 200


if __name__ == '__main__':
    app.run(debug=True)