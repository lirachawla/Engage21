import re
from app import *
from app.helperFunctions import *
from flask import (Blueprint, Flask, flash, g, redirect, render_template,
                   request, send_file, session, url_for)
from flask_mysqldb import MySQL
import hashlib
import os
from datetime import date
from werkzeug.utils import secure_filename
from datetime import datetime
import subprocess
import string
import secrets

main = Blueprint('main', __name__) 

@main.route('/', methods=['GET','POST'])
def home():
	user = getCurrentStudent()
	cur = mysql.connection.cursor()
	try:
		if user:
			return redirect(url_for('main.dashboard'))
		if request.method == 'POST':
			rollNumber = request.form['student-login-roll']
			password = hashlib.md5(request.form['student-login-password'].encode())
			result=None
			result = query_db("select * from login_student where rollNumber=%s;",(rollNumber,))
			if result:
				if result[0][2]==password.hexdigest():
					if str(result[0][3])=="1":
						session['rollNumber']=rollNumber
						return redirect(url_for('main.dashboard'))
					else:
						return render_template('login.html',loginFlag=2) 
				else:
					return render_template('login.html',loginFlag=0)
			else:
				return render_template('login.html',loginFlag=0)
		else:
			return render_template('login.html',loginFlag=1)
	except Exception as e:
		mysql.connection.rollback()
		flash("Something went wrong!", 'danger')
		return redirect(url_for('main.home'))
	finally:
		cur.close()

@main.route('/dashboard', methods=['GET'])
def dashboard():
	user=getCurrentStudent()
	cur = mysql.connection.cursor()
	if user:
		#remove next line when dashboard is ready
		return redirect(url_for('main.userProfile'))
		userDetails = query_db("select userID, rollNumber, firstName, lastName from student_details where userID=%s;",(user[0][0],))
		return render_template('dashboard.html',user=userDetails)
	else:
		return redirect(url_for('main.home'))

