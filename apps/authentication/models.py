from flask_login import UserMixin  # Provides default implementations for Flask-Login user properties

from sqlalchemy.exc import SQLAlchemyError, IntegrityError  # Database exception handlers for query/constraint errors
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin  # SQLAlchemy model mixin for OAuth tokens

from apps import db, login_manager  # Imports core database instance and login manager extension
from apps.authentication.util import hash_pass  # Helper function for hashing user passwords

# Define the Users data model (table in database)
class Users(db.Model, UserMixin):
    # Define the Users model with fields for authentication and user profile information
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64), unique=True)
    first_name    = db.Column(db.String(100), nullable=True)
    last_name     = db.Column(db.String(100), nullable=True)
    address       = db.Column(db.String(100), nullable=True)
    designation   = db.Column(db.String(200), nullable=True)
    email         = db.Column(db.String(64), unique=True)
    password      = db.Column(db.LargeBinary)
    profile_image = db.Column(db.String(255), default='profile.png')
    is_admin      = db.Column(db.Boolean, nullable=False, default=False)

    # Initialize the Users model with keyword arguments for dynamic attribute assignment
    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]

            if property == 'password':
                value = hash_pass(value)  # we need bytes here (not plain str)

            setattr(self, property, value)

    # Representation method for debugging and logging purposes
    def __repr__(self):
        return str(self.username)

    # Class method to find a user by email in the database
    @classmethod
    def find_by_email(cls, email: str) -> "Users":
        return cls.query.filter_by(email=email).first()
    # Class method to find a user by username in the database
    @classmethod
    def find_by_username(cls, username: str) -> "Users":
        return cls.query.filter_by(username=username).first()
    # Class method to find a user by ID in the database
    @classmethod
    def find_by_id(cls, _id: int) -> "Users":
        return cls.query.filter_by(id=_id).first()
    # Method to save the user instance to the database with error handling for integrity issues
    def save(self) -> None:
        try:
            db.session.add(self)
            db.session.commit()
          
        except SQLAlchemyError as e:
            db.session.rollback()
            db.session.close()
            error = str(e.__dict__['orig'])
            raise IntegrityError(error, 422)
    # Method to delete the user instance from the database with error handling for integrity issues
    def delete_from_db(self) -> None:
        try:
            db.session.delete(self)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            db.session.close()
            error = str(e.__dict__['orig'])
            raise IntegrityError(error, 422)
        return
    
# Define the OAuth model for storing OAuth tokens in the database
@login_manager.user_loader
def user_loader(id):
    return Users.query.filter_by(id=id).first()

# Define the request loader for Flask-Login to load a user from the request form data
@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    user = Users.query.filter_by(username=username).first()
    return user if user else None

# Define the Students data model (table in database)
class Students(db.Model, UserMixin):
    # Define the Students model with fields for student information and academic details
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, unique=True, nullable=False)
    forename = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(64), nullable=False)
    date_of_birth = db.Column(db.String(64), nullable=False)
    yrgrp = db.Column(db.String(64), nullable=False)
    sped = db.Column(db.String(64), nullable=True)
    nationality = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(64), nullable=True)

    # Method to convert the Students object to a dictionary for easier data handling
    def __repr__(self):
        return str(self.student_id)

# Define the data model (table in database) for NGRT-A
class NGRTA(db.Model, UserMixin):
    # Define the NGRTA model with fields for student assessment data and academic performance
    __tablename__ = 'ngrta'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False) # Foreign Key to Students table
    ngrt_level = db.Column(db.String(64), nullable=False)
    sas = db.Column(db.Integer, nullable=True)
    stanine = db.Column(db.Integer, nullable=True)
    reading_age = db.Column(db.String(64), nullable=True)
    profile_desc = db.Column(db.String(150), nullable=True)

    # Method to convert the NGRTA object to a dictionary for easier data handling
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'ngrt_level': self.ngrt_level,
            'sas': self.sas,
            'stanine': self.stanine,
            'reading_age': self.reading_age,
            'profile_desc': self.profile_desc
        }
    # Representation method for debugging and logging purposes
    def __repr__(self):
        return str(self.student_id)
    
