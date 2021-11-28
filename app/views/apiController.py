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
import json
from flask_httpauth import HTTPBasicAuth
import hashlib


apiController = Blueprint('apiController', __name__, url_prefix='/api') 
auth = HTTPBasicAuth()

users = {
    "capstone": "95c5022d6ccb62cf4634f653246c003a"
}

# Verify Authentication
@auth.verify_password
def verify_password(username, password):
	hashedPass = hashlib.md5(password.encode())
	if username=="capstone" and users[username]==hashedPass.hexdigest():
		return username

# Webhook for auto pull
@apiController.route("/autoPull", methods=['POST'])
def autoPull():
	os.system("sudo git pull")
	return "OK", 200

# Cron jobs
@apiController.route("/cron/dbSync", methods=['POST'])
def dbSync():
	os.system("python3 database\ updation/dbSyncAutomated.py")
	return "OK", 200


@apiController.route("/cron/refreshApprovals", methods=['POST'])
def refreshApprovals():
	cur=mysql.connection.cursor()
	temp=query_db('select complaintID,subject,userID,dateCompleted from cms where status in (5);')
	d=" "
	if temp is None:
		temp=[]
	for complaint in temp:
		complainID = complaint[0]
		complaintDesc = complaint[1]
		userID=complaint[2]
		dateOfComplaint = complaint[3]
		curDate = date.today()
		complaintDate = date.today()
		if dateOfComplaint== None:
			complaintDate=curDate
		else:
			dateOfComplaint=str(dateOfComplaint)
			complaintDate = date(int(dateOfComplaint.split('-')[2]),int(dateOfComplaint.split('-')[1]),int(dateOfComplaint.split('-')[0]))
		delta = curDate-complaintDate
		if(delta.days==2):
			body="Dear Student\n\nYour Complaint with Complaint ID = "+str(complainID)+" and Subject : '"+str(complaintDesc)+"' awaits a feedback. Incase you fail to provide a feedback by today, it shall be auto-approved by the system. Please check your dashboard at http://cmmstiet.in for further details.\nTHIS IS AN AUTOMATED MESSAGE- PLEASE DO NOT REPLY.\n\nThank You!"
			subject = "Complaint feedback required for complaintID:"+str(complainID)
			email(body,subject,userID)
		if(delta.days>3):
			d=delta.days
			cur.execute('update cms set status=7 where complaintID=%s;',(complainID,))
			mysql.connection.commit()
			body="Dear Student\n\nYour Complaint with Complaint ID = "+str(complainID)+" and Subject : '"+str(complaintDesc)+"' has been auto-approved. Please check your dashboard at http://cmmstiet.in for further details.\nTHIS IS AN AUTOMATED MESSAGE- PLEASE DO NOT REPLY.\n\nThank You!"
			subject = "Complaint Auto-approved (complaintID:"+str(complainID)+")"
			email(body,subject,userID)
	cur.close()
	return "OK", 200

@apiController.route("/cron/allot", methods=['POST'])
def allot():
	try:
		cur=mysql.connection.cursor()
		key=request.form["key"]
		if key=="Avada Kedavra":
			cur.execute("update cms set status=4 where status=3;")
			mysql.connection.commit() 
			return "OK", 200
		else:
			return "KEY INVALID", 200
	except Exception as e:
		return "Error"

@apiController.route("/cron/deleteComplaintResports", methods=['POST'])
def deleteComplaintReports():
	try:
		key=request.form["key"]
		if key=="Avada Kedavra":
			directory = "app/static/complaintReports"
			files_in_directory = os.listdir(directory)
			filtered_files = [file for file in files_in_directory if file.endswith(".csv")]
			for file in filtered_files:
				path_to_file = os.path.join(directory, file)
				os.remove(path_to_file)
			return "OK", 200
		else:
			return "KEY INVALID", 200
	except Exception as e:
		return "Error"

@apiController.route("/cron/mail", methods=['POST'])
def refreshMails():
	try:
		hostelList=query_db('select hostelID, caretakerID from hostel_data;')
		if hostelList is None:
			hostelList=[]
		for hostel in hostelList:
			hostelID = hostel[0]
			caretakerID = hostel[1]
			pendingApprovals = query_db("select * from cms where status=0 and deleted=0 and hostelID=%s",(hostelID,))
			count = 0
			if pendingApprovals is None:
				pendingApprovals=[]
			for i in pendingApprovals:
				count+=1
			if count>0:
				caretakerEmail = query_db("select email from caretaker_details where userID=%s",(caretakerID,))[0][0]
				curDateTime = datetime.now().strftime("%d-%m-%Y")
				subject = "Pending Complaint Approvals as of "+str(curDateTime)
				body = "Dear Hostel Caretaker,\n\nKindly approve the student complaints on CMMS website. Number of remaining complaints = "+str(count)+". \nPlease visit http://cmmstiet.in/hostel for the same.\nTHIS IS AN AUTOMATED MESSAGE- PLEASE DO NOT REPLY.\n\nThank you!"
				email(body,subject,caretakerEmail)
		return "OK", 200
	except Exception as e:
		return "Error"

