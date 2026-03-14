from fpdf import FPDF
from fpdf.enums import XPos, YPos
import pandas as pd
import os


class CertificateGenerator:
    def __init__(self, image_path):
        self.image_path = image_path

    def create_certificate(self, pdf, name, name2, verein, ak, ak_platz, time1, time2, timetotal, wettkampf, veranstaltung, background):
        print(f"Creating certificate for: {name}{name2}")
        pdf.add_page()
        if background:
            pdf.image(self.image_path, x=0, y=0, w=210, h=297)
        self._add_text(pdf, veranstaltung, 25, 70)
        self._add_text(pdf, wettkampf, 18, 90)
        if name2:
            self._add_text(pdf, name, 32, 110)
            self._add_text(pdf, name2, 32, 130)
        else:
            self._add_text(pdf, name, 42, 120)
        if not pd.isna(verein):
            self._add_text(pdf, verein, 22, 145)
        if not pd.isna(ak):
            self._add_text(pdf, f"erreichte in der Altersklasse {ak} den", 22, 165)
        self._add_text(pdf, f"{ak_platz}. Platz", 42, 185)
        self._add_text(pdf, f" Swim: {time1}", 18, 210)
        self._add_text(pdf, f"  Run: {time2}", 18, 220)
        self._add_text(pdf, f"Total: {timetotal}", 18, 230)

    def _add_text(self, pdf, text, size, y):
        pdf.set_font("helvetica", size=size)
        pdf.set_xy(0, y)
        pdf.cell(0, 0, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')


def read_event_details(filename):
    with open(filename, encoding="latin_1") as file:
        lines = [line.rstrip() for line in file]
    print(f"Reading event details from: {filename}")
    wettkampf = "".join(lines[5].split("am")[0])
    veranstaltung = lines[2]
    return wettkampf, veranstaltung


def create_directory(directory_name):
    print(f"Checking directory: {directory_name}")
    if not os.path.exists(directory_name):
        os.mkdir(directory_name)


def detect_format(filename):
    """Detect whether file uses old or new TriA format by checking for Snr column."""
    with open(filename, encoding='unicode_escape', errors='replace') as f:
        lines = [next(f) for _ in range(15)]

    # Find the CSV header line - it's the first line with a semicolon that's also a valid header
    # The header line contains column names like Rng, Snr, Name, etc.
    header_line = None
    for line in lines:
        # Header line has multiple semicolons and contains column markers
        if ';' in line and ('Rng;' in line or 'Name' in line):
            header_line = line
            break

    if header_line and 'Snr' in header_line:
        return 'old'
    return 'new'


def get_column_mapping(format_type, lenswim, lenrun):
    """Get column mapping based on format type."""
    if format_type == 'old':
        return {
            'skiprows': 8,
            'swim_col': f'S{lenswim}',
            'run_col': f'L{lenrun}',
            'total_col': 'Endzeit'
        }
    else:
        # New format: Swim 100m, Run 400m, Summe
        swim_col = f'Swim {lenswim}m'
        run_col = f'Run {lenrun}m'
        return {
            'skiprows': 8,
            'swim_col': swim_col,
            'run_col': run_col,
            'total_col': 'Summe'
        }


def process_wettkamp(filename, lenswim, lenrun, staffel, onlytop, background):
    print(f"Processing file: {filename}")

    # Detect format and get column mapping
    format_type = detect_format(filename)
    print(f"Detected format: {format_type}")
    col_mapping = get_column_mapping(format_type, lenswim, lenrun)

    wettkampf, veranstaltung = read_event_details(filename)
    create_directory(f"Urkunden_{wettkampf.replace('/', '_')}")
    data = pd.read_csv(filename, encoding='unicode_escape', skiprows=col_mapping['skiprows'], delimiter=";", header=0)
    generator = CertificateGenerator("background.png")
    pdf_all = FPDF()
    pdf_top3 = FPDF()
    print(f"Generating certificates for {len(data)} participants")
    for u in data.itertuples():
        platz = u.Rng
        if platz != "DNF":
            ak = None if staffel else u.Ak
            ak_platz = u.AkRng if ak else platz
            if staffel:
                name = f"{u._4}"
            else:
                name = f"{u._3}"
            name2 = None
            if staffel:
                name2 = f"{u._7}"
            verein = u.Mannschaft if staffel else u._4
            swim = getattr(u, col_mapping['swim_col'])
            run = getattr(u, col_mapping['run_col'])
            total = getattr(u, col_mapping['total_col'])
            if not onlytop:
                print(f"Generating certificate for: {name} {name2}, Platz: {platz}, AK Platz: {ak_platz}")
                pdf = FPDF()
                generator.create_certificate(pdf, name, name2, verein, ak, ak_platz, swim, run, total, wettkampf, veranstaltung, background)
                generator.create_certificate(pdf_all, name, name2, verein, ak, ak_platz, swim, run, total, wettkampf,
                                             veranstaltung, background)
                pdf.output(f"Urkunden_{wettkampf.replace('/', '_')}/{ak}_{ak_platz}_{name}{name2}.pdf")
            if int(ak_platz) <= 3:
                pdf = FPDF()
                create_directory(f"Urkunden_Top_{wettkampf.replace('/', '_')}")
                print(f"Generating top certificate for: {name}{name2}, AK: {ak}, AK Platz: {ak_platz}")
                generator.create_certificate(pdf_top3, name, name2, verein, ak, ak_platz, swim, run, total, wettkampf, veranstaltung, background)
                generator.create_certificate(pdf, name, name2, verein, ak, ak_platz, swim, run, total, wettkampf,
                                             veranstaltung, background)
                pdf.output(f"Urkunden_Top_{wettkampf.replace('/', '_')}/{ak}_{ak_platz}_{name}{name2}.pdf")
    pdf_top3.output(f"Urkunden_Top_{wettkampf.replace('/', '_')}/top3_certificates.pdf")
    pdf_all.output(f"Urkunden_{wettkampf.replace('/', '_')}/all_certificates.pdf")
    return f"Urkunden_Top_{wettkampf.replace('/', '_')}/top3_certificates.pdf"
