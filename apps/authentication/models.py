from flask_login import UserMixin

from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin

from apps import db, login_manager

from apps.authentication.util import hash_pass

class Users(db.Model, UserMixin):

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

    def __repr__(self):
        return str(self.username)

    @classmethod
    def find_by_email(cls, email: str) -> "Users":
        return cls.query.filter_by(email=email).first()

    @classmethod
    def find_by_username(cls, username: str) -> "Users":
        return cls.query.filter_by(username=username).first()
    
    @classmethod
    def find_by_id(cls, _id: int) -> "Users":
        return cls.query.filter_by(id=_id).first()
   
    def save(self) -> None:
        try:
            db.session.add(self)
            db.session.commit()
          
        except SQLAlchemyError as e:
            db.session.rollback()
            db.session.close()
            error = str(e.__dict__['orig'])
            raise IntegrityError(error, 422)
    
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

@login_manager.user_loader
def user_loader(id):
    return Users.query.filter_by(id=id).first()

@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    user = Users.query.filter_by(username=username).first()
    return user if user else None

# students_ngrtb = db.Table(
#     'students_ngrtb',
#     db.Column('student_id', db.Integer, db.ForeignKey('students.student_id')),
#     db.Column('ngrtb_id', db.Integer, db.ForeignKey('ngrtb_id'))
# )

# Define the Students data model (table in database)
class Students(db.Model, UserMixin):

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
    # ngrtb = db.relationship('NGRTB', secondary=students_ngrtb, backref='students')

    def __repr__(self):
        return str(self.student_id)

# Define the data model (table in database) for NGRT-B
class NGRTB(db.Model, UserMixin):

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

    def __repr__(self):
        return str(self.student_id)