import os
import shutil

import requests as rs
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from langchain.document_loaders.generic import GenericLoader
from langchain.document_loaders.parsers.audio import OpenAIWhisperParserLocal
from dotenv import load_dotenv
from g4f.client import Client

load_dotenv()

requests = Blueprint('requests',__name__)
whisper_parser = OpenAIWhisperParserLocal(lang_model='openai/whisper-base')

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
        print('C audioloader что-то не так')
        # Load and process the audio file
        result = next(audio_loader.lazy_load())
        print('скрипт отработал')
        print(result.page_content)
        
        return jsonify({
            'message': 'File uploaded and processed successfully',
            'transcription': result.page_content
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

    finally:
        # Clean up the directory after processing
        shutil.rmtree(save_dir)

@requests.route('/weather', methods = ['GET','POST'])
def get_weather(city_name, api_key):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={os.environ.get('WEATHER_API')}&units=metric"
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

    client = Client()
    response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": '''
    Что сказал Дорин Речан про платы ассистентам
    '''}],
    )

    return jsonify({'response':response.choices[0].message.content})