@main.route('/hostel-complaint', methods=['GET','POST'])
def studentCMS():
	user=getCurrentStudent()
	cur = mysql.connection.cursor()
	try:
		if user:
			userDetails = query_db("select userID, rollNumber, firstName, lastName from student_details where userID=%s;",(user[0][0],))
			if request.method == 'GET':
				showActiveComplaints = query_db("select * from cms where userID=%s and deleted=0 and status in (0,2,3,4);",(userDetails[0][0],))
				showVerifyComplaints = query_db("select * from cms where userID=%s and deleted=0 and status in (5);",(userDetails[0][0],))
				showPastComplaints = query_db("select * from cms where userID=%s and deleted=0 and status in (1,6,7,9);",(userDetails[0][0],))
				hostelLog=query_db("select * from hostel_log where userID=%s and active=1;",(userDetails[0][0],))
				if showActiveComplaints is None:
					showActiveComplaints =[]
				if showVerifyComplaints is None:
					showVerifyComplaints =[]
				if showPastComplaints is None:
					showPastComplaints =[]
				pastComplaints=[]
				activeComplaints=[]
				verifyComplaints=[]
				activeUpdates=[]
				verifyUpdates=[]
				for complaint in showPastComplaints:
					workerID = complaint[14]
					worker = query_db("select name, phone from cms_workers_details where workerID=%s;",(workerID,))
					if worker is None:
						worker=[["Not Available","Not Available"]]
					a=[]
					for i in complaint:
						a.append(i)
					a.append(worker[0][0])
					a.append(worker[0][1])
					pastComplaints.append(a)
				showPastComplaints=pastComplaints

				for complaint in showVerifyComplaints:
					workerID = complaint[14]
					worker = query_db("select name, phone from cms_workers_details where workerID=%s;",(workerID,))
					if worker is None:
						worker=[["Not Available","Not Available"]]
					a=[]
					for i in complaint:
						a.append(i)
					a.append(worker[0][0])
					a.append(worker[0][1])
					verifyComplaints.append(a)
					complaintID=complaint[0]
					updates = query_db("select updatedID,complaintID,timestamp,updates from complaint_updates where complaintID=%s;",(complaint[0],))
					if updates is None:
						updates = []
					for update in updates:
						verifyUpdates.append(update)	
				showVerifyComplaints=verifyComplaints

				for complaint in showActiveComplaints:
					workerID = complaint[14]
					worker = query_db("select name, phone from cms_workers_details where workerID=%s;",(workerID,))
					if worker is None:
						worker=[["Not Available","Not Available"]]
					a=[]
					for i in complaint:
						a.append(i)
					a.append(worker[0][0])
					a.append(worker[0][1])
					activeComplaints.append(a)
					complaintID=complaint[0]
					updates = query_db("select updatedID,complaintID,timestamp,updates from complaint_updates where complaintID=%s;",(complaint[0],))
					if updates is None:
						updates = []
					for update in updates:
						activeUpdates.append(update)	
				showActiveComplaints=activeComplaints
				complaintTypes = query_db("select * from complaint_types;")	
				if hostelLog is not None:
					hostelRoomID=hostelLog[0][4]
					hostelDetails = query_db("select * from hostel_details where hostelRoomID=%s;",(hostelRoomID,))
					hostelData = query_db("select * from hostel_data where hostelID=%s;",(hostelDetails[0][1],))
					return render_template('studentCMS.html',user=userDetails, activeComplaints = showActiveComplaints, verifyComplaints = showVerifyComplaints, pastComplaints = showPastComplaints, roomNo=hostelDetails[0][2], hostelName = hostelData[0][1], activeUpdates=activeUpdates,verifyUpdates=verifyUpdates, complaintTypes=complaintTypes)
				return render_template('studentCMS.html',user=userDetails, activeComplaints = showActiveComplaints, verifyComplaints = showVerifyComplaints, pastComplaints = showPastComplaints, roomNo="Not Applicable", hostelName="Not Applicable", activeUpdates=activeUpdates,verifyUpdates=verifyUpdates, complaintTypes=complaintTypes)
			if request.method=='POST':
				if request.form['submit']=='submitComplaint':
					complaintType = request.form['type-of-complaint']
					complaintSubject = request.form['complaint-subject']
					description = request.form['issue']
					date1 = request.form['date1']
					from1 = request.form['from1']
					to1 = request.form['to1']
					date2 = request.form['date2']
					from2 = request.form['from2']
					to2 = request.form['to2']
					date3 = request.form['date3']
					from3 = request.form['from3']
					to3 = request.form['to3']
					datetime1 = date1+"="+from1+"="+to1
					datetime2 = date2+"="+from2+"="+to2
					datetime3 = date3+"="+from3+"="+to3
					availabilityTime = datetime1+"###"+datetime2+"###"+datetime3
					curDate = datetime.now().strftime("%d-%m-%Y")
					curTime = datetime.now().strftime("%H:%M:%S")
					hostelLog=query_db("select * from hostel_log where userID=%s and active=1;",(userDetails[0][0],))
					hostelRoomID=-1
					hostelID=-1
					if hostelLog is not None:
						hostelRoomID=hostelLog[0][4]
						hostelDetails = query_db("select * from hostel_details where hostelRoomID=%s;",(hostelRoomID,))
						hostelID=hostelDetails[0][1]
					curTypes = query_db("select type from cms where deleted=0 and status in (0,2,3,4) and userID=%s;", (userDetails[0][0],))
					if curTypes is None:
						curTypes=[]
					else:
						curTypes=list(curTypes)
					rep = 0
					for curType in curTypes:
						if curType[0] == complaintType:
							rep = 1
					filename=''
					uploaded_file = request.files['filesComplaint']
					filename = secure_filename(uploaded_file.filename)
					if filename != '':
						file_ext = filename.split('.')[-1]
						filename = str(userDetails[0][0])+datetime.now().strftime("%H-%M-%S")+'.'+file_ext
						filepath='complaintImages/'+filename
						uploaded_file.save('app/static/complaintImages/'+filename)
						cur.execute('insert into cms (userID, hostelRoomID, type, subject, remarksStudent, hostelID, availabilityTime, attachment,times, date, repeated) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);',(user[0][0], hostelRoomID, complaintType, complaintSubject, description, hostelID, availabilityTime, filepath,curTime, curDate,rep,))
						mysql.connection.commit()
						flash("Complaint Registered Successfully!", 'success')
						return redirect(url_for('main.studentCMS'))
					else :
						cur.execute('insert into cms (userID, hostelRoomID, type, subject, remarksStudent, hostelID, availabilityTime, times, date, repeated) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);',(user[0][0], hostelRoomID, complaintType, complaintSubject, description, hostelID, availabilityTime, curTime, curDate,rep,))
						mysql.connection.commit()
						
						flash("Complaint Registered Successfully!", 'success')
						return redirect(url_for('main.studentCMS'))
				elif request.form['submit'].split(':')[0]=='deleteComplaint':
					complaintID=request.form['submit'].split(':')[1]
					cur.execute('update cms set deleted=1 where complaintID=%s;',(complaintID,))
					mysql.connection.commit()
					return redirect(url_for('main.studentCMS'))
				elif request.form['submit'].split(':')[0]=='feedbackSubmit':
					complaintID=request.form['submit'].split(':')[1]
					feedback = request.form['feedback']
					cur.execute('update cms set feedback=%s, status=%s where complaintID=%s;',(feedback,6,complaintID,))
					mysql.connection.commit()
					return redirect(url_for('main.studentCMS'))
		else:
			return redirect(url_for('main.home'))
	except Exception as e:
		mysql.connection.rollback()
		flash("Something went wrong!", 'danger')
		return redirect(url_for('main.studentCMS'))
	finally:
		cur.close()

