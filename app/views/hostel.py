from os import stat
from werkzeug import utils
from app import *
from app.helperFunctions import *
from flask import (Blueprint, Flask, flash, g, redirect, render_template,
                   request, send_file, session, url_for)
from flask_mysqldb import MySQL
import hashlib
from werkzeug.utils import secure_filename
from datetime import datetime
import re
import csv
from datetime import date
import subprocess
import string
import secrets
import pandas as pd

hostel = Blueprint('hostel', __name__, url_prefix='/hostel') 

@hostel.route('/', methods=['GET','POST'])
def home():
	user = getCurrentHostelUser()
	cur = mysql.connection.cursor()
	try:
		if user:
			return redirect(url_for('hostel.dashboard'))
		if request.method == 'POST':
			employeeID = request.form['hostel-login-employeeID']
			password = hashlib.md5(request.form['hostel-login-password'].encode())
			result=None
			result = query_db("select * from login_hostel where employeeID=%s;",(employeeID,))
			if result:
				if result[0][1]==password.hexdigest():
					session['employeeID']=employeeID
					session['whatIsMyRole']="departmentOfHostelManagement"
					return redirect(url_for('hostel.dashboard'))
				else:
					return render_template('hostel/login.html',loginFlag=0)
			else:
				return render_template('hostel/login.html',loginFlag=0)
		else:
			return render_template('hostel/login.html',loginFlag=1)
	except Exception as e:
		mysql.connection.rollback()
		flash("Something went wrong!", 'danger')
		return redirect(url_for('hostel.home'))
	finally:
		cur.close()

@hostel.route('/dashboard', methods=['GET'])
def dashboard():
	user=getCurrentHostelUser()
	if user:
		return redirect(url_for('hostel.hostelCMS'))
		employee=query_db("select * from hostel_employee_mapping where employeeID=%s;",(user[0][0],))
		employeeDetails = []
		if(employee[0][1]==0):
			employeeDetails=query_db("select * from warden_details where userID=%s;",(employee[0][2],))
		elif(employee[0][1]==1):
			employeeDetails=query_db("select * from caretaker_details where userID=%s;",(employee[0][2],))
		elif(employee[0][1]==2):
			employeeDetails=query_db("select * from night_caretaker_details where userID=%s;",(employee[0][2],))
		employeeHostelID=employeeDetails[0][6]
		employeeHostelDetails = query_db("select * from hostel_data where hostelID=%s;",(employeeHostelID,))
		return render_template('hostel/dashboard.html',user=employeeDetails, employeeRole=employee[0][1])
	else:
		return redirect(url_for('hostel.home'))