# Define the data model (table in database) for NGRT-B
class NGRTB(db.Model, UserMixin):
    # Define the NGRTB model with fields for student assessment data and academic performance
    __tablename__ = 'ngrtb'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False) # Foreign Key to Students table
    ngrt_level = db.Column(db.String(64), nullable=False)
    sas = db.Column(db.Integer, nullable=True)
    stanine = db.Column(db.Integer, nullable=True)
    reading_age = db.Column(db.String(64), nullable=True)
    prev_test_name = db.Column(db.String(64), nullable=True)
    prev_sas = db.Column(db.Integer, nullable=True)
    prev_stanine = db.Column(db.Integer, nullable=True)
    progress_category = db.Column(db.String(64), nullable=True)
    reader_profile = db.Column(db.String(100), nullable=True)
    profile_desc = db.Column(db.String(150), nullable=True)

    # Method to convert NGRTB object to dictionary for easier data handling in views/templates
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'ngrt_level': self.ngrt_level,
            'sas': self.sas,
            'stanine': self.stanine,
            'reading_age': self.reading_age,
            'prev_test_name': self.prev_test_name,
            'prev_sas': self.prev_sas,
            'prev_stanine': self.prev_stanine,
            'progress_category': self.progress_category,
            'reader_profile': self.reader_profile,
            'profile_desc': self.profile_desc
        }
    # Representation method for debugging and logging purposes
    def __repr__(self):
        return str(self.student_id)
    
# Define the data model (table in database) for NGRT-C
class NGRTC(db.Model, UserMixin):
    # Define the NGRTC model with fields for student assessment data and academic performance
    __tablename__ = 'ngrtc'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False) # Foreign Key to Students table
    ngrt_level = db.Column(db.String(64), nullable=False)
    sas = db.Column(db.Integer, nullable=True)
    stanine = db.Column(db.Integer, nullable=True)
    reading_age = db.Column(db.String(64), nullable=True)
    prev_test_name = db.Column(db.String(64), nullable=True)
    prev_sas = db.Column(db.Integer, nullable=True)
    prev_stanine = db.Column(db.Integer, nullable=True)
    progress_category = db.Column(db.String(64), nullable=True)
    reader_profile = db.Column(db.String(100), nullable=True)
    profile_desc = db.Column(db.String(150), nullable=True)

    # Serialization of NGRT-C data to dictionary format for API responses or other uses
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'ngrt_level': self.ngrt_level,
            'sas': self.sas,
            'stanine': self.stanine,
            'reading_age': self.reading_age,
            'prev_test_name': self.prev_test_name,
            'prev_sas': self.prev_sas,
            'prev_stanine': self.prev_stanine,
            'progress_category': self.progress_category,
            'reader_profile': self.reader_profile,
            'profile_desc': self.profile_desc
        }
    # Representation method for debugging and logging purposes
    def __repr__(self):
        return str(self.student_id)
    
# Define the Internal Exam data model (table in database)
class InternalExam(db.Model, UserMixin):
    # Define the InternalExam model with fields for student internal exam scores and grades
    __tablename__ = 'internalexam'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, unique=True, nullable=False)

    # English
    eng_prevPct = db.Column(db.Integer, nullable=True)
    eng_prevGr = db.Column(db.String(3), nullable=True)
    eng_currPct = db.Column(db.Integer, nullable=True)
    eng_currGr = db.Column(db.String(3), nullable=True)
    eng_progcat = db.Column(db.String(20), nullable=True)

    # Maths
    maths_prevPct = db.Column(db.Integer, nullable=True)
    maths_prevGr = db.Column(db.String(3), nullable=True)
    maths_currPct = db.Column(db.Integer, nullable=True)
    maths_currGr = db.Column(db.String(3), nullable=True)
    maths_progcat = db.Column(db.String(20), nullable=True)

    # Science
    sci_prevPct = db.Column(db.Integer, nullable=True)
    sci_prevGr = db.Column(db.String(3), nullable=True)
    sci_currPct = db.Column(db.Integer, nullable=True)
    sci_currGr = db.Column(db.String(3), nullable=True)
    sci_progcat = db.Column(db.String(20), nullable=True)
    
    def __repr__(self):
        return str(self.student_id)