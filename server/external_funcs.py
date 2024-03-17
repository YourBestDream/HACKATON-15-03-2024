from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
# Path to the service account credentials file
SERVICE_ACCOUNT_FILE = 'service_account.json'
# Scopes for Google Contacts API
SCOPES2 = ['https://www.googleapis.com/auth/contacts.readonly']

def get_contacts():
    try:
        # Authentication
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES2)

        # Creating the API client object
        service = build('people', 'v1', credentials=credentials)

        # Getting the list of contacts
        results = service.people().connections().list(
            resourceName='people/me',
            pageSize=100,  # number of contacts to fetch
            personFields='names,emailAddresses').execute()

        # Dictionary to store contacts
        contacts_dict = {}

        # Iterating over contacts and populating dictionary
        connections = results.get('connections', [])
        for person in connections:
            names = person.get('names', [])
            if names:
                name = names[0].get('displayName', 'Unknown')
            else:
                name = 'Unknown'
            email_addresses = person.get('emailAddresses', [])
            for email_obj in email_addresses:
                email = email_obj.get('value')
                contacts_dict[name] = email

        return contacts_dict

    except HttpError as error:
        print(f'An error occurred: {error}')
        return {}