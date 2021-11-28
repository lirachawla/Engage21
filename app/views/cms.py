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

cms = Blueprint('cms', __name__, url_prefix='/cms') 

@cms.route('/', methods=['GET','POST'])
def home():
	user = getCurrentCmsUser()
	cur = mysql.connection.cursor()
	try:
		if user:
			return redirect(url_for('cms.dashboard'))
		if request.method == 'POST':
			employeeID = request.form['cms-login-employeeID']
			password = hashlib.md5(request.form['cms-login-password'].encode())
			result=None
			result = query_db("select * from login_cms where employeeID=%s;",(employeeID,))
			if result:
				if result[0][1]==password.hexdigest():
					session['employeeID']=employeeID
					session['whatIsMyRole']="departmentOfComplaintManagementSystem"
					return redirect(url_for('cms.dashboard'))
				else:
					return render_template('cms/login.html',loginFlag=0)
			else:
				return render_template('cms/login.html',loginFlag=0)
		else:
			return render_template('cms/login.html',loginFlag=1)
	except Exception as e:
		mysql.connection.rollback()
		flash("Something went wrong!", 'danger')
		return redirect(url_for('cms.home'))
	finally:
		cur.close()

@cms.route('/user-profile', methods=['GET', 'POST'])
def userProfile():
	user=getCurrentCmsUser()
	cur = mysql.connection.cursor()
	if user:
		userDetails=query_db("select * from cms_employee_details where employeeID=%s;",(user[0][0],))
			
		if request.method=='GET':
			return render_template('cms/userProfile.html',employeeID = user[0][0],user=userDetails,passwordCheck=0,success=0)
		if request.method=='POST':
			if request.form['submit']=='Change Password':
				oldPassword = hashlib.md5(request.form['employee-old-password'].encode())
				newPassword = hashlib.md5(request.form['employee-new-password'].encode())
				result = query_db("select * from login_cms where employeeID=%s;",(user[0][0],))
				if result[0][1]==oldPassword.hexdigest():
					cur.execute("update login_cms set password=%s where employeeID=%s;", (newPassword.hexdigest(),user[0][0],))
					mysql.connection.commit()
					return render_template('cms/userProfile.html',employeeID = user[0][0],user=userDetails,passwordCheck=0,success=1)
				else:
					return render_template('cms/userProfile.html',employeeID = user[0][0],user=userDetails,passwordCheck=1,success=0)
			
	else:
		return redirect(url_for('cms.home'))
	cur.close()

