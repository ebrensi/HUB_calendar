
from __future__ import print_function
import httplib2
import os

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

import datetime
import csv


try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'

CALENDARS = ["Conference Room", "HUB Oakland Events"]


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def main():
    """Shows basic usage of the Google Calendar API.

    Creates a Google Calendar API service object and outputs a list of the next
    10 events on the user's calendar.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    print("Getting available calendars...")
    calendars_json = service.calendarList().list().execute()

    hub_cals = {cal["id"]: cal["summary"] for cal in calendars_json["items"]
                if cal["summary"] in CALENDARS}

    with open("IHO_cal.csv", "w") as outfile:
        items = {}
        fieldnames = ["Calendar", "Start", "End", "Title",
                      "Description", "Where", "Created by"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for id in hub_cals:
            page = 0
            print("\nRetrieving events from {}".format(hub_cals[id]))
            now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time

            page_token = None
            while True:
                eventsResult = service.events().list(calendarId=id,
                                                     timeMax=now,
                                                     maxResults=2500,
                                                     pageToken=page_token,
                                                     singleEvents=True,
                                                     orderBy='startTime').execute()

                events = eventsResult.get('items', [])
                page += 1
                print("{} results page {}:".format(hub_cals[id], page))
                for event in events:
                    item = {"Calendar": hub_cals[id],
                            "Title": event.get("summary"),
                            "Description": event.get("description"),
                            "Where": event.get("location"),
                            "Start": (event['start']
                                      .get('dateTime', event['start'].get('date'))),
                            "End": (event['end']
                                    .get('dateTime', event['end'].get('date'))),
                            "Created by": event["organizer"].get("displayName")
                            }
                    items[id] = item
                    writer.writerow(item)
                    print(item["Start"], event.setdefault('summary', ""))

                page_token = eventsResult.get('nextPageToken')

                if not page_token:
                    sync_token = eventsResult.get('nextSyncToken')
                    break

            print('sync token: {}\n'
                  .format(sync_token))


if __name__ == '__main__':
    main()
