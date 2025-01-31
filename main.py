# Import required libraries
import csv
import json
import os
import re
from datetime import datetime, timedelta

from flask import Flask, request, render_template

# Load JSON config
with open('config.json') as f:
    config = json.load(f)

# Create Flask app
app = Flask(__name__)


# Create website template
@app.route('/')
def index():
    event_name = config['event']
    logo = config['Logo']
    wettkampf = config['wettkampf']
    return render_template('index.html', event=event_name, Logo=logo, wettkampf=wettkampf)


def combine_times(wettkampf_time, measured_time):
    # Parse the wettkampf time
    wettkampf_dt = datetime.strptime(wettkampf_time, '%H:%M:%S')

    # Parse the measured time
    measured_dt = datetime.strptime(measured_time, '%M:%S')

    # Kombiniere die Zeiten
    combined_time = wettkampf_dt + timedelta(minutes=measured_dt.minute, seconds=measured_dt.second)

    # Formatiere die kombinierte Zeit im gewünschten Format
    return combined_time.strftime('%H:%M:%S,0')


# Handle form submission
@app.route('/submit', methods=['POST'])
def submit():
    start_offsets = {}
    selected_wettkampf_index = int(request.form['wettkampf_index'])
    selected_wettkampf = config['wettkampf'][selected_wettkampf_index]
    event = config['event']
    event = re.sub(r'[()&/ ]', '_', event)
    wettkampf = re.sub(r'[()&/ ]', '_', selected_wettkampf["title"])
    # Erstelle den Ordner, falls er nicht existiert
    if not os.path.exists(event):
        os.makedirs(event)
    filename = f"{event}/{wettkampf}.trz"
    with open(filename, 'a') as f:
        writer = csv.writer(f, delimiter='\t')
        print(f"write data to {filename}")

        for i in range(int(selected_wettkampf['max'])):
            start_number = request.form[f'start_number_{i}'].zfill(4)
            time = request.form[f'time_{i}']
            if start_number and time and start_number != "0000":
                ctimes = combine_times(selected_wettkampf["start offset"], time)
                print(f"{start_number} -> {ctimes}")
                writer.writerow([start_number, ctimes])

    return f"Data submitted successfully!\n bitte importiere jetzt die Datei {event}/{wettkampf}.trz"


if __name__ == '__main__':
    app.run(debug=True)
