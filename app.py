from __future__ import print_function
from unicodedata import name
from flask import Flask, request, render_template, redirect, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, time, date, timedelta
import numpy as np
import pickle
import pytz
import sys
from sqlalchemy import exc
import requests
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = b'_5#y2LMPDER"FHUEJN189451O4Q8z\n\xec]/'
#making a db file for all patient appointments
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patients.db'
# #making a db file for hospital login
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///login.db'
#for hashing password
bcrypt = Bcrypt(app)
#initialize db databse
db =  SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view="login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


model = pickle.load(open('model.pkl', 'rb'))

#model for login
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(20), nullable = False, unique = True)
    password = db.Column(db.String(80), nullable = False)

#create db model/schema for patients
class Patients(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    datetime_ist = datetime.now(pytz.timezone('Asia/Kolkata'))
    date_created = db.Column(db.DateTime, default = datetime_ist)
    name = db.Column(db.String(200), nullable = False)
    phone = db.Column(db.Integer, nullable = False)
    age = db.Column(db.Integer, nullable = False)
    issue = db.Column(db.String(200), nullable = False)
    treatment_time = db.Column(db.Float, nullable = False)
    app_date = db.Column(db.Date)
    app_time = db.Column(db.String(200))
    #used this to delete a patients data on that specidic day and specific time slot
    available_date_time = db.Column(db.DateTime, default = datetime_ist )
    #create a function to return string when we add something
    def __repr__(self):
        return '<Name %r>' % self.id

db.create_all()

#regitering user
class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder":"Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder":"Password"})
    submit = SubmitField("Register")
    def validate_user(self, username):
        existing_user_usrname = User.query.filter_by(username = username.data).first()
        if existing_user_usrname:
            raise ValidationError("Choose another name")


#login user
class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder":"Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder":"Password"})
    submit = SubmitField("Login")

@app.route("/")
def home():
    return render_template('index.html')


@app.route("/login", methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username = form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('allpatients'))
                
    return render_template('login.html', form=form)

@app.route("/register", methods=['GET','POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username = form.username.data, password= hashed_password)
        db.session.add(new_user)
        db.session.commit()
    return render_template('register.html', form=form)


@app.route("/delete/<int:id>")
def delete(id):
    patient_to_delete = Patients.query.get_or_404(id)  
    #deleting entry of the specific person and updating new time for everyone else
    allpatients = Patients.query.filter_by(available_date_time=patient_to_delete.available_date_time).all()
    try:
        time_change = patient_to_delete.treatment_time
        for patient in allpatients:
            if(patient.id > id):
                app_date = str(patient.app_date)
                app_date_and_time = app_date+" "+patient.app_time
                app_date_time = datetime.strptime(app_date_and_time, '%Y-%m-%d %H:%M:%S')
                new_app_date_time = app_date_time - timedelta(minutes=time_change) + timedelta(seconds=1)
                new_time = new_app_date_time.strftime("%H:%M:%S")
                patient.app_time = new_time
                db.session.commit()

        db.session.delete(patient_to_delete)
        db.session.commit()

        return redirect('/allpatients')
    except exc.IntegrityError as e:
        errorInfo = e.orig.args
        print(errorInfo[0], file=sys.stderr)  #This will give you error code
        print("Oops!", sys.exc_info()[0], "occurred." , file=sys.stderr)
        return "Could not delete"


@app.route("/allpatients", methods = ['GET','POST'])
@login_required
def allpatients():
    allpatients = Patients.query.order_by(Patients.app_date, Patients.app_time)
    return render_template("allpatients.html", allpatients=allpatients)


@app.route("/predict", methods=['POST'])
def predict():
    #getting data from form
    pname = request.form['name']
    pnumber = request.form['number']
    page = request.form['age']
    pissue = request.form['issue']
    
    # converting issue to decimal for ml prediction
    issuenum = 0
    if(pissue == "fever"):
        issuenum = 0.1
    else:
        issuenum = 0.4

    #set date and time of appointment for a specific day from form 
    form_app_date = request.form['app_date']
    form_app_time = request.form['time']
    app_date_and_timeslot = form_app_date +" "+ form_app_time
    app_date_and_timeslot = datetime.strptime(app_date_and_timeslot, '%Y-%m-%d %H:%M:%S')
    
    #for queueing purpose
    #get the appointment time uptil the last entry
    allpatients = Patients.query.filter_by(available_date_time = app_date_and_timeslot).all()
    timeSum=0
    for patient in allpatients:
        timeSum += patient.treatment_time
    timeSum = round(timeSum, 2)

    #for that patient's appointment date and time
    patient_date_time = app_date_and_timeslot + timedelta(minutes=timeSum)
    patient_date = patient_date_time.strftime("%Y-%m-%d")
    patient_date = datetime.strptime(patient_date, '%Y-%m-%d').date()
    patient_time = patient_date_time.strftime("%H:%M:%S")


    #for finding the treatement time using ml and storing it in database
    predicted_time = model.predict([[page,issuenum]])
    output = round(predicted_time[0],2)
    
    #adding a new patient in database
    new_patient = Patients(name=pname, phone=pnumber, age=page,issue=pissue,treatment_time=output, app_date = patient_date, app_time=patient_time , available_date_time = app_date_and_timeslot)
    try:
        db.session.add(new_patient)
        db.session.commit()

        #sending sms to the patient if the patient gets successfully added in database
        url = "https://www.fast2sms.com/dev/bulkV2"

        payload = {
            'message' : "Thank You for booking an appointment. \n Dear {},%20".format(pname)+ "your appointment is scheduled on {} ".format(patient_date)+"at {} ".format(patient_time) +"\n Please be present 20 minutes prior to your scheduled time.",
            'language' : "english",
            'route' : "q",
            'numbers' : "{}".format(pnumber),
        }
        headers = {
            'authorization': "kiALcCSwIyxePsVmZHqNOjlJXWahUgB1T8ruvdnoD9bE5KY72pvxD9oKmwPOIEfVtQZ7g80phLlYb5dy",
            'Content-Type': "application/x-www-form-urlencoded",
            'Cache-Control': "no-cache",
            }
        #response = requests.request("POST", url, data=payload, headers=headers)
        #print(response.text, file=sys.stderr)


        flash("Thank You for booking an appointment. \n Dear {},%20".format(pname)+ "your appointment is scheduled on {} ".format(patient_date)+"at {} ".format(patient_time) +"\n Please be present 20 minutes prior to your scheduled time. An SMS will be sent regarding the same on the registered mobile number")
        return redirect('/')

    except exc.IntegrityError as e:
        errorInfo = e.orig.args
        print(errorInfo[0], file=sys.stderr)  #This will give you error code
        print("Oops!", sys.exc_info()[0], "occurred." , file=sys.stderr)
        return 'error'
  


   
