# Import required libraries
import csv
import json
import logging
import os
import re
from datetime import datetime, timedelta
from urllib.parse import quote

from flask import Flask, request, render_template, send_file, jsonify, abort
from werkzeug.utils import secure_filename

from certificateGenerator import process_wettkamp

## TODO
# Urkunden generieren, automatisch Staffel berücksichtigen
# Der Name Groß macht Probleme
# Staffel müssen noch generiert werden
# lange Namen berücksichtigen
# testen ob das mit dem Background so passt
# random Zeiten Generator zum testen


# Load JSON config
with open('config.json') as cf:
    config = json.load(cf)

# Configure logging so debug/error messages from certificateGenerator are visible
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Create Flask app
app = Flask(__name__)

# Register a Jinja2 filter to percent-encode filenames for use in URLs
@app.template_filter('urlencode')
def urlencode_filter(s):
    return quote(s, safe='')


# Create website template
@app.route('/')
def index():
    event_name = config['event']
    logo = config['Logo']
    wettkampf = config['wettkampf']
    return render_template('index.html', event=event_name, Logo=logo, wettkampf=wettkampf)


def extract_unique_titles(events):
    unique_titles = set()

    for event in events:
        title = event['title']
        processed_title = title.split(" - ")[0]  # Alles nach " - " entfernen
        unique_titles.add(processed_title)  # In ein Set einfügen (automatische Duplikatelöschung)

    return list(unique_titles)  # Set in Liste umwandeln

@app.route('/cert')
def cert():
    event_name = config['event']
    logo = config['Logo']
    wettkampf = extract_unique_titles(config['wettkampf'])
    print(wettkampf)
    return render_template('cert.html', event=event_name, Logo=logo, wettkampf=wettkampf)

@app.route('/createCert', methods=['POST'])
def createCert():
    # Retrieve form data
    form_data = request.form.to_dict()
    print("Received form data:", form_data)
    onlytop    = request.form.get('onlyTop3')       == 'on'
    background = request.form.get('withBackground') == 'on'

    selected_wettkampf = request.form['wettkampf_name']
    print(selected_wettkampf)

    def _render_warning(msg):
        event_name = config['event']
        logo = config['Logo']
        wettkampf_list = extract_unique_titles(config['wettkampf'])
        return render_template(
            'cert.html',
            event=event_name,
            Logo=logo,
            wettkampf=wettkampf_list,
            warning=msg,
        )

    try:
        if selected_wettkampf == "Swim 100 & Run 400":
            pdf_filename = process_wettkamp(f"{selected_wettkampf}.txt", 100, 400, False, onlytop, background)
        elif selected_wettkampf == "Swim 200 & Run 1200":
            pdf_filename = process_wettkamp(f"{selected_wettkampf}.txt", 200, 1200, False, onlytop, background)
        elif selected_wettkampf == "Swim 400 & Run 2500":
            pdf_filename = process_wettkamp(f"{selected_wettkampf}.txt", 400, 2500, False, onlytop, background)
        elif selected_wettkampf == "Swim 800 & Run 5000":
            pdf_filename = process_wettkamp(f"{selected_wettkampf}.txt", 800, 5000, False, onlytop, background)
        elif selected_wettkampf == "Swim 800 & Run 5000 Staffel":
            pdf_filename = process_wettkamp(f"{selected_wettkampf}.txt", 800, 5000, True, onlytop, background)
        else:
            return _render_warning(f"Unbekannter Wettkampf: {selected_wettkampf}")
    except FileNotFoundError as e:
        return _render_warning(str(e))

    return send_file(pdf_filename, as_attachment=True, download_name=f"{selected_wettkampf}.pdf")

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
    selected_wettkampf_index = int(request.form['wettkampf_index'])
    selected_wettkampf = config['wettkampf'][selected_wettkampf_index]
    event = config['event']
    event = re.sub(r'[()&/ ]', '_', event)
    wettkampf = re.sub(r'[()&/ ]', '_', selected_wettkampf["title"])
    # create folder
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


# Directory containing TriA .trz files
TRZ_DIR = 'SwimRun_2026'