@hostel.route('/lodge-complaint', methods=['GET','POST'])
def lodgeComplaint():
	user=getCurrentHostelUser()
	cur = mysql.connection.cursor()
	if user:
		employee=query_db("select * from hostel_employee_mapping where employeeID=%s;",(user[0][0],))
		employeeDetails = []
		if(employee[0][1]==0):
			employeeDetails=query_db("select * from warden_details where userID=%s;",(employee[0][2],))
		elif(employee[0][1]==1):
			employeeDetails=query_db("select * from caretaker_details where userID=%s;",(employee[0][2],))
		elif(employee[0][1]==2):
			employeeDetails=query_db("select * from night_caretaker_details where userID=%s;",(employee[0][2],))
		employeeID = employee[0][0]
		employeeRole = employee[0][1]
		employeeUserID = employee[0][2]
		employeeFName = employeeDetails[0][1]
		employeeSName = employeeDetails[0][2]
		employeeGender = employeeDetails[0][3]
		employeePic = employeeDetails[0][5]
		employeePhone = employeeDetails[0][4]
		hostelID = int(employeeDetails[0][6])
		userData = [employeeID,employeeUserID,employeeRole,employeeFName,employeeSName,employeeGender,employeePic,employeePhone,hostelID]
		hostelRoomData = query_db("select hostelRoomID, roomNumber from hostel_details where hostelID=%s;",(hostelID,))
		if hostelRoomData is None:
			roomDict={}
			hostelRoomData=[]
		else:
			roomDict = dict(hostelRoomData)
		hostelName = query_db("select * from hostel_data where hostelID=%s;",(hostelID,))[0][1]
		if request.method=="GET":
			showActiveComplaints = query_db("select * from cms where hostelID=%s and deleted=2 and status in (3,4);",(hostelID,))
			showPastComplaints = query_db("select * from cms where hostelID=%s and deleted=2 and status in (8);",(hostelID,))
			activeUpdates = []
			pastComplaints=[]	
			activeComplaints=[]	
			pastUpdates=[]
			if showPastComplaints is None:
				showPastComplaints = []
			for complaint in showPastComplaints:
				updates = query_db("select updatedID,complaintID,timestamp,updates from complaint_updates where complaintID=%s;",(complaint[0],))
				if updates is None:
					updates = []
				for update in updates:
					pastUpdates.append(update)
			if showActiveComplaints is None:
				showActiveComplaints =[]
			for complaint in showActiveComplaints:
				updates = query_db("select updatedID,complaintID,timestamp,updates from complaint_updates where complaintID=%s;",(complaint[0],))
				if updates is None:
					updates = []
				for update in updates:
					activeUpdates.append(update)
			for i in range(len(showActiveComplaints)):
				complaintID=showActiveComplaints[i][0]
				complaintUserID=showActiveComplaints[i][1]
				hostelRoomID=showActiveComplaints[i][2]
				complaintType=showActiveComplaints[i][3]
				subject = showActiveComplaints[i][4]
				description=showActiveComplaints[i][5]
				time = showActiveComplaints[i][6]
				date = showActiveComplaints[i][13]
				status = showActiveComplaints[i][7]
				image = showActiveComplaints[i][11]
				sev=showActiveComplaints[i][16]
				if image is None:
					image = "1"
				workerID = showActiveComplaints[i][14]
				workerDeets=[]
				if workerID!=0:
					workerDeets = query_db("select name, phone from cms_workers_details where workerID=%s;",(workerID,))
				else:
					workerID="Not Available"
					workerDeets=[["Not Available","Not Available"]]
				workerName = workerDeets[0][0]
				workerNumber = workerDeets[0][1]
				complaint=[complaintID,complaintType,subject,description,time,date,status,complaintUserID,workerName,workerNumber,image,hostelRoomID,sev]
				activeComplaints.append(complaint)
			for i in range(len(showPastComplaints)):
				complaintID=showPastComplaints[i][0]
				complaintUserID=showPastComplaints[i][1]
				hostelRoomID=showPastComplaints[i][2]
				complaintType=showPastComplaints[i][3]
				subject=showPastComplaints[i][4]
				description=showPastComplaints[i][5]
				time=showPastComplaints[i][6]
				date=showPastComplaints[i][13]
				status=showPastComplaints[i][7]
				image=showPastComplaints[i][11]
				if image is None:
					image = "1"
				workerID = showPastComplaints[i][14]
				workerDeets=[]
				if workerID!=0:
					workerDeets = query_db("select name, phone from cms_workers_details where workerID=%s;",(workerID,))
				else:
					workerID="Not Available"
					workerDeets=[["Not Available","Not Available"]]
				workerName = workerDeets[0][0]
				workerNumber = workerDeets[0][1]
				dateCompleted = showPastComplaints[i][15]
				sev=showPastComplaints[i][16]
				complaint=[complaintID,complaintType,subject,description,time,date,status,complaintUserID,workerName,workerNumber,image,hostelRoomID,dateCompleted,sev]
				pastComplaints.append(complaint)
			complaintTypes = query_db("select * from complaint_types;")
			return render_template('hostel/lodgeComplaint.html',user=userData, activeUpdates=activeUpdates,pastUpdates=pastUpdates, activeComplaints=activeComplaints,  pastComplaints=pastComplaints, hostelRoomData = hostelRoomData, hostelName=hostelName,roomDict=roomDict, complaintTypes=complaintTypes)
		if request.method=="POST":
			submittedReq = request.form['submit']
			if submittedReq =='submitComplaint':
				complaintType = request.form['type-of-complaint']
				severity = request.form['sev-of-complaint']
				complaintSubject = request.form['complaint-subject']
				HostelRoomID = request.form['room-number']
				description = request.form['issue']
				curDate = datetime.now().strftime("%d-%m-%Y")
				curTime = datetime.now().strftime("%H:%M:%S")
				filename=''
				uploaded_file = request.files['filesComplaint']
				availibilityString = "Hostel Complaint"
				filename = secure_filename(uploaded_file.filename)
				if filename != '':
					file_ext = filename.split('.')[-1]
					filename = str(userData[0])+datetime.now().strftime("%H-%M-%S")+'.'+file_ext
					filepath='complaintImages/'+filename
					uploaded_file.save('app/static/complaintImages/'+filename)
					cur.execute('insert into cms (userID, hostelRoomID, type, subject, remarksStudent, hostelID, availabilityTime, attachment,times, date,status,deleted,severity) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);',(userData[0], HostelRoomID, complaintType, complaintSubject, description, userData[8], availibilityString, filepath,curTime, curDate,3,2,severity,))
					mysql.connection.commit()
					flash("Complaint Registered Successfully!", 'success')
					return redirect(url_for('hostel.lodgeComplaint'))
				else :
					filepath="1"
					cur.execute('insert into cms (userID, hostelRoomID, type, subject, remarksStudent, hostelID, availabilityTime, times, date,attachment,status,deleted,severity) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);',(userData[0], HostelRoomID, complaintType, complaintSubject, description,userData[8], availibilityString, curTime, curDate,filepath,3,2,severity,))
					mysql.connection.commit()
					flash("Complaint Registered Successfully!", 'success')
					return redirect(url_for('hostel.lodgeComplaint'))
			elif submittedReq.split(':')[0]=="update":
				complaintID = submittedReq.split(':')[1]
				update = request.form['updateNew']
				curDateTime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
				cur.execute('insert into complaint_updates (complaintID,timestamp,updates,updatedBy) values (%s,%s,%s,%s);',(complaintID,curDateTime,update,employeeID,))
				mysql.connection.commit()
			elif submittedReq.split(':')[0]=="markCompleted":
				complaintID = submittedReq.split(':')[1]
				filename=query_db("select attachment from cms where complaintID=%s",(complaintID,))
				if filename is not None and filename[0] is not None and filename[0][0]!="1":
					os.remove('app/static/'+filename[0][0])
				update = request.form['updateNew']
				update = "Marked Completed: "+ update
				curDateTime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
				cur.execute('insert into complaint_updates (complaintID,timestamp,updates,updatedBy) values (%s,%s,%s,%s);',(complaintID,curDateTime,update,employeeID,))
				cur.execute('update cms set status=8 where complaintID=%s;',(complaintID,))
				curDate = datetime.now().strftime("%d-%m-%Y")
				cur.execute('update cms set dateCompleted=%s where complaintID=%s;',(curDate,complaintID,))
				mysql.connection.commit() 
			elif request.form['submit'].split(':')[0]=='deleteComplaint':
				complaintID=request.form['submit'].split(':')[1]
				cur.execute('update cms set deleted=1 where complaintID=%s;',(complaintID,))
				mysql.connection.commit()
			return redirect(url_for('hostel.lodgeComplaint'))
	else:
		return redirect(url_for('hostel.home'))	


