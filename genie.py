from flask import Flask, request
import os
from dotenv import load_dotenv
import json
import re
import requests
import opsgenie_sdk
from pyral import Rally

load_dotenv('.env')

OPSGENIE_API_TOKEN = os.environ.get('OPSGENIE_API_TOKEN')
SERVER = os.environ.get('SERVER')
USER = os.environ.get('USER')
PASSWORD = os.environ.get('PASSWORD')
API_KEY = os.environ.get('API_KEY')
WORKSPACE = os.environ.get('WORKSPACE')
PROJECT = os.environ.get('PROJECT')
OWNER = os.environ.get('OWNER')
NAME = os.environ.get('NAME')

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    Type = data[0].get('Type')
    Application = data[0].get('Application')
    Description = data[0].get('Description')
    Priority = data[0].get('Priority')
    Submiter = data[0].get('Submiter')
    Team = data[0].get('Team')
    Train_Solution = data[0].get('Train_Solution')
    Message = Application +' '+ Team

    regex_email = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    if not re.fullmatch(regex_email, Submiter):
        return 'Verify submiter is a valid email', 400

    ops = 'Opsgenie reference : '
    rally = Rally(SERVER, USER, PASSWORD, apiKey=API_KEY, workspace=WORKSPACE, project=PROJECT)
    rally.enableLogging('rally.simple-use.log')

    info = {
        "Name": NAME,
        "Description": Description + ' ' + ops,
        "Owner": OWNER,
        "ScheduleState": "Defined",
    }

    body = opsgenie_sdk.CreateAlertPayload(
        message=Message,
        description=Description,
        responders=[{
            'name': 'DSSP-GoOps-Osprey',
            'type': 'team'
        }],
        tags=[Type],
        details={
            "Submiter": Submiter,
            "Team": Team,
            "Train/Solution": Train_Solution,
            "Priority": Priority,
            "Application": Application
        },
        priority=Priority
    )

    try:
        create_response = opsgenie_sdk.AlertApi().create_alert(create_alert_payload=body)
        print('OpsGenie alert created:', create_response)
    except opsgenie_sdk.ApiException as err:
        print("Exception when calling AlertApi->create_alert: %s\n" % err)
        return 'OpsGenie alert creation failed', 500

    try:
        defect = rally.create('UserStory', info)
        print('Rally user story created:', defect)
    except Exception as details:
        print('Rally user story creation failed:', details)
        return 'Rally user story creation failed', 500

    return 'Success', 200

if __name__ == '__main__':
    app.run(debug=True)