@cms.route('/dashboard', methods=['GET','POST'])
def dashboard():
	user=getCurrentCmsUser()
	cur=mysql.connection.cursor()
	if user:
		if request.method == 'GET':
			employee_details=query_db("select * from cms_employee_details where employeeID=%s;",(user[0][0],))
			showPendingComplaints = query_db("select * from cms where deleted<>1 and status=3 and inHouse=0;")
			showActiveComplaints = query_db("select * from cms where deleted<>1 and status in (4) and inHouse=0;")
			showCompletedComplaints = query_db("select * from cms where deleted<>1 and status in (5,6,7,8,9) and inHouse=0 order by complaintID desc limit 50;")
			workers = query_db("select * from cms_workers_details;")
			if workers is None:
				workers=[]
			completedComplaints=[]	
			activeComplaints=[]	
			pendingComplaints=[]
			if showPendingComplaints is None:
				showPendingComplaints=[]
			for i in range(len(showPendingComplaints)):
				complaintID=showPendingComplaints[i][0]
				hostelRoomID=showPendingComplaints[i][2]
				roomNumber="Hostel Complaint"
				if hostelRoomID!=1:
					roomNumber=query_db("select roomNumber from hostel_details where hostelRoomID=%s;",(hostelRoomID,))[0][0]
				userDetails = ["name", "userID/rollnumber"]
				if showPendingComplaints[i][8]==2:
					employeeID=showPendingComplaints[i][1]
					employeeMap=query_db("select role,userID from hostel_employee_mapping where employeeID=%s;",(employeeID,))
					role = employeeMap[0][0]
					userID = employeeMap[0][1]
					userDetails[1]=employeeID
					if role == 0:
						wardenDetails=query_db("select firstName, lastName from warden_details where userID=%s;",(userID,))
						userDetails[0]=wardenDetails[0][0]+" "+wardenDetails[0][1]
					elif role == 1:
						caretakerDetails=query_db("select firstName, lastName from caretaker_details where userID=%s;",(userID,))
						userDetails[0]=caretakerDetails[0][0]+" "+caretakerDetails[0][1]
					elif role == 2:
						nCaretakerDetails=query_db("select firstName, lastName from night_caretaker_details where userID=%s;",(userID,))
						userDetails[0]=nCaretakerDetails[0][0]+" "+nCaretakerDetails[0][1]
				elif showPendingComplaints[i][8]==0:
					userID = showPendingComplaints[i][1]
					studentDeets = query_db("select rollNumber,firstName,lastName from student_details where userID=%s;",(userID,))
					userDetails[1]=studentDeets[0][0]
					userDetails[0]=studentDeets[0][1]+" "+studentDeets[0][2]
				hostelID=showPendingComplaints[i][9]
				hostelName=query_db("select hostelName from hostel_data where hostelID=%s;",(hostelID,))[0][0]
				type=showPendingComplaints[i][3]
				subject=showPendingComplaints[i][4]
				description=showPendingComplaints[i][5]
				time = showPendingComplaints[i][6]
				date = showPendingComplaints[i][13]
				status = showPendingComplaints[i][7]
				image = showPendingComplaints[i][11]
				severity = showPendingComplaints[i][16]
				if image is None:
					image = "1"
				workerID = showPendingComplaints[i][14]
				workerDeets=[]
				if workerID!=0:
					workerDeets = query_db("select name,phone from cms_workers_details where workerID=%s;",(workerID,))
				else:
					workerID="Not Alloted"
					workerDeets=[["Not Alloted","Not Alloted"]]
				workerName = workerDeets[0][0]
				workerNumber = workerDeets[0][1]
				complaint=[complaintID,userDetails[0],userDetails[1],roomNumber,hostelName,type,subject,description,time,date,status,workerName,workerNumber,image,severity]
				pendingComplaints.append(complaint)

			
			if showActiveComplaints is None:
				showActiveComplaints =[]
			for i in range(len(showActiveComplaints)):
				complaintID=showActiveComplaints[i][0]
				hostelRoomID=showActiveComplaints[i][2]
				roomNumber="Hostel Complaint"
				if hostelRoomID!=1:
					roomNumber=query_db("select roomNumber from hostel_details where hostelRoomID=%s;",(hostelRoomID,))[0][0]
				userDetails = ["name", "userID/rollnumber"]
				if showActiveComplaints[i][8]==2:
					employeeID=showActiveComplaints[i][1]
					employeeMap=query_db("select role,userID from hostel_employee_mapping where employeeID=%s;",(employeeID,))
					role = employeeMap[0][0]
					userID = employeeMap[0][1]
					userDetails[1]=employeeID
					if role == 0:
						wardenDetails=query_db("select firstName, lastName from warden_details where userID=%s;",(userID,))
						userDetails[0]=wardenDetails[0][0]+" "+wardenDetails[0][1]
					elif role == 1:
						caretakerDetails=query_db("select firstName, lastName from caretaker_details where userID=%s;",(userID,))
						userDetails[0]=caretakerDetails[0][0]+" "+caretakerDetails[0][1]
					elif role == 2:
						nCaretakerDetails=query_db("select firstName, lastName from night_caretaker_details where userID=%s;",(userID,))
						userDetails[0]=nCaretakerDetails[0][0]+" "+nCaretakerDetails[0][1]
				elif showActiveComplaints[i][8]==0:
					userID = showActiveComplaints[i][1]
					studentDeets = query_db("select rollNumber,firstName,lastName from student_details where userID=%s;",(userID,))
					userDetails[1]=studentDeets[0][0]
					userDetails[0]=studentDeets[0][1]+" "+studentDeets[0][2]
				hostelID=showActiveComplaints[i][9]
				hostelName=query_db("select hostelName from hostel_data where hostelID=%s;",(hostelID,))[0][0]
				type=showActiveComplaints[i][3]
				subject=showActiveComplaints[i][4]
				description=showActiveComplaints[i][5]
				time = showActiveComplaints[i][6]
				date = showActiveComplaints[i][13]
				status = showActiveComplaints[i][7]
				image = showActiveComplaints[i][11]
				severity = showActiveComplaints[i][16]
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
				complaint=[complaintID,userDetails[0],userDetails[1],roomNumber,hostelName,type,subject,description,time,date,status,workerName,workerNumber,image,severity]
				activeComplaints.append(complaint)
			
			if showCompletedComplaints is None:
				showCompletedComplaints =[]
			for i in range(len(showCompletedComplaints)):
				complaintID=showCompletedComplaints[i][0]
				hostelRoomID=showCompletedComplaints[i][2]
				roomNumber="Hostel Complaint"
				if hostelRoomID!=1:
					roomNumber=query_db("select roomNumber from hostel_details where hostelRoomID=%s;",(hostelRoomID,))[0][0]
				userDetails = ["name", "userID/rollnumber"]
				if showCompletedComplaints[i][8]==2:
					employeeID=showCompletedComplaints[i][1]
					employeeMap=query_db("select role,userID from hostel_employee_mapping where employeeID=%s;",(employeeID,))
					role = employeeMap[0][0]
					userID = employeeMap[0][1]
					userDetails[1]=employeeID
					if role == 0:
						wardenDetails=query_db("select firstName, lastName from warden_details where userID=%s;",(userID,))
						userDetails[0]=wardenDetails[0][0]+" "+wardenDetails[0][1]
					elif role == 1:
						caretakerDetails=query_db("select firstName, lastName from caretaker_details where userID=%s;",(userID,))
						userDetails[0]=caretakerDetails[0][0]+" "+caretakerDetails[0][1]
					elif role == 2:
						nCaretakerDetails=query_db("select firstName, lastName from night_caretaker_details where userID=%s;",(userID,))
						userDetails[0]=nCaretakerDetails[0][0]+" "+nCaretakerDetails[0][1]
				elif showCompletedComplaints[i][8]==0:
					userID = showCompletedComplaints[i][1]
					studentDeets = query_db("select rollNumber,firstName,lastName from student_details where userID=%s;",(userID,))
					userDetails[0]=studentDeets[0][1]+" "+studentDeets[0][2]
					userDetails[1]=studentDeets[0][0]
				hostelID=showCompletedComplaints[i][9]
				hostelName=query_db("select hostelName from hostel_data where hostelID=%s;",(hostelID,))[0][0]
				type=showCompletedComplaints[i][3]
				subject=showCompletedComplaints[i][4]
				description=showCompletedComplaints[i][5]
				time = showCompletedComplaints[i][6]
				date = showCompletedComplaints[i][13]
				status = showCompletedComplaints[i][7]
				image = showCompletedComplaints[i][11]
				feedback=showCompletedComplaints[i][12]
				dateCompleted = showCompletedComplaints[i][15]
				severity = showCompletedComplaints[i][16]
				if image is None:
					image = "1"
				workerID = showCompletedComplaints[i][14]
				workerDeets=[]
				if workerID!=0:
					workerDeets = query_db("select name,phone from cms_workers_details where workerID=%s;",(workerID,))
				else:
					workerID="Not Alloted"
					workerDeets=[["Not Alloted","Not Alloted"]]
				workerName = workerDeets[0][0]
				workerNumber = workerDeets[0][1]
				complaint=[complaintID,userDetails[0],userDetails[1],roomNumber,hostelName,type,subject,description,time,date,status,workerName,workerNumber,image,feedback,dateCompleted,severity]
				completedComplaints.append(complaint)
			return render_template('cms/dashboard.html',user=employee_details,activeComplaints=activeComplaints, pendingComplaints=pendingComplaints, completedComplaints=completedComplaints, workers=workers)	
		if request.method=="POST":
			employee_details=query_db("select * from cms_employee_details where employeeID=%s;",(user[0][0],))
			submittedReq = request.form["submit"]
			if submittedReq.split(':')[0]=="discard":
				complaintID = submittedReq.split(':')[1]
				reason = request.form['discardReason']
				curDateTime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
				cur.execute('insert into cms_discarded_complaints (complaintID,discardedBy,reason,timestamp) values (%s,%s,%s,%s);',(complaintID,employee_details[0][1],curDateTime,reason,))
				cur.execute("update cms set status=9 where complaintID=%s;",(complaintID,))
				mysql.connection.commit()
			elif submittedReq.split(':')[0]=="worker":
				complaintID = submittedReq.split(':')[1]
				workerID = request.form['workerID']
				cur.execute("update cms set status=4 where complaintID=%s;",(complaintID,))
				cur.execute("update cms set workerID=%s where complaintID=%s;",(workerID,complaintID,))
				mysql.connection.commit()
			return redirect(url_for('cms.dashboard'))	
	else:
		return redirect(url_for('cms.home'))

