import os
import shutil
import codecs
import time
import io
import json
from datetime import datetime, timedelta

from .external_funcs import get_contacts

from PIL import Image
import requests as rs
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from langchain.document_loaders.generic import GenericLoader
from langchain.document_loaders.parsers.audio import OpenAIWhisperParserLocal
from dotenv import load_dotenv
from g4f.client import Client
import g4f

load_dotenv()

requests = Blueprint('requests',__name__)
whisper_parser = OpenAIWhisperParserLocal(device = "gpu", lang_model='openai/whisper-small', forced_decoder_ids=({"language":"romanian", "task":"transcribe"}))

@requests.route('/transform', methods = ['POST'])
def transform():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    try:
        package_dir = os.path.dirname(os.path.abspath(__file__))
        sub_dir = "Audio"
        save_dir = os.path.join(package_dir, sub_dir)

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(save_dir, filename)
        file.save(filepath)
        print(filepath)
        # Setup GenericLoader with the correct parser for audio files
        audio_loader = GenericLoader.from_filesystem(
            path=filepath,
            parser=whisper_parser
        )
        
        # Load and process the audio file
        start = time.time()
        result = next(audio_loader.lazy_load())
        end = time.time()
        print(end-start)
        print(result.page_content)
        
        #rs.post("http://192.168.8.173/api/v1/authentication/parseTranscription", json={'transcription':result.page_content})

        return jsonify({
            'message': 'File uploaded and processed successfully',
            'transcription': result.page_content
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

    finally:
        shutil.rmtree(save_dir)

@requests.route('/structurize',methods=['POST'])
def structurize_request():
    transcription = request.get_json().get('transcription')

    client = Client()
    start = time.time()
    response = client.chat.completions.create(
    model=g4f.models.gpt_35_turbo_16k,
    messages=[{"role": "user", "content": f'''
    I need you to THORORUGHLY analyze the transcription I will give you. You should ONLY analyze, you SHOULD NOT try to answer the request. Your reponse should be in json formatwith 2 elements: "category" and "additional_data". Category element can contain only these categories: news, weather, person-search or meeting. 
    For example if you will receive the following transcription: "I want to know what happened with Steve Harvey this week" you SHOULD give the following answer in JSON format: 
    "category": "News",
    "additional_data" : "What happened with Steve Harvey last week"
    If you cannot classify the transcription just leave the category blank and in additional_data write your answer to the user like if you were talking to the normal user without remindings about clasification.
    If you categorize the transcription as "person-search" you should leave in "additional_data" ONLY names.
    If you categorize the transcription as "weather" you should leave in "additional_data" ONLY the name of the city.
    If you categorize the transcription as "meeting" you should leave in "additional_data" ONLY the time of the beggining in format "2024-03-31T10:00:00"
    You SHOULD always answer IN the LANGUAGE OF TRANSCRIPTION
    TRANSCRIPTION:
    {transcription}
    ANSWER ONLY IN JSON FORMAT:
    '''}],
    )

    response = response.choices[0].message.content
    end = time.time()
    print(end-start)
    response = json.loads(response)
    return jsonify(response)

@requests.route('/weather', methods = ['POST'])
def get_weather():
    city_name = request.get_json().get('query')
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={os.environ.get('WEATHER_API_KEY')}&units=metric"
    response = rs.get(url)
    data = response.json()

    if data["cod"] == 200:
        weather_description = data["weather"][0]["description"]
        temperature = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]

        return jsonify({'city_name':city_name,'description':weather_description,'temperature':temperature, 'humidity':humidity,'wind_speed':wind_speed})
    else:
        return jsonify({'message':f"Failed to fetch weather data. Error: {data['message']}"})

@requests.route('/news', methods=['GET','POST'])
def news():
    query = request.get_json().get('query')
    client = Client()
    response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[{"role": "user", "content": f'''
    {query}
    '''}],
    ).choices[0].message.content
    print(response)

    return jsonify({'response':response})

@requests.route('/person-search', methods=['POST'])
def find_a_person():
    if 'photo' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['photo']
    
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    upload_url = "https://search4faces.com/upload.php"
    if not file.content_type == 'image/jpeg':
        try:
            # Convert the image to JPEG
            image = Image.open(file.stream)
            with io.BytesIO() as output:
                image.convert('RGB').save(output, format='JPEG')
                image_data = output.getvalue()
        except IOError:
            return jsonify({'error': 'File conversion error'}), 500
    else:
        image_data = file.read()

    headers = {
        "Referer": "https://search4faces.com/en/vkok/index.html",
        "Content-Type": "image/jpeg"  # Set the content type to JPEG
    }

    upload_response = rs.post(upload_url, data=image_data, headers=headers)
    if upload_response.status_code != 200:
        return jsonify({'error': 'Failed to upload image'}), 500

    # Process response from the upload
    response_json = upload_response.json()
    detect_url = "https://search4faces.com/detect.php"
    detect_response = rs.post(detect_url, json={"query": "vkok", "lang": "en", "filename": response_json["url"], "boundings": response_json["boundings"][0]})
    
    if detect_response.status_code != 200:
        return jsonify({'error': 'Failed to detect faces'}), 500

    detect_json = detect_response.json()
    selected_links = [detect_json["faces"][i][1] for i in range(3)]
    
    return jsonify({'links': selected_links}), 200

SCOPES = ['https://www.googleapis.com/auth/calendar']
# Path to the service account credentials file
SERVICE_ACCOUNT_FILE = 'E:\programs\HACKATON-15-03-2024\service_account.json'
# Scopes for Google Contacts API
SCOPES2 = ['https://www.googleapis.com/auth/contacts.readonly']

@requests.route('/meeting', methods = ['GET','POST'])
def create_meeting():
    # starting_time = '2024-03-31T10:00:00'
    starting_time = request.get_json().get("query")
    datetime_obj = datetime.strptime(starting_time, '%Y-%m-%dT%H:%M:%S')
    # Adding one hour
    datetime_obj_plus_one_hour = datetime_obj + timedelta(hours=1)

    ending_time = datetime_obj_plus_one_hour.strftime('%Y-%m-%dT%H:%M:%S')
    # ending_time = '2024-03-31T11:00:00'
    contacts = get_contacts()
    name = 'Dima Cvasiuc'
    attendees = []
    attendees.append(contacts[name])

    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(host='localhost', port=8880)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': 'Test Meeting',  # Corrected summary
        'description': 'This is a test meeting.',  # Corrected description
        'start': {
            'dateTime': starting_time,
            'timeZone': 'Europe/Chisinau',
        },
        'end': {
            'dateTime': ending_time,  # Fixed datetime format
            'timeZone': 'Europe/Chisinau',
        },
        'conferenceData': {
            'createRequest': {'requestId': 'random_string'}
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }

    if attendees:
        event['attendees'] = [{'email': attendee} for attendee in attendees]

    try:
        event = service.events().insert(calendarId='primary', body=event, conferenceDataVersion=1).execute()
        print('Event created: %s' % event.get('htmlLink'))

        meet_link = None
        entry_points = event.get('conferenceData', {}).get('entryPoints', [])
        for entry_point in entry_points:
            if entry_point.get('entryPointType') == 'video':
                meet_link = entry_point.get('uri')
                break
        
        if meet_link:
            return jsonify({'meeting': meet_link})
        else:
            return jsonify({'error':'Google Meet link not found.'})
            
    except Exception as e:
        return jsonify({'error':f'An error occured during meeting planing:{e}'})