@hostel.route('/hostel-complaint', methods=['GET','POST'])
def hostelCMS():
	user=getCurrentHostelUser()
	cur = mysql.connection.cursor()
	if user:
		employee=query_db("select * from hostel_employee_mapping where employeeID=%s;",(user[0][0],))
		employeeDetails = []
		if(employee[0][1]==0):
			employeeDetails=query_db("select * from warden_details where userID=%s;",(employee[0][2],))
		elif(employee[0][1]==1):
			employeeDetails=query_db("select * from caretaker_details where userID=%s;",(employee[0][2],))
		elif(employee[0][1]==2):
			employeeDetails=query_db("select * from night_caretaker_details where userID=%s;",(employee[0][2],))
		employeeHostelID=employeeDetails[0][6]
		if request.method == 'GET':
			showPendingComplaints = query_db("select * from cms where deleted=0 and status=0 and hostelID=%s;",(employeeHostelID,))
			showActiveComplaints = query_db("select * from cms where deleted=0 and status in (2,3,4) and hostelID=%s;",(employeeHostelID,))
			showResolvedComplaints = query_db("select * from cms where deleted=0 and status in (6,7,5) and hostelID=%s order by complaintID DESC LIMIT 20;",(employeeHostelID,))
			showRejectedComplaints = query_db("select * from cms where deleted=0 and status in (1,9) and hostelID=%s order by complaintID DESC LIMIT 20;",(employeeHostelID,))
			pendingComplaints=[]
			activeComplaints=[]	
			resolvedComplaints=[]
			rejectedComplaints=[]
			activeUpdates = []
			if showActiveComplaints is None:
				showActiveComplaints =[]
			if showPendingComplaints is None:
				showPendingComplaints =[]
			if showRejectedComplaints is None:
				showRejectedComplaints =[]
			if showResolvedComplaints is None:
				showResolvedComplaints =[]
			for complaint in showActiveComplaints:
				complaintID=complaint[0]
				updates=[]
				updates = query_db("select updatedID,complaintID,timestamp,updates from complaint_updates where complaintID=%s;",(complaint[0],))
				if updates is None:
					updates = []
				for update in updates:
					activeUpdates.append(update)			

			for i in range(len(showActiveComplaints)):
				complaintID=showActiveComplaints[i][0]
				userID=showActiveComplaints[i][1]
				hostelDetails=query_db("select * from hostel_details where hostelRoomID=%s;",(showActiveComplaints[i][2],))
				roomNo=hostelDetails[0][2]
				studentDeets = query_db("select rollNumber,firstName,lastName,mobileStudent from student_details where userID=%s;",(userID,))
				studentFName = studentDeets[0][1]
				studentSName = studentDeets[0][2]
				rollNumber = studentDeets[0][0]
				contact = studentDeets[0][3]
				complaintType=showActiveComplaints[i][3]
				subject = showActiveComplaints[i][4]
				description=showActiveComplaints[i][5]
				time = showActiveComplaints[i][6]
				date = showActiveComplaints[i][13]
				status = showActiveComplaints[i][7]
				image = showActiveComplaints[i][11]
				if image is None:
					image = "1"
				workerID = showActiveComplaints[i][14]
				workerDeets=[]
				if workerID!=0:
					workerDeets = query_db("select name,phone from cms_workers_details where workerID=%s;",(workerID,))
				else:
					workerID="Not Alloted"
					workerDeets=[["Not Alloted","Not Alloted"]]
				workerName = workerDeets[0][0]
				workerNumber = workerDeets[0][1]
				complaint=[complaintID,complaintType,subject,studentFName,studentSName,rollNumber,roomNo,description,time,date,status,workerID,workerName,workerNumber,image,contact]
				activeComplaints.append(complaint)

			for i in range(len(showPendingComplaints)):
				complaintID=showPendingComplaints[i][0]
				userID=showPendingComplaints[i][1]
				hostelDetails=query_db("select * from hostel_details where hostelRoomID=%s;",(showPendingComplaints[i][2],))
				roomNo=hostelDetails[0][2]
				studentDeets = query_db("select rollNumber,firstName,lastName,mobileStudent from student_details where userID=%s;",(userID,))
				studentFName = studentDeets[0][1]
				studentSName = studentDeets[0][2]
				rollNumber = studentDeets[0][0]
				contact = studentDeets[0][3]
				complaintType=showPendingComplaints[i][3]
				subject = showPendingComplaints[i][4]
				description=showPendingComplaints[i][5]
				time = showPendingComplaints[i][6]
				date = showPendingComplaints[i][13]
				status = showPendingComplaints[i][7]
				image = showPendingComplaints[i][11]
				rep = showPendingComplaints[i][18]
				if image is None:
					image = "1"
				complaint=[complaintID,complaintType,subject,studentFName,studentSName,rollNumber,roomNo,description,time,date,status,image,rep,contact]
				pendingComplaints.append(complaint)

			for i in range(len(showResolvedComplaints)):
				complaintID=showResolvedComplaints[i][0]
				userID=showResolvedComplaints[i][1]
				hostelDetails=query_db("select * from hostel_details where hostelRoomID=%s;",(showResolvedComplaints[i][2],))
				roomNo=hostelDetails[0][2]
				studentDeets = query_db("select rollNumber,firstName,lastName,mobileStudent from student_details where userID=%s;",(userID,))
				studentFName = studentDeets[0][1]
				studentSName = studentDeets[0][2]
				rollNumber = studentDeets[0][0]
				contact = studentDeets[0][3]
				complaintType=showResolvedComplaints[i][3]
				subject=showResolvedComplaints[i][4]
				description=showResolvedComplaints[i][5]
				time = showResolvedComplaints[i][6]
				date = showResolvedComplaints[i][13]
				status = showResolvedComplaints[i][7]
				feedback=showResolvedComplaints[i][12]
				workerID = showResolvedComplaints[i][14]
				dateCompleted = showResolvedComplaints[i][15]
				workerDeets=[]
				if workerID!=0:
					workerDeets = query_db("select name,phone from cms_workers_details where workerID=%s;",(workerID,))
				else:
					workerID="NULL"
					workerDeets=[["NULL","NULL"]]
				workerName = workerDeets[0][0]
				workerNumber = workerDeets[0][1]
				complaint=[complaintID,complaintType,subject,studentFName,studentSName,rollNumber,roomNo,description,time,date,status,workerID,workerName,workerNumber,feedback,dateCompleted,contact]
				resolvedComplaints.append(complaint)
			
			for i in range(len(showRejectedComplaints)):
				complaintID=showRejectedComplaints[i][0]
				userID=showRejectedComplaints[i][1]
				hostelDetails=query_db("select * from hostel_details where hostelRoomID=%s;",(showRejectedComplaints[i][2],))
				roomNo=hostelDetails[0][2]
				studentDeets = query_db("select rollNumber,firstName,lastName,mobileStudent from student_details where userID=%s;",(userID,))
				studentFName = studentDeets[0][1]
				studentSName = studentDeets[0][2]
				rollNumber = studentDeets[0][0]
				contact = studentDeets[0][3]
				complaintType=showRejectedComplaints[i][3]
				subject=showRejectedComplaints[i][4]
				description=showRejectedComplaints[i][5]
				time = showRejectedComplaints[i][6]
				date = showRejectedComplaints[i][13]
				status = showRejectedComplaints[i][7]
				feedback=showRejectedComplaints[i][12]
				workerID = showRejectedComplaints[i][14]
				dateCompleted = showRejectedComplaints[i][15]
				workerDeets=[]
				if workerID!=0:
					workerDeets = query_db("select name,phone from cms_workers_details where workerID=%s;",(workerID,))
				else:
					workerID="NULL"
					workerDeets=[["NULL","NULL"]]
				workerName = workerDeets[0][0]
				workerNumber = workerDeets[0][1]
				complaint=[complaintID,complaintType,subject,studentFName,studentSName,rollNumber,roomNo,description,time,date,status,workerID,workerName,workerNumber,feedback,dateCompleted,contact]
				rejectedComplaints.append(complaint)
			return render_template('hostel/hostelCMS.html',user=employeeDetails, employeeRole=employee[0][1], pendingComplaints=pendingComplaints, activeComplaints=activeComplaints, resolvedComplaints=resolvedComplaints, rejectedComplaints=rejectedComplaints, activeUpdates=activeUpdates)	
		if request.method=="POST":
			submittedReq = request.form["submit"]
			if submittedReq.split(':')[0]=="accepted":
				complaintID = submittedReq.split(':')[1]
				update = request.form['update']
				update = "Complaint Approved :" + update
				curDateTime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
				cur.execute('insert into complaint_updates (complaintID,timestamp,updates,updatedBy) values (%s,%s,%s,%s);',(complaintID,curDateTime,update,employee[0][0],))
				cur.execute('update cms set status=3 where complaintID=%s;',(complaintID,))
				mysql.connection.commit()
			elif submittedReq.split(':')[0]=="rejected":
				complaintID = submittedReq.split(':')[1]
				update = request.form['update']
				update = "Complaint Rejected :"+update
				curDateTime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
				cur.execute('insert into complaint_updates (complaintID,timestamp,updates,updatedBy) values (%s,%s,%s,%s);',(complaintID,curDateTime,update,employee[0][0],))
				cur.execute('update cms set status=1 where complaintID=%s;',(complaintID,))
				mysql.connection.commit()
			elif submittedReq.split(':')[0]=="inhouse":
				complaintID = submittedReq.split(':')[1]
				update = request.form['update']
				update = "Complaint Inhouse: "+update
				curDateTime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
				cur.execute('insert into complaint_updates (complaintID,timestamp,updates,updatedBy) values (%s,%s,%s,%s);',(complaintID,curDateTime,update,employee[0][0],))
				cur.execute('update cms set status=2, inHouse=1 where complaintID=%s;',(complaintID,))
				mysql.connection.commit()
			elif submittedReq.split(':')[0]=="update":
				complaintID = submittedReq.split(':')[1]
				update = request.form['updateNew']
				curDateTime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
				cur.execute('insert into complaint_updates (complaintID,timestamp,updates,updatedBy) values (%s,%s,%s,%s);',(complaintID,curDateTime,update,employee[0][0],))
				mysql.connection.commit()
			elif submittedReq.split(':')[0]=="discard":
				complaintID = submittedReq.split(':')[1]
				update = request.form['updateNew']
				curDateTime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
				cur.execute('insert into complaint_updates (complaintID,timestamp,updates,updatedBy) values (%s,%s,%s,%s);',(complaintID,curDateTime,update,employee[0][0],))
				cur.execute('update cms set status=1 where complaintID=%s;',(complaintID,))
				mysql.connection.commit()
			elif submittedReq.split(':')[0]=="markCompleted":
				complaintID = submittedReq.split(':')[1]
				filename=query_db("select attachment from cms where complaintID=%s",(complaintID,))
				if filename is not None and filename[0] is not None and filename[0][0] is not None:
					if(os.path.isfile('app/static/'+filename[0][0])):
						os.remove('app/static/'+filename[0][0])
				update = request.form['updateNew']
				update = "Marked Completed: "+ update
				curDate = datetime.now().strftime("%d-%m-%Y")
				curDateTime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
				cur.execute('insert into complaint_updates (complaintID,timestamp,updates,updatedBy) values (%s,%s,%s,%s);',(complaintID,curDateTime,update,employee[0][0],))
				cur.execute('update cms set status=5 where complaintID=%s;',(complaintID,))
				cur.execute('update cms set dateCompleted=%s where complaintID=%s;',(curDate,complaintID,))
				mysql.connection.commit()
			elif submittedReq.split(':')[0]=="markAllApproved":
				complaints = query_db("select complaintID from cms where status=0 and hostelID=%s and deleted=0;",(employeeHostelID,))
				if complaints is None:
					complaints = []
				update = "Approved via `Approve all`"
				curDateTime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
				for complaint in complaints:
					cur.execute('insert into complaint_updates (complaintID,timestamp,updates,updatedBy) values (%s,%s,%s,%s);',(complaint[0],curDateTime,update,employee[0][0],))
				cur.execute('update cms set status=3 where status=0 and hostelID=%s and deleted=0;',(employeeHostelID,))
				mysql.connection.commit()
			return redirect(url_for('hostel.hostelCMS'))


	else:
		return redirect(url_for('hostel.home'))