@apiController.route("/cron/cmsMail", methods=['POST'])
def cmsMails():
	allData = query_db('select * from cms where deleted<>1 and inHouse=0 and status in (3,4) order by complaintID desc;')
	hostelData = query_db('select hostelID, hostelName from hostel_data;')
	roomData = query_db('select hostelRoomID, roomNumber from hostel_details;')
	workerData = query_db('select workerID, name from cms_workers_details;')
	completionData=query_db("select complaintID, updatedBy from complaint_updates where updates='Marked Completed: RESOLVED';")
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
	if completionData is None:
		completionData = {}
	else:
		completionData=dict(completionData)

	hostels={}
	
	curDateTime = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
	filename = "complaintsReport-"+str(curDateTime)+".csv"
	count=0
	with open('app/static/complaintReports/'+filename, 'w') as csvfile:
		fieldnames = ['S.No', 'Complaint ID', 'Date', 'Time', 'Pending Since (days)', 'Roll number/ User ID', 'Hostel', 'Room No', 'Complaint Type', 'Subject', 'Student Remarks', 'Status', 'Availability Date 1', 'From Time 1', 'To Time 1', 'Availability Date 2', 'From Time 2', 'To Time 2', 'Availability Date 3', 'From Time 3', 'To Time 3', 'Worker', 'Severity',]
		writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
		writer.writeheader()
		for record in allData:
			complaintId=record[0]
			userId=record[1]
			hostelName=hostelData[record[9]]
			hostels[record[9]]=1
			hostelRoom=roomData[record[2]]
			complaintType=record[3]
			subject=record[4]
			remarksStudent=record[5]
			time=record[6]
			status=record[7]
			availabilityTime=record[10]
			complaintDate=date(int(record[13].split('-')[2]),int(record[13].split('-')[1]),int(record[13].split('-')[0]))
			curDate=datetime.now().strftime("%d-%m-%Y")
			pendDays=(date(int(curDate.split('-')[2]),int(curDate.split('-')[1]),int(curDate.split('-')[0])) - date(int(record[13].split('-')[2]),int(record[13].split('-')[1]),int(record[13].split('-')[0]))).days
			workerId=record[14]
			worker = "Not Available"
			if workerId in workerData.keys():
				worker=workerData[workerId]
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
			count=count+1
			data = {'S.No' : count, 'Complaint ID' : complaintId, 'Date' : complaintDate, 'Time' : time, 'Pending Since (days)' : pendDays, 'Roll number/ User ID' : userId, 'Hostel' : hostelName, 'Room No' : hostelRoom, 'Complaint Type' : complaintType, 'Subject' : subject, 'Student Remarks' : remarksStudent, 'Status' : status, 'Availability Date 1' : date1, 'From Time 1' : fromTime1, 'To Time 1' : toTime1, 'Availability Date 2' : date2, 'From Time 2' : fromTime2, 'To Time 2' : toTime2, 'Availability Date 3' : date3, 'From Time 3' : fromTime3, 'To Time 3' : toTime3, 'Worker' : worker, 'Severity' : severity}
			writer.writerow(data)
		csvfile.close()
		data = pd.read_csv("app/static/complaintReports/"+filename)
		filename = "complaintsReport-"+str(curDateTime)+".xlsx"
		data.to_excel("app/static/complaintReports/"+filename, index=None, header=True)
		curDateTime = datetime.now().strftime("%d-%m-%Y")
		subject = "Pending Hostel Complaints till  "+str(curDateTime)
		body = "Dear Team CMS,\n\nPlease find attached the pending complaints till " +str(curDateTime)+". Number of remaining complaints = "+str(count)+". \n\nKindly resolve them ASAP.\nTHIS IS AN AUTOMATED MESSAGE- PLEASE DO NOT REPLY.\n\nThank you!"
		recipients=["chandan.kumar@thapar.edu","sanchit.pachauri@thapar.edu","azharuddin@thapar.edu","ajay@thapar.edu","arvind.gupta@thapar.edu","tarsem.kumar@thapar.edu"]
		cc=["skjain.cms@thapar.edu","harpreet.virdi@thapar.edu","ashish.purohit@thapar.edu"]
		bcc=[]
		warden_emails=query_db("Select hostelID, hostelEmail from warden_details;")
		ct_emails=query_db("Select hostelID, email from caretaker_details;")
		for email in ct_emails:
			if email is not None and email[1] is not None and email[0] in hostels:
				bcc.append(email[1])
		for email in warden_emails:
			if email is not None and email[1] is not None and email[0] in hostels:
				cc.append(email[1])
		emailAttach(body,subject,recipients,cc,bcc,"static/complaintReports/"+filename)
	return "OK", 200