@app.route('/trz-files')
def trz_files():
    base = os.path.dirname(__file__)
    trz_path = os.path.join(base, TRZ_DIR)
    files = []
    if os.path.isdir(trz_path):
        files = sorted([f for f in os.listdir(trz_path) if f.lower().endswith('.trz')])
    event_name = config['event']
    logo = config['Logo']
    return render_template('trz_downloads.html', event=event_name, Logo=logo, files=files)


@app.route('/trz-files/<path:filename>')
def download_trz(filename):
    # Security: only allow .trz files and prevent path traversal
    safe_name = os.path.basename(filename)
    if not safe_name.lower().endswith('.trz'):
        abort(400)
    base = os.path.dirname(__file__)
    trz_path = os.path.join(base, TRZ_DIR)
    file_path = os.path.join(trz_path, safe_name)
    real_file = os.path.realpath(file_path)
    real_dir = os.path.realpath(trz_path)
    if not real_file.startswith(real_dir + os.sep):
        abort(403)
    if not os.path.isfile(real_file):
        abort(404)
    return send_file(real_file, as_attachment=True, download_name=safe_name)


# Directories that contain downloadable Urkunden PDFs
URKUNDEN_DIRS = [
    'Urkunden_100m Schwimmen_0,4km Laufen  ',
    'Urkunden_200m Schwimmen_1,2km Laufen  ',
    'Urkunden_400m Schwimmen_2,5km Laufen  ',
    'Urkunden_Top_100m Schwimmen_0,4km Laufen  ',
    'Urkunden_Top_200m Schwimmen_1,2km Laufen  ',
    'Urkunden_Top_400m Schwimmen_2,5km Laufen  ',
]


@app.route('/downloads')
def downloads():
    base = os.path.dirname(__file__)
    dirs_data = []
    for idx, dir_name in enumerate(URKUNDEN_DIRS):
        dir_path = os.path.join(base, dir_name)
        pdfs = []
        if os.path.isdir(dir_path):
            pdfs = sorted([f for f in os.listdir(dir_path) if f.lower().endswith('.pdf')])
        dirs_data.append({'idx': idx, 'name': dir_name.strip(), 'files': pdfs})
    event_name = config['event']
    logo = config['Logo']
    return render_template('downloads.html', event=event_name, Logo=logo, dirs=dirs_data)


@app.route('/downloads/<int:dir_idx>/<path:filename>')
def download_pdf(dir_idx, filename):
    # Security: only allow known directory indices and .pdf files
    if dir_idx < 0 or dir_idx >= len(URKUNDEN_DIRS):
        abort(404)
    if not filename.lower().endswith('.pdf'):
        abort(400)
    dir_name = URKUNDEN_DIRS[dir_idx]
    base = os.path.dirname(__file__)
    file_path = os.path.join(base, dir_name, filename)
    # Ensure the resolved path is still inside the expected directory
    real_file = os.path.realpath(file_path)
    real_dir = os.path.realpath(os.path.join(base, dir_name))
    if not real_file.startswith(real_dir + os.sep):
        abort(403)
    if not os.path.isfile(real_file):
        abort(404)
    return send_file(real_file, as_attachment=True, download_name=filename)


ALLOWED_FILENAMES = {
    'Swim 100 & Run 400.txt',
    'Swim 200 & Run 1200.txt',
    'Swim 400 & Run 2500.txt',
    'Swim 800 & Run 5000.txt',
    'Swim 800 & Run 5000 Staffel.txt',
}


@app.route('/upload', methods=['POST'])
def upload():
    uploaded_files = request.files.getlist('files')
    results = []
    for file in uploaded_files:
        original_name = file.filename
        if original_name not in ALLOWED_FILENAMES:
            results.append({'name': original_name, 'status': 'error',
                            'message': f'Dateiname nicht erlaubt: {original_name}'})
            continue
        save_path = os.path.join(os.path.dirname(__file__), original_name)
        file.save(save_path)
        results.append({'name': original_name, 'status': 'ok',
                        'message': f'{original_name} erfolgreich hochgeladen.'})
    return jsonify(results)


if __name__ == '__main__':
    app.run(debug=True, port=5005, host='0.0.0.0')