@main.route('/logout')
def logout():
    user = getCurrentStudent()
    if user:
        session.pop('rollNumber', None)
        return redirect(url_for('main.home'))
    else:
        return redirect(url_for('main.home'))
        
@main.route('/user-profile', methods=['GET', 'POST'])
def userProfile():
	user=getCurrentStudent()
	cur = mysql.connection.cursor()
	if user:
		userDetails = query_db("select userID, rollNumber, firstName, lastName, emailStudent, DOB, course, branch from student_details where userID=%s;",(user[0][0],))
		hostelLog = query_db("select hostelRoomID from hostel_log where userID=%s;",(user[0][0],))
		hostelDetails = query_db("select hostelID, roomNumber, type from hostel_details where hostelRoomID=%s",(hostelLog[0][0],))
		hostelData = query_db("select hostelName, caretakerID, nightCaretakerID, wardenID from hostel_data where hostelID=%s",(hostelDetails[0][0],))
		hostelPeeps = []
		wardenDeets = query_db("select firstName, lastName, mobile, email, hostelEmail from warden_details where userID=%s;",(hostelData[0][3],))
		ctDeets = query_db("select firstName, lastName, mobile, email from caretaker_details where userID=%s;",(hostelData[0][1],))
		ntctDeets = query_db("select firstName, lastName, mobile, email from night_caretaker_details where userID=%s;",(hostelData[0][2],))
		hostelPeeps.append(wardenDeets[0])
		hostelPeeps.append(ctDeets[0])
		hostelPeeps.append(ntctDeets[0])
		if request.method=='GET':
			return render_template('changePassword.html',user=userDetails,hostelDetails=hostelDetails,hostelPeeps=hostelPeeps,hostelData=hostelData,passwordCheck=0,success=0)
		if request.method=='POST':
			if request.form['submit']=='Change Password':
				oldPassword = hashlib.md5(request.form['student-old-password'].encode())
				newPassword = hashlib.md5(request.form['student-new-password'].encode())
				result = query_db("select * from login_student where rollNumber=%s;",(user[0][1],))
				if result[0][2]==oldPassword.hexdigest():
					cur.execute("update login_student set password=%s where rollNumber=%s;", (newPassword.hexdigest(),user[0][1],))
					mysql.connection.commit()
					return render_template('changePassword.html',user=userDetails,hostelDetails=hostelDetails,hostelPeeps=hostelPeeps,hostelData=hostelData, passwordCheck=0,success=1)
				else:
					return render_template('changePassword.html',user=userDetails,hostelDetails=hostelDetails,hostelPeeps=hostelPeeps,hostelData=hostelData, passwordCheck=1,success=0)
			
	else:
		return redirect(url_for('main.home'))
	cur.close()
		
@main.route('/forgot-password', methods=['GET','POST'])
def forgotPassword():
	cur = mysql.connection.cursor()
	if request.method=='GET':
		return render_template('forgotPassword.html',detailsCheck=0,success=0)
	if request.method=='POST':
		rollNumber = request.form['student-roll']
		emailX= request.form['student-email']
		rollResult = query_db("select * from login_student where rollNumber=%s;", (rollNumber,))
		if rollResult is not None:
			emailResult = None
			emailResult = query_db("select emailStudent from student_details where rollNumber=%s;", (rollNumber,))
			if emailResult and emailResult[0][0]==emailX:
				password=None
				alphabet = string.ascii_letters + string.digits
				while True:
    					password = ''.join(secrets.choice(alphabet) for i in range(10))
    					if (any(c.islower() for c in password)
            							and any(c.isupper() for c in password)
            							and sum(c.isdigit() for c in password) >= 3):
        					break
				mailBody="Dear Student\n\nHere is your updated password for the hostel webkiosk.\n{}\nKindly change it as soon as possible.\nTHIS IS AN AUTOMATED MESSAGE- PLEASE DO NOT REPLY.\n\nThank You!".format(password)
				curDateTime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
				mailSubject="Hostel Webkiosk Password Reset at "+str(curDateTime)
				receiversEmail = query_db("select emailStudent from student_details where rollNumber=%s",(rollNumber,))
				if email(mailBody,mailSubject,receiversEmail)=="OK":
					cur.execute("update login_student set password=%s where rollNumber=%s;", (hashlib.md5(password.encode()).hexdigest(),rollNumber,))
					mysql.connection.commit()
					return render_template('forgotPassword.html',detailsCheck=0,success=1)
				else:
					return render_template('forgotPassword.html',detailsCheck=0,success=0) 
			else:
				return render_template('forgotPassword.html',detailsCheck=1,success=0)
		else:
			return render_template('forgotPassword.html',detailsCheck=1,success=0)
	cur.close()

