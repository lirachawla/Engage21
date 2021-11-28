from datetime import datetime
from flask import session
from app import *
from flask_mysqldb import MySQL

# Gets current student user
def getCurrentStudent():
	userResult = None
	if 'rollNumber' in session:
		rollNumber = session['rollNumber']
		for key in list(session.keys()):
			if key != "rollNumber":
				session.pop(key)
		userResult = query_db("select userID, rollNumber from login_student where rollNumber=%s;",(rollNumber,))
	return userResult

def getCurrentHostelUser():
	userResult = None
	if 'employeeID' in session:
		employeeID = session['employeeID']
		role=session['whatIsMyRole']
		for key in list(session.keys()):
			if key == "employeeID" or key == "whatIsMyRole":
				continue
			session.pop(key)
		cur = mysql.connection.cursor()
		userResult = query_db("select employeeID from login_hostel where employeeID=%s;",(employeeID,))
		if role!= "departmentOfHostelManagement":
			temp=None
			return temp
	return userResult

def getCurrentAdminUser():
	userResult = None
	if 'employeeID' in session:
		employeeID = session['employeeID']
		role=session['whatIsMyRole']
		for key in list(session.keys()):
			if key == "employeeID" or key == "whatIsMyRole":
				continue
			session.pop(key)
		cur = mysql.connection.cursor()
		userResult = query_db("select employeeID from login_admin where employeeID=%s;",(employeeID,))
		if role!= "departmentOfAdmin":
			temp=None
			return temp
	return userResult

def getCurrentCmsUser():
	userResult = None
	if 'employeeID' in session:
		employeeID = session['employeeID']
		role=session['whatIsMyRole']
		for key in list(session.keys()):
			if key == "employeeID" or key == "whatIsMyRole":
				continue
			session.pop(key)
		cur = mysql.connection.cursor()
		userResult = query_db("select employeeID from login_cms where employeeID=%s;",(employeeID,))
		if role!= "departmentOfComplaintManagementSystem":
			temp=None
			return temp
	return userResult

#email
def email(msgBody,subject,receiversEmail,senderEmail='cmstiet@gmail.com' ):
	msg = Message(subject, sender = senderEmail, recipients = [receiversEmail])
	msg.body = msgBody
	mail.send(msg)
	return "OK"

def emailAttach(msgBody,subject,recipients,cc,bcc,attachment,senderEmail='cmstiet@gmail.com' ):
	msg = Message(subject, body = msgBody, sender = senderEmail, recipients = recipients, cc = cc, bcc = bcc)
	with app.open_resource(attachment) as fp:
		msg.attach("CMSReport.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", fp.read())
		mail.send(msg)
	return "OK"
