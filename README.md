<h1>ExamInsight<h1></h1>
Attainment and Progress Tracking in Year 2 Internal Assessments and External Benchmark Tests at Pristine Private School.

###########################################

Default admin username: awingsuma
Default admin password: Pristine@2024

###########################################

MANUAL BUILD

It’s best to use a Python Virtual Environment for installing the project dependencies. You can use the following code to create the virtual environment

virtualenv env

To activate the environment execute env\Scripts\activate.bat for Windows (or source env/bin/activate on Linux-based operating systems).

Having the VENV active, we can proceed and install the project dependencies:

pip install -r requirements.txt

ENVIRONMENT

Set up the environment

set FLASK_APP=run.py
set FLASK_ENV=development

RUNNING THE APP
Windows:
flask run
or
flask --app run.py run