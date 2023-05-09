from pyral import Rally
import opsgenie_sdk
import os

# Set up the Rally API connection
RALLY_API_KEY = 'RALLY_API_KEY'
RALLY_SERVER = 'https://rally1.rallydev.com'
RALLY_USER = 'YOU_RALLY_USERNAME'
RALLY_PASSWORD = 'YOUR_RALLY_PASSWORD'
RALLY_WORKSPACE = 'RALLY_WORKSPACE'
RALLY_PROJECT = 'RALLY_PROJECT'

# Set up the Opsgenie API connection
OPSGENIE_API_KEY = 'OPSGENIE_API_KEY'
opsgenie_sdk.configuration.api_key['GenieKey'] = OPSGENIE_API_KEY

# Function to recursively get all child projects
def get_child_projects(project):
    child_projects = []
    query = 'Parent = %s' % project.ref
    response = rally.get('Project', query=query, fetch='Name')
    for child_project in response:
        child_projects.append(child_project)
        child_projects.extend(get_child_projects(child_project))
    return child_projects

# Get all child projects for the given project
rally = Rally(RALLY_SERVER, apikey=RALLY_API_KEY, username=RALLY_USER, password=RALLY_PASSWORD, workspace=RALLY_WORKSPACE, project=RALLY_PROJECT)
project = rally.project
child_projects = get_child_projects(project)

# Search for new incidents or defects in all child projects
query = '(((State = "Open") OR (State = "Submitted")) AND (c_GoOps_AlertCreated = false))'
for child_project in [project] + child_projects:
    rally = Rally(RALLY_SERVER, apikey=RALLY_API_KEY, username=RALLY_USER, password=RALLY_PASSWORD, workspace=RALLY_WORKSPACE, project=child_project.ref)
    response = rally.get('Defect', query=query, order='Rank', fetch='FormattedID,Name,Description,Priority,Severity,SubmittedBy,Owner,State,CreationDate,c_GoOps_AlertCreated')
    if response.resultCount > 0:
        incident = response.next()
        incident_formatted_id = incident.FormattedID
        incident_name = incident.Name
        incident_description = incident.Description or ''
        incident_priority = incident.Priority or 'None'
        incident_severity = incident.Severity or 'None'
        incident_reporter = incident.SubmittedBy or ''
        incident_owner = incident.Owner or ''
        incident_state = incident.State or ''
        incident_creation_date = incident.CreationDate or ''
        
        # Create the alert in Opsgenie
        alert_api = opsgenie_sdk.AlertApi()
        create_alert_request = opsgenie_sdk.CreateAlertRequest(
            message=incident_name,
            description=incident_description,
            priority=incident_priority,
            tags=[incident_state, incident_severity],
            details={
                'formatted_id': incident_formatted_id,
                'reporter': incident_reporter,
                'owner': incident_owner,
                'creation_date': incident_creation_date
            },
            responders=[
                opsgenie_sdk.Responder(
                    name='team-name',
                    type='team'
                )
            ],
        )
        try:
            response = alert_api.create_alert(create_alert_request=create_alert_request)
            print('Opsgenie alert created: ' + response.request_id)
            
            # Update Rally to mark the incident/defect as processed
            rally.update('Defect', incident.oid, {'c_GoOps_AlertCreated': True})
            print('Rally defect updated')
        except opsgenie_sdk.ApiException as ex:
            print('Opsgenie create alert failed: ' + str(ex))
    else
