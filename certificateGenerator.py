from fpdf import FPDF
from fpdf.enums import XPos, YPos
import pandas as pd
import os


class CertificateGenerator:
    def __init__(self, image_path):
        self.image_path = image_path

    def create_certificate(self, pdf, name, verein, ak, ak_platz, time1, time2, timetotal, wettkampf, veranstaltung, background):
        print(f"Creating certificate for: {name}")
        pdf.add_page()
        if background:
            pdf.image(self.image_path, x=0, y=0, w=210, h=297)
        self._add_text(pdf, veranstaltung, 25, 70)
        self._add_text(pdf, wettkampf, 18, 90)
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


def process_wettkamp(filename, lenswim, lenrun, staffel, onlytop, background):
    print(f"Processing file: {filename}")
    wettkampf, veranstaltung = read_event_details(filename)
    create_directory(f"Urkunden_{wettkampf.replace('/', '_')}")
    data = pd.read_csv(filename, encoding='unicode_escape', skiprows=8, delimiter=";", header=0)
    generator = CertificateGenerator("background.png")
    pdf_all = FPDF()
    pdf_top3 = FPDF()
    print(f"Generating certificates for {len(data)} participants")
    for u in data.itertuples():
        platz = u.Rng
        if platz != "DNF":
            ak = None if staffel else u.Ak
            ak_platz = u.AkRng if ak else platz
            name = f"{u._4} & {u._7}" if staffel else u._3
            verein = u.Mannschaft if staffel else u._4
            swim = eval(f"u.S{lenswim}")
            run = eval(f"u.L{lenrun}")
            total = u.Endzeit
            if not onlytop:
                print(f"Generating certificate for: {name}, Platz: {platz}, AK Platz: {ak_platz}")
                pdf = FPDF()
                generator.create_certificate(pdf, name, verein, ak, ak_platz, swim, run, total, wettkampf, veranstaltung, background)
                generator.create_certificate(pdf_all, name, verein, ak, ak_platz, swim, run, total, wettkampf,
                                             veranstaltung, background)
                pdf.output(f"Urkunden_{wettkampf.replace('/', '_')}/{ak}_{ak_platz}_{name}.pdf")
            if int(ak_platz) <= 3:
                pdf = FPDF()
                create_directory(f"Urkunden_Top_{wettkampf.replace('/', '_')}")
                print(f"Generating top certificate for: {name}, AK: {ak}, AK Platz: {ak_platz}")
                generator.create_certificate(pdf_top3, name, verein, ak, ak_platz, swim, run, total, wettkampf, veranstaltung, background)
                generator.create_certificate(pdf, name, verein, ak, ak_platz, swim, run, total, wettkampf,
                                             veranstaltung, background)
                pdf.output(f"Urkunden_Top_{wettkampf.replace('/', '_')}/{ak}_{ak_platz}_{name}.pdf")
    pdf_top3.output(f"Urkunden_Top_{wettkampf.replace('/', '_')}/top3_certificates.pdf")
    pdf_all.output(f"Urkunden_{wettkampf.replace('/', '_')}/all_certificates.pdf")
    return f"Urkunden_Top_{wettkampf.replace('/', '_')}/top3_certificates.pdf"


#process_wettkamp("SwimRun2024_100.txt", 100, 400, False, False, False)
#process_wettkamp("SwimRun2024_200.txt", 200, 1200, False)
#process_wettkamp("SwimRun2024_400.txt", 400, 2500, False)
#process_wettkamp("SwimRun2024_400s.txt", 400, 2500, True)
#process_wettkamp("SwimRun2024_800.txt", 800, 5000, False)
#process_wettkamp("SwimRun2024_800s.txt", 800, 5000, True)
