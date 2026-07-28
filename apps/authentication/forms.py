# base class for web forms
from flask_wtf import FlaskForm
# input fields for text/email and passwords
from wtforms import StringField, PasswordField
# validation rules for required input and valid emails
from wtforms.validators import Email, DataRequired

# Login form for user authentication
class LoginForm(FlaskForm):
    # Form fields for username
    username = StringField('Username',
                         id='username_login',
                         validators=[DataRequired()])
    # Form field for password
    password = PasswordField('Password',
                             id='pwd_login',
                             validators=[DataRequired()])

# Create account form for user registration
class CreateAccountForm(FlaskForm):
    # Form fields for username
    username = StringField('Username',
                         id='username_create',
                         validators=[DataRequired()])
    # Form field for email with validation
    email = StringField('Email',
                      id='email_create',
                      validators=[DataRequired(), Email()])
    # Form field for password
    password = PasswordField('Password',
                             id='pwd_create',
                             validators=[DataRequired()])
    # Form field for designation
    designation = StringField('Designation',
                                id='designation_create',
                                validators=[DataRequired()])
    # Form field for first name
    first_name = StringField('First Name',
                                id='firstname_create',
                                validators=[DataRequired()])
    # Form field for last name
    last_name = StringField('Last Name',
                            id='lastname_create',
                            validators=[DataRequired()])
    # Form field for address
    address = StringField('Address',
                            id='address_create',
                            validators=[DataRequired()])
