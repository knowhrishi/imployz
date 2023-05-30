import firebase_admin
from firebase_admin import auth, credentials

cred = credentials.Certificate('/Users/knowhrishi/Documents/Code/Hackathons/HackBay23/resume_res/imployz-f8ee4-firebase-adminsdk-ei5aq-d9d56ea9fc.json')
firebase_admin.initialize_app(cred)
