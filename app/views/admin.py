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
from datetime import date
import subprocess
import string
import secrets

admin = Blueprint('admin', __name__, url_prefix='/admin') 

@admin.route('/', methods=['GET','POST'])
def home():
	user = getCurrentAdminUser()
	cur = mysql.connection.cursor()
	try:
		if user:
			return redirect(url_for('admin.dashboard'))
		if request.method == 'POST':
			employeeID = request.form['admin-login-employeeID']
			password = hashlib.md5(request.form['admin-login-password'].encode())
			result=None
			result = query_db("select * from login_admin where employeeID=%s;",(employeeID,))
			if result:
				if result[0][1]==password.hexdigest():
					session['employeeID']=employeeID
					session['whatIsMyRole']="departmentOfAdmin"
					return redirect(url_for('admin.dashboard'))
				else:
					return render_template('admin/login.html',loginFlag=0)
			else:
				return render_template('admin/login.html',loginFlag=0)
		else:
			return render_template('admin/login.html',loginFlag=1)
	except Exception as e:
		mysql.connection.rollback()
		flash("Something went wrong!", 'danger')
		return redirect(url_for('admin.home'))
	finally:
		cur.close()

@admin.route('/dashboard', methods=['GET'])
def dashboard():
	user=getCurrentAdminUser()
	if user:
		return redirect(url_for('admin.userProfile'))
		return render_template('admin/dashboard.html',user=user)
	else:
		return redirect(url_for('admin.home'))
		
@admin.route('/hostel-data', methods=["POST","GET"])
def hostelData():
	user=getCurrentAdminUser()
	if user:
		employeeDetails=query_db("select * from admin_details where employeeID=%s;",(user[0][0],))
		wardenDetails=query_db('select * from warden_details;')
		caretakerDetails=query_db('select * from caretaker_details;')
		nightCaretakerDetails=query_db('select * from night_caretaker_details;')
		
		wardenData=[]
		for i in range(len(wardenDetails)):
			hostelID=wardenDetails[i][6]
			hostel=(query_db("select hostelName from hostel_data where hostelID=%s;",(hostelID,)))[0][0]
			if hostel == 'TEST':
				continue
			name=wardenDetails[i][1]+" "+wardenDetails[i][2] 
			gender=wardenDetails[i][3]
			contact=wardenDetails[i][4]
			email=wardenDetails[i][8]
			personalEmail=wardenDetails[i][7]
			warden=[hostel,name,gender,contact,email,personalEmail]
			wardenData.append(warden)
			
		caretakerData=[]
		for i in range(len(caretakerDetails)):
			hostelID=caretakerDetails[i][6]
			hostel=(query_db("select hostelName from hostel_data where hostelID=%s;",(hostelID,)))[0][0]
			if hostel == 'TEST':
				continue
			name=caretakerDetails[i][1]
			gender=caretakerDetails[i][3]
			contact=caretakerDetails[i][4]
			email=caretakerDetails[i][7]
			caretaker=[hostel,name,gender,contact,email]
			caretakerData.append(caretaker)
			
		nightCaretakerData=[]
		for i in range(len(nightCaretakerDetails)):
			hostelID=nightCaretakerDetails[i][6]
			hostel=(query_db("select hostelName from hostel_data where hostelID=%s;",(hostelID,)))[0][0]
			if hostel == 'TEST':
				continue
			name=nightCaretakerDetails[i][1]
			gender=nightCaretakerDetails[i][3]
			contact=nightCaretakerDetails[i][4]
			email=nightCaretakerDetails[i][7]
			nightCaretaker=[hostel,name,gender,contact,email]
			nightCaretakerData.append(nightCaretaker)
		
		
		return render_template('admin/hostel-data.html',user=employeeDetails,wardenData=wardenData,caretakerData=caretakerData,nightCaretakerData=nightCaretakerData)
	else:
		return redirect(url_for('admin.home'))
		
@admin.route('/generate-report', methods=["POST","GET"])
def generateReport():
	user=getCurrentAdminUser()
	if user:
		employeeDetails=query_db("select * from admin_details where employeeID=%s;",(user[0][0],))
		if request.method=="GET":
			hostelData = query_db('select hostelID, hostelName from hostel_data;')
			complaintTypes = query_db("select * from complaint_types;")
			return render_template('admin/generateReport.html',user=employeeDetails, hostelList=hostelData, complaintTypes=complaintTypes)
		elif request.method=="POST":
			startDate=date(int(request.form['startDate'].split('-')[2]),int(request.form['startDate'].split('-')[1]),int(request.form['startDate'].split('-')[0]))
			endDate=date(int(request.form['endDate'].split('-')[2]),int(request.form['endDate'].split('-')[1]),int(request.form['endDate'].split('-')[0]))
			complaintTypeCheck = request.form['type-of-complaint']
			statusCheck = request.form['status']
			allData = query_db('select * from cms where deleted<>1;')
			hostelData = query_db('select hostelID, hostelName from hostel_data;')
			roomData = query_db('select hostelRoomID, roomNumber from hostel_details;')
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
			if hostelData is None:
				hostelData = {}
			else:
				hostelData = dict(hostelData)
			curDateTime = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
			filename = 'complaintsReport-'+str(user[0][0])+"-"+str(curDateTime)+".csv"
			with open('app/static/complaintReports/'+filename, 'w') as csvfile:
				fieldnames = ['Complaint ID', 'Roll number/ User ID', 'Hostel', 'Room No', 'Complaint Type', 'Subject', 'Student Remarks', 'Date', 'Time', 'Status', 'Availability Date 1', 'From Time 1', 'To Time 1', 'Availability Date 2', 'From Time 2', 'To Time 2', 'Availability Date 3', 'From Time 3', 'To Time 3', 'Feedback', 'Worker', 'Date Completed', 'Severity','In house',]
				writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
				writer.writeheader()
				for record in allData:
					complaintId=record[0]
					userId=record[1]
					hostelName=hostelData[record[9]]
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
		return redirect(url_for('admin.home'))

