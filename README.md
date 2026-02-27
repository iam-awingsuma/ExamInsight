<h1>ExamInsight<h1></h1>
Attainment and Progress Tracking in Year 2 Internal Assessments and External Benchmark Tests at Pristine Private School.
<hr />
Default admin username: <b><i>awingsuma</i></b><br />
Default admin password: <b><i>Pristine@2024</i></b>
<hr />
<h3>MANUAL BUILD</h3>

<b>Prerequisite:</b>
The Python version required for this build to avoid issues is <b>python 3.12</b>

It’s best to use a Python Virtual Environment for installing the project dependencies. You can use the following code to create the virtual environment

<code>virtualenv env</code>

If you are using Python 3, you don't need <code>virtualenv</code> anymore because Python 3 already includes a virtual environment tool.

Just run:

<code>python3 venv env</code>

*** <code>env</code> is the name of the virtual environment

To activate the environment execute <code>env\Scripts\activate.bat</code> for Windows (or <code>source env/bin/activate</code> on Mac/Linux-based operating systems).

Having the VENV active, we can proceed and install the project dependencies:

<code>pip install -r requirements.txt</code>

<h3>ENVIRONMENT</h3>

<h4>SETUP THE ENVIRONMENT</h4>

<code>set FLASK_APP=run.py</code><br/>
<code>set FLASK_ENV=development</code><br/>
<code>set FLASK_DEBUG=1</code>

or you can use the following option:<br/><br/>
<code>export FLASK_APP=run.py</code><br/>
<code>export FLASK_ENV=development</code><br/>
<code>export FLASK_DEBUG=1</code>

<h4>RUNNING THE APP</h4>
Windows:
<code>flask run</code>
or
<code>flask --app run.py --debug run</code><br/>
to run the app with automatic reload when file changes<br/>
or use the most common and recommended way to enable auto-reloading 
<code>flask --app run.py --debug run</code><br/><br/>

Alternatively, use the following if you encounter issues when running the app:<br/>
<code>python -m flask --app run run</code><br/>
to avoid PATH issues.