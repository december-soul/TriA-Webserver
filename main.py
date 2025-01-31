# Import required libraries
import json
from flask import Flask, request, render_template
import csv
from datetime import datetime

# Load JSON config
with open('config.json') as f:
    config = json.load(f)

# Create Flask app
app = Flask(__name__)

# Create website template
@app.route('/')
def index():
    var = "hello"
    print("{}".format(var))
    event_name = config['event']
    logo = config['Logo']
    wettkampf = config['wettkampf']
    max_participants = [wett[k] for wett in wettkampf for k in ['max']]
    return render_template('index.html', event=event_name, Logo=logo, wettkampf=wettkampf, max=max_participants)


# Handle form submission
@app.route('/submit', methods=['POST'])
def submit():
    start_offsets = {}
    print(f"{config['wettkampf']}")
    for i in range(int(config['wettkampf']['max'])):
        start_number = request.form[f'start_number_{i}']
        time = request.form[f'time_{i}']
        start_offsets[i] = {'start_number': start_number, 'time': time}
    # Send data to API as JSON
    api_url = 'http://localhost:5000/api/event'
    response = requests.post(api_url, json={'event': config['event'],  'start_offsets': start_offsets})
    return 'Data submitted successfully!'

# Write data to CSV file
@app.route('/api/event', methods=['POST'])
def write_to_csv():
    event_name = request.json['event']
    start_offsets = request.json['start_offsets']
    # Open the corresponding CSV file for writing
    with open(f'{event_name}.csv', 'a') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.strptime(start_offsets['Swim'], '%H:%M'), datetime.strptime(start_offsets['Run'], '%H:%M')])
    return 'Data written to CSV file successfully!'

if __name__ == '__main__':
    app.run(debug=True)
