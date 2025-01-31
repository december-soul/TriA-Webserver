# Import required libraries
import json
import re
import os
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
    selected_wettkampf_index = int(request.form['wettkampf_index'])
    selected_wettkampf = config['wettkampf'][selected_wettkampf_index]
    event = config['event']
    print(f"{selected_wettkampf_index} {selected_wettkampf} {event}")
    # Ersetze Sonderzeichen durch '_'
    event = re.sub(r'[()&/] ', '_', event)
    wettkampf = re.sub(r'[()&/] ', '_', selected_wettkampf["title"])
    # Erstelle den Ordner, falls er nicht existiert
    if not os.path.exists(event):
        os.makedirs(event)
    filename = f"{event}/{wettkampf}.cvs"
    with open(filename, 'a') as f:
        writer = csv.writer(f)

        for i in range(int(selected_wettkampf['max'])):
            start_number = request.form[f'start_number_{i}']
            time = request.form[f'time_{i}']
            print(f"{start_number} -> {time}")
            if start_number and time:
                # start_offsets[i] = {'start_number': start_number, 'time': time}
                writer.writerow([start_number, datetime.strptime(time, '%H:%M')])

    return 'Data submitted successfully!'

# Write data to CSV file
@app.route('/api/event', methods=['POST'])
def write_to_csv():
    event_name = request.json['event']
    start_offsets = request.json['start_offsets']
    # Open the corresponding CSV file for writing
    with open(f'{event_name}.csv', 'a') as f:
        writer = csv.writer(f)
        for offset in start_offsets.values():
            writer.writerow([datetime.strptime(offset['time'], '%H:%M')])
    return 'Data written to CSV file successfully!'

if __name__ == '__main__':
    app.run(debug=True)