@hostel.route('/generate-report', methods=["POST","GET"])
def generateReport():
	user=getCurrentHostelUser()
	if user:
		employee=query_db("select * from hostel_employee_mapping where employeeID=%s;",(user[0][0],))
		employeeDetails = []
		if(employee[0][1]==0):
			employeeDetails=query_db("select firstName, lastName from warden_details where userID=%s;",(employee[0][2],))
			fhostelID=(query_db("select hostelID from warden_details where userID=%s;",(employee[0][2],)))[0][0]
		elif(employee[0][1]==1):
			employeeDetails=query_db("select firstName, lastName from caretaker_details where userID=%s;",(employee[0][2],))
			fhostelID=(query_db("select hostelID from caretaker_details where userID=%s;",(employee[0][2],)))[0][0]
		elif(employee[0][1]==2):
			employeeDetails=query_db("select firstName, lastName from night_caretaker_details where userID=%s;",(employee[0][2],))
			fhostelID=(query_db("select hostelID from night_caretaker_details where userID=%s;",(employee[0][2],)))[0][0]
		if request.method=="GET":
			complaintTypes = query_db("select * from complaint_types;")
			return render_template('hostel/generateReport.html', user=employeeDetails, complaintTypes=complaintTypes)
		elif request.method=="POST":
			startDate=date(int(request.form['startDate'].split('-')[2]),int(request.form['startDate'].split('-')[1]),int(request.form['startDate'].split('-')[0]))
			endDate=date(int(request.form['endDate'].split('-')[2]),int(request.form['endDate'].split('-')[1]),int(request.form['endDate'].split('-')[0]))
			complaintTypeCheck = request.form['type-of-complaint']
			statusCheck = request.form['status']
			allData = query_db('select * from cms where hostelID=%s and deleted<>1 order by complaintID desc;',(fhostelID,))
			hostelName = (query_db('select hostelName from hostel_data where hostelID=%s;',(fhostelID,)))[0][0]
			roomData = query_db('select hostelRoomID, roomNumber from hostel_details where hostelID=%s;',(fhostelID,))
			workerData = query_db('select workerID, name from cms_workers_details;')
			if workerData is None:
				workerData={}
			else:
				workerData=dict(workerData)
			if allData is None:
				allData = []
			else:
				allData = list(allData)	
			if roomData is None:
				roomData = {}
			else:
				roomData = dict(roomData)
			roomData[1]="Hostel Complaint"
			curDateTime = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
			filename = 'complaintsReport-'+str(employee[0][0])+"-"+str(curDateTime)+".csv"
			with open('app/static/complaintReports/'+filename, 'w') as csvfile:
				fieldnames = ['Complaint ID', 'Roll number/ User ID', 'Hostel', 'Room No', 'Complaint Type', 'Subject', 'Student Remarks', 'Date', 'Time', 'Status', 'Availability Date 1', 'From Time 1', 'To Time 1', 'Availability Date 2', 'From Time 2', 'To Time 2', 'Availability Date 3', 'From Time 3', 'To Time 3', 'Feedback', 'Worker', 'Date Completed', 'Severity', 'In house', ]
				writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
				writer.writeheader()
				
				for record in allData:
					complaintId=record[0]
					userId=record[1]
					hostelRoom=roomData[record[2]]
					complaintType=record[3]
					subject=record[4]
					remarksStudent=record[5]
					time=record[6]
					status=record[7]
					availabilityTime=record[10]
					feedback=record[12]
					complaintDate=date(int(record[13].split('-')[2]),int(record[13].split('-')[1]),int(record[13].split('-')[0]))
					workerId=record[14]
					worker = "Not Available"
					if workerId in workerData.keys():
						worker=workerData[workerId]
					dateCompleted=record[15]
					severity=record[16]
					if record[17]==1:
						inHouse="Yes"
					else:
						inHouse="No"

					if record[7] in [2,3,4]:
						status="Active"
					elif record[7]==0:
						status="Pending Approval"
					elif record[7] in [6,7,5,8]:
						status="Completed"
					elif record[7]==1:
						status="Discarded"
					else:
						continue
					if availabilityTime is not None:
						if availabilityTime=="Hostel Complaint":
							date1="ANY DAY"
							fromTime1="ANY TIME"
							toTime1="-"
							date2="ANY DAY"
							fromTime2="ANY TIME"
							toTime2="-"
							date3="ANY DAY"
							fromTime3="ANY TIME"
							toTime3="-"
						else:
							res=availabilityTime.split('###')
							res0=res[0].split('=')
							res1=res[1].split('=')
							res2=res[2].split('=')
							date1=res0[0]
							fromTime1=res0[1]
							toTime1=res0[2]
							date2=res1[0]
							fromTime2=res1[1]
							toTime2=res1[2]
							date3=res2[0]
							fromTime3=res2[1]
							toTime3=res2[2]
					if complaintTypeCheck!="all":
						if complaintTypeCheck!=complaintType:
							continue
					if statusCheck!="all":
						if statusCheck!=status:
							continue
					data = {'Complaint ID' : complaintId, 'Roll number/ User ID' : userId, 'Hostel' : hostelName, 'Room No' : hostelRoom, 'Complaint Type' : complaintType, 'Subject' : subject, 'Student Remarks' : remarksStudent, 'Date' : complaintDate, 'Time' : time, 'Status' : status, 'Availability Date 1' : date1, 'From Time 1' : fromTime1, 'To Time 1' : toTime1, 'Availability Date 2' : date2, 'From Time 2' : fromTime2, 'To Time 2' : toTime2, 'Availability Date 3' : date3, 'From Time 3' : fromTime3, 'To Time 3' : toTime3, 'Feedback' : feedback, 'Worker' : worker, 'Date Completed' : dateCompleted, 'Severity' : severity, 'In house' : inHouse}
					if complaintDate>=startDate and complaintDate<=endDate:
						writer.writerow(data)
			return send_file('static/complaintReports/'+filename, mimetype='text/csv', attachment_filename='complaintsReport.csv',as_attachment=True)	
	else:
		return redirect(url_for('hostel.home'))
		