@cms.route('/workers', methods=['GET','POST'])
def workers():
	user = getCurrentCmsUser()
	cur = mysql.connection.cursor()
	try:
		if user:
			employee_details=query_db("select * from cms_employee_details where employeeID=%s;",(user[0][0],))
			#if request.method == 'GET':
			return render_template('cms/workerInfo.html', user=employee_details)	
		else:
			return redirect(url_for('cms.home'))
	except Exception as e:
		mysql.connection.rollback()
		flash("Something went wrong!", 'danger')
		return redirect(url_for('cms.home'))
	finally:
		cur.close()
		
@cms.route('/generate-report', methods=["POST","GET"])
def generateReport():
	user=getCurrentCmsUser()
	if user:
		employeeDetails=query_db("select * from cms_employee_details where employeeID=%s;",(user[0][0],))
		if request.method=="GET":
			hostelData = query_db('select hostelID, hostelName from hostel_data;')
			complaintTypes = query_db("select * from complaint_types;")
			return render_template('cms/generateReport.html', user=employeeDetails, hostelList=hostelData, complaintTypes=complaintTypes)
		elif request.method=="POST":
			startDate=date(int(request.form['startDate'].split('-')[2]),int(request.form['startDate'].split('-')[1]),int(request.form['startDate'].split('-')[0]))
			endDate=date(int(request.form['endDate'].split('-')[2]),int(request.form['endDate'].split('-')[1]),int(request.form['endDate'].split('-')[0]))
			complaintTypeCheck = request.form['type-of-complaint']
			statusCheck = request.form['status']
			hostelCheck = request.form['select-hostel']
			allData = query_db('select * from cms where deleted<>1 and inHouse=0;')
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
				fieldnames = ['Complaint ID', 'Roll number/ User ID', 'Hostel', 'Room No', 'Complaint Type', 'Subject', 'Student Remarks', 'Date', 'Time', 'Status', 'Availability Date 1', 'From Time 1', 'To Time 1', 'Availability Date 2', 'From Time 2', 'To Time 2', 'Availability Date 3', 'From Time 3', 'To Time 3', 'Feedback', 'Worker', 'Date Completed', 'Severity',]
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
					
					if record[7]==4:
						status="Active"
					elif record[7]==3:
						status="Pending allotment to worker"
					elif record[7] in [5,6,7,8]:
						status="Completed"
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
					if hostelCheck!="all":
						if hostelCheck!=hostelName:
							continue
					data = {'Complaint ID' : complaintId, 'Roll number/ User ID' : userId, 'Hostel' : hostelName, 'Room No' : hostelRoom, 'Complaint Type' : complaintType, 'Subject' : subject, 'Student Remarks' : remarksStudent, 'Date' : complaintDate, 'Time' : time, 'Status' : status, 'Availability Date 1' : date1, 'From Time 1' : fromTime1, 'To Time 1' : toTime1, 'Availability Date 2' : date2, 'From Time 2' : fromTime2, 'To Time 2' : toTime2, 'Availability Date 3' : date3, 'From Time 3' : fromTime3, 'To Time 3' : toTime3, 'Feedback' : feedback, 'Worker' : worker, 'Date Completed' : dateCompleted, 'Severity' : severity}
					if complaintDate>=startDate and complaintDate<=endDate:
						writer.writerow(data)
			return send_file('static/complaintReports/'+filename, mimetype='text/csv', attachment_filename='complaintsReport.csv',as_attachment=True)	
	else:
		return redirect(url_for('cms.home'))

@cms.route('/logout')
def logout():
	user = getCurrentCmsUser()
	if user:
		session.pop('employeeID', None )
		return redirect(url_for('cms.home'))
	else:
		return redirect(url_for('cms.home'))
