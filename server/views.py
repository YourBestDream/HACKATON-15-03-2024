from flask import Blueprint, jsonify
import requests as rs

views = Blueprint('views', __name__)

@views.route('/',methods = ['GET','POST'])
def starting_page():

    return jsonify({'message':'Hello, epta'})