@hostel.route('/user-profile', methods=['GET', 'POST'])
def userProfile():
	user=getCurrentHostelUser()
	cur = mysql.connection.cursor()
	if user:
		employee=query_db("select * from hostel_employee_mapping where employeeID=%s;",(user[0][0],))
		userDetails = []
		userRole = ""
		if(employee[0][1]==0):
			userDetails=(query_db("select firstName, lastName, mobile, hostelID, email, hostelEmail from warden_details where userID=%s;",(employee[0][2],)))
			userRole = "Warden"
		elif(employee[0][1]==1):
			userDetails=(query_db("select firstName, lastName, mobile, hostelID, email from caretaker_details where userID=%s;",(employee[0][2],)))
			userRole = "Caretaker"
		elif(employee[0][1]==2):
			userDetails=(query_db("select firstName, lastName, mobile, hostelID, email from night_caretaker_details where userID=%s;",(employee[0][2],)))
			userRole = "Night Caretaker"
		hostelID = userDetails[0][3]
		hostelData = query_db("select hostelName, caretakerID, nightCaretakerID, wardenID from hostel_data where hostelID=%s",(hostelID,))
		hostelPeeps = []
		wardenDeets = query_db("select firstName, lastName, mobile, email, hostelEmail from warden_details where userID=%s;",(hostelData[0][3],))
		ctDeets = query_db("select firstName, lastName, mobile, email from caretaker_details where userID=%s;",(hostelData[0][1],))
		ntctDeets = query_db("select firstName, lastName, mobile, email from night_caretaker_details where userID=%s;",(hostelData[0][2],))
		hostelPeeps.append(wardenDeets[0])
		hostelPeeps.append(ctDeets[0])
		hostelPeeps.append(ntctDeets[0])
		if request.method=='GET':
			return render_template('hostel/userProfile.html',employeeID = user[0][0],userRole = userRole, user=userDetails, hostelPeeps=hostelPeeps,hostelData=hostelData,passwordCheck=0,success=0)
		if request.method=='POST':
			if request.form['submit']=='Change Password':
				oldPassword = hashlib.md5(request.form['employee-old-password'].encode())
				newPassword = hashlib.md5(request.form['employee-new-password'].encode())
				result = query_db("select * from login_hostel where employeeID=%s;",(user[0][0],))
				if result[0][1]==oldPassword.hexdigest():
					cur.execute("update login_hostel set password=%s where employeeID=%s;", (newPassword.hexdigest(),user[0][0],))
					mysql.connection.commit()
					return render_template('hostel/userProfile.html',employeeID = user[0][0],userRole = userRole, user=userDetails, hostelPeeps=hostelPeeps,hostelData=hostelData, passwordCheck=0,success=1)
				else:
					return render_template('hostel/userProfile.html',employeeID = user[0][0],userRole = userRole, user=userDetails, hostelPeeps=hostelPeeps,hostelData=hostelData, passwordCheck=1,success=0)
			
	else:
		return redirect(url_for('hostel.home'))
	cur.close()


