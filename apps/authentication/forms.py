from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import Email, DataRequired

# login and registration

class LoginForm(FlaskForm):
    username = StringField('Username',
                         id='username_login',
                         validators=[DataRequired()])
    password = PasswordField('Password',
                             id='pwd_login',
                             validators=[DataRequired()])


class CreateAccountForm(FlaskForm):
    username = StringField('Username',
                         id='username_create',
                         validators=[DataRequired()])
    email = StringField('Email',
                      id='email_create',
                      validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                             id='pwd_create',
                             validators=[DataRequired()])
    designation = StringField('Designation',
                                id='designation_create',
                                validators=[DataRequired()])
    first_name = StringField('First Name',
                                id='firstname_create',
                                validators=[DataRequired()])
    last_name = StringField('Last Name',
                            id='lastname_create',
                            validators=[DataRequired()])
    address = StringField('Address',
                            id='address_create',
                            validators=[DataRequired()])