@admin.route('/complaints-data', methods=['GET', 'POST'])
def complaintsData():
	user=getCurrentAdminUser()
	cur = mysql.connection.cursor()
	if user:
		userDetails=(query_db("select firstName, lastName from admin_details where employeeID=%s;",(user[0][0],)))
		pending = (query_db("select hostelID, count(*) from cms where deleted<>1 and status in (0) group by hostelID;"))
		active = (query_db("select hostelID, count(*) from cms where deleted<>1 and status in (2,3,4) group by hostelID;"))
		completed = (query_db("select hostelID, count(*) from cms where deleted<>1 and status in (1,5,6,7,8) group by hostelID;"))
		hostels = list(query_db("select hostelID, hostelName from hostel_data;"))

		pendingApprovals = {}
		activeComplaints = {}
		completedComplaints = {}
		if pending is not None:
			pendingApprovals = dict(pending)
		if active is not None:
			activeComplaints = dict(active)
		if completed is not None:
			completedComplaints = dict(completed)
				
		complaints=[]

		for hostel in hostels:
				complaint=[]
				if hostel[1]=="TEST":
					continue
				complaint.append(hostel[1])
				if hostel[0] in pendingApprovals:
					complaint.append(pendingApprovals[hostel[0]])
				else:
					complaint.append(0)

				if hostel[0] in activeComplaints:
					complaint.append(activeComplaints[hostel[0]])
				else:
					complaint.append(0)

				if hostel[0] in completedComplaints:
					complaint.append(completedComplaints[hostel[0]])
				else:
					complaint.append(0)

				complaints.append(complaint)

		return render_template('admin/complaintsData.html',user=userDetails,complaints=complaints)
	else:
		return redirect(url_for('admin.home'))
			
		
@admin.route('/user-profile', methods=['GET', 'POST'])
def userProfile():
	user=getCurrentAdminUser()
	cur = mysql.connection.cursor()
	if user:
		userDetails=(query_db("select firstName, lastName from admin_details where employeeID=%s;",(user[0][0],)))
			
		if request.method=='GET':
			return render_template('admin/userProfile.html',employeeID = user[0][0],user=userDetails,passwordCheck=0,success=0)
		if request.method=='POST':
			if request.form['submit']=='Change Password':
				oldPassword = hashlib.md5(request.form['employee-old-password'].encode())
				newPassword = hashlib.md5(request.form['employee-new-password'].encode())
				result = query_db("select * from login_admin where employeeID=%s;",(user[0][0],))
				if result[0][1]==oldPassword.hexdigest():
					cur.execute("update login_admin set password=%s where employeeID=%s;", (newPassword.hexdigest(),user[0][0],))
					mysql.connection.commit()
					return render_template('admin/userProfile.html',employeeID = user[0][0],user=userDetails,passwordCheck=0,success=1)
				else:
					return render_template('admin/userProfile.html',employeeID = user[0][0],user=userDetails,passwordCheck=1,success=0)
			
	else:
		return redirect(url_for('admin.home'))
	cur.close()
		
@admin.route('/forgot-password', methods=['GET','POST'])
def forgotPassword():
	cur = mysql.connection.cursor()
	if request.method=='GET':
		return render_template('admin/forgotPassword.html',detailsCheck=0,success=0)
	if request.method=='POST':
		employeeID = request.form['employee-id']
		emailX= request.form['employee-email']
		employeeResult = query_db("select * from login_admin where employeeID=%s;", (employeeID,))
		if employeeResult is not None:
			emailResult = query_db("select email from admin_details where employeeID=%s;",(employeeID,))
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
					cur.execute("update login_admin set password=%s where employeeID=%s;", (hashlib.md5(password.encode()).hexdigest(),employeeID,))
					mysql.connection.commit()
					return render_template('admin/forgotPassword.html',detailsCheck=0,success=1)
				else:
					return render_template('admin/forgotPassword.html',detailsCheck=0,success=0) 
			else:
				return render_template('admin/forgotPassword.html',detailsCheck=1,success=0)
		else:
			return render_template('admin/forgotPassword.html',detailsCheck=1,success=0)
	cur.close()


@admin.route('/logout')
def logout():
    user = getCurrentAdminUser()
    if user:
        session.pop('employeeID', None)
        return redirect(url_for('admin.home'))
    else:
        return redirect(url_for('admin.home'))