@hostel.route('/forgot-password', methods=['GET','POST'])
def forgotPassword():
	cur = mysql.connection.cursor()
	if request.method=='GET':
		return render_template('hostel/forgotPassword.html',detailsCheck=0,success=0)
	if request.method=='POST':
		employeeID = request.form['employee-id']
		emailX= request.form['employee-email']
		employeeResult = query_db("select * from login_hostel where employeeID=%s;", (employeeID,))
		if employeeResult is not None:
			emailResult = None
			employee=query_db("select * from hostel_employee_mapping where employeeID=%s;",(employeeID,))
			emailResult = []
			if(employee[0][1]==0):
				emailResult=query_db("select email from warden_details where userID=%s;",(employee[0][2],))
			elif(employee[0][1]==1):
				emailResult=query_db("select email from caretaker_details where userID=%s;",(employee[0][2],))
			elif(employee[0][1]==2):
				emailResult=query_db("select email from night_caretaker_details where userID=%s;",(employee[0][2],))
			if emailResult and emailResult[0][0]==emailX:
				password=None
				alphabet = string.ascii_letters + string.digits
				while True:
    					password = ''.join(secrets.choice(alphabet) for i in range(10))
    					if (any(c.islower() for c in password)
            							and any(c.isupper() for c in password)
            							and sum(c.isdigit() for c in password) >= 3):
        					break
				mailBody="Dear User\nHere is your updated password for the hostel webkiosk.\n{}\nKindly change it as soon as possible.".format(password)
				curDateTime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
				mailSubject="Hostel Webkiosk Password Reset Requested at "+str(curDateTime)
				if email(mailBody,mailSubject,emailX)=="OK":
					cur.execute("update login_hostel set password=%s where employeeID=%s;", (hashlib.md5(password.encode()).hexdigest(),employeeID,))
					mysql.connection.commit()
					return render_template('hostel/forgotPassword.html',detailsCheck=0,success=1)
				else:
					return render_template('hostel/forgotPassword.html',detailsCheck=0,success=0) 
			else:
				return render_template('hostel/forgotPassword.html',detailsCheck=1,success=0)
		else:
			return render_template('hostel/forgotPassword.html',detailsCheck=1,success=0)
	cur.close()
	

@hostel.route('/logout')
def logout():
	user = getCurrentHostelUser()
	if user:
		session.pop('employeeID', None )
		session.pop('whatIsMyRole', None )
		return redirect(url_for('hostel.home'))
	else:
		return redirect(url_for('hostel.home'))

