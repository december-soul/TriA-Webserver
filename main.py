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
    var = "hello"
    print("{}".format(var))
    event_name = config['event']
    logo = config['Logo']
    wettkampf = config['wettkampf']
    max_participants = [wett[k] for wett in wettkampf for k in ['max']]
    return render_template('index.html', event=event_name, Logo=logo, wettkampf=wettkampf, max=max_participants)


def combine_times(wettkampf_time, measured_time):
    print(f"{wettkampf_time} {measured_time}")
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
    print(f"{selected_wettkampf_index} {selected_wettkampf} {event}")
    # Ersetze Sonderzeichen durch '_'
    event = re.sub(r'[()&/ ]', '_', event)
    wettkampf = re.sub(r'[()&/ ]', '_', selected_wettkampf["title"])
    # Erstelle den Ordner, falls er nicht existiert
    if not os.path.exists(event):
        os.makedirs(event)
    filename = f"{event}/{wettkampf}.trz"
    with open(filename, 'a') as f:
        writer = csv.writer(f, delimiter='\t')

        for i in range(int(selected_wettkampf['max'])):
            start_number = request.form[f'start_number_{i}'].zfill(4)
            time = request.form[f'time_{i}']
            if start_number and time:
                print(f"{start_number} -> {time}")
                # start_offsets[i] = {'start_number': start_number, 'time': time}
                # calc_time = datetime.strptime(time, '%M:%S')
                ctimes = combine_times(selected_wettkampf["start offset"], time)
                writer.writerow([start_number, ctimes])

    return 'Data submitted successfully!'


if __name__ == '__main__':
    app.run(debug=True)
