from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class ParticipantData:
    name: str
    name2: Optional[str]
    verein: str
    ak: Optional[str]
    ak_platz: int
    swim: str
    run: str
    total: str


# ---------------------------------------------------------------------------
# Certificate generation
# ---------------------------------------------------------------------------

class CertificateGenerator:
    def __init__(self, image_path: str):
        self.image_path = image_path

    def create_certificate(
        self,
        pdf: FPDF,
        name: str,
        name2: Optional[str],
        verein: str,
        ak: Optional[str],
        ak_platz: int,
        time1: str,
        time2: str,
        timetotal: str,
        wettkampf: str,
        veranstaltung: str,
        background: bool,
    ) -> None:
        logger.debug("Creating certificate for: %s%s", name, name2 or "")
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
        if ak and not pd.isna(ak):
            self._add_text(pdf, f"erreichte in der Altersklasse {ak} den", 22, 165)
        self._add_text(pdf, f"{ak_platz}. Platz", 42, 185)
        self._add_text(pdf, f" Swim: {time1}", 18, 210)
        self._add_text(pdf, f"  Run: {time2}", 18, 220)
        self._add_text(pdf, f"Total: {timetotal}", 18, 230)

    def _add_text(self, pdf: FPDF, text: str, size: int, y: int) -> None:
        pdf.set_font("helvetica", size=size)
        pdf.set_xy(0, y)
        pdf.cell(0, 0, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")


# ---------------------------------------------------------------------------
# File / format helpers
# ---------------------------------------------------------------------------

def read_event_details(filename: str) -> tuple[str, str]:
    with open(filename, encoding="latin_1") as file:
        lines = [line.rstrip() for line in file]
    logger.info("Reading event details from: %s", filename)
    wettkampf = "".join(lines[5].split("am")[0])
    veranstaltung = lines[2]
    return wettkampf, veranstaltung


def _safe_dir(path: str) -> None:
    """Create directory (and any parents) if it does not already exist."""
    os.makedirs(path, exist_ok=True)


def detect_format(filename: str) -> str:
    """Detect whether the file uses the old or new TriA format by looking for 'Serienwertung'."""
    with open(filename, encoding="unicode_escape", errors="replace") as f:
        for _ in range(15):
            line = f.readline()
            if not line:
                break
            if "Serienwertung" in line:
                return "new"
    return "old"


def get_column_mapping(format_type: str, lenswim: str, lenrun: str) -> dict:
    """Return column mapping for the given format type."""
    if format_type == "old":
        return {
            "skiprows": 8,
            "swim_col": f"S{lenswim}",
            "run_col": f"L{lenrun}",
            "total_col": "Endzeit",
            "name_idx": 3,    # "Name, Vorname" after Index, Rng, Snr
            "verein_idx": 4,  # "Verein/Ort"
        }
    else:
        # New format: Swim 100m, Run 400m, Summe (no Snr column)
        return {
            "skiprows": 8,
            "swim_col": f"S{lenswim}",   # fixed: was missing f-prefix
            "run_col": f"L{lenrun}",      # fixed: was missing f-prefix
            "total_col": "Summe",
            "name_idx": 2,    # "Name, Vorname" after Index, Rng
            "verein_idx": 3,  # "Verein/Ort"
        }


def get_staffel_mapping(lenswim: str, lenrun: str) -> dict:
    """Return column mapping for the Staffel (relay) format."""
    return {
        "skiprows": 8,
        "swim_col": f"S{lenswim}",
        "run_col": f"L{lenrun}",
        "total_col": "Endzeit",
        "name_idx": 4,    # Teilnehmer 1 (after Index, Rng, Snr, Mannschaft)
        "verein_idx": 3,  # Mannschaft (team name)
        "name2_idx": 7,   # Teilnehmer 2 (after Teilnehmer1, S800, Rng1)
    }


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------

def _safe_name2(value) -> Optional[str]:
    """Return None when name2 is absent, NaN, or the literal string 'None'."""
    if value is None:
        return None
    s = str(value).strip()
    return None if s in ("", "None", "nan") else s


def _safe_int(value) -> Optional[int]:
    """Convert to int, returning None on failure."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _cert_call(
    generator: CertificateGenerator,
    pdf: FPDF,
    p: ParticipantData,
    wettkampf: str,
    veranstaltung: str,
    background: bool,
) -> None:
    """Convenience wrapper to avoid repeating the 11-argument call."""
    generator.create_certificate(
        pdf,
        p.name, p.name2, p.verein,
        p.ak, p.ak_platz,
        p.swim, p.run, p.total,
        wettkampf, veranstaltung, background,
    )


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------

def process_wettkamp(
    filename: str,
    lenswim: str,
    lenrun: str,
    staffel: bool,
    onlytop: bool,
    background: bool,
) -> str:
    """
    Generate PDF certificates for all participants in *filename*.

    Returns the path to the combined top-3 PDF, or an empty string when there
    are no top-3 participants.
    """
    logger.info("Processing file: %s", filename)

    # Resolve column mapping -----------------------------------------------
    if staffel:
        col_mapping = get_staffel_mapping(lenswim, lenrun)
        format_type = "staffel"
    else:
        format_type = detect_format(filename)
        col_mapping = get_column_mapping(format_type, lenswim, lenrun)
    logger.info("Detected format: %s", format_type)

    # Event meta-data -------------------------------------------------------
    wettkampf, veranstaltung = read_event_details(filename)
    safe_name = wettkampf.replace("/", "_")  # computed once; used in all paths

    all_dir = f"Urkunden_{safe_name}"
    top_dir = f"Urkunden_Top_{safe_name}"
    _safe_dir(all_dir)
    _safe_dir(top_dir)  # create both directories up front, not inside the loop

    # Load participant data -------------------------------------------------
    data = pd.read_csv(
        filename,
        encoding="unicode_escape",
        skiprows=col_mapping["skiprows"],
        delimiter=";",
        header=0,
    )

    generator = CertificateGenerator("background.png")
    pdf_all  = FPDF()
    pdf_top3 = FPDF()
    has_top3 = False

    logger.info("Generating certificates for %d participants", len(data))

    for u in data.itertuples():
        platz = u.Rng
        if platz == "DNF":
            continue  # skip non-finishers early

        # Extract participant fields ----------------------------------------
        ak           = None if staffel else getattr(u, "Ak", None)
        ak_platz_raw = u.AkRng if ak else platz
        ak_platz_int = _safe_int(ak_platz_raw)
        if ak_platz_int is None:
            logger.warning(
                "Skipping row with non-numeric ak_platz=%r (overall platz=%s)",
                ak_platz_raw, platz,
            )
            continue

        name   = str(u[col_mapping["name_idx"]])
        name2  = _safe_name2(
            u[col_mapping["name2_idx"]] if "name2_idx" in col_mapping else None
        )
        verein = u[col_mapping["verein_idx"]]
        swim   = getattr(u, col_mapping["swim_col"])
        run    = getattr(u, col_mapping["run_col"])
        total  = getattr(u, col_mapping["total_col"])

        participant = ParticipantData(
            name=name, name2=name2, verein=verein,
            ak=ak, ak_platz=ak_platz_int,
            swim=swim, run=run, total=total,
        )

        # Sanitised filename parts
        ak_part    = ak or "NoAK"
        name2_part = name2 or ""

        # Individual + combined-all certificate ----------------------------
        if not onlytop:
            logger.debug(
                "Generating certificate: %s %s  Platz=%s  AKPlatz=%d",
                name, name2, platz, ak_platz_int,
            )
            pdf_ind = FPDF()
            _cert_call(generator, pdf_ind,  participant, wettkampf, veranstaltung, background)
            _cert_call(generator, pdf_all,  participant, wettkampf, veranstaltung, background)
            pdf_ind.output(f"{all_dir}/{ak_part}_{ak_platz_int}_{name}{name2_part}.pdf")

        # Top-3 certificate ------------------------------------------------
        if ak_platz_int <= 3:
            has_top3 = True
            logger.debug(
                "Generating top certificate: %s%s  AK=%s  AKPlatz=%d",
                name, name2_part, ak, ak_platz_int,
            )
            pdf_top = FPDF()
            _cert_call(generator, pdf_top,  participant, wettkampf, veranstaltung, background)
            _cert_call(generator, pdf_top3, participant, wettkampf, veranstaltung, background)
            pdf_top.output(f"{top_dir}/{ak_part}_{ak_platz_int}_{name}{name2_part}.pdf")

    # Write combined PDFs --------------------------------------------------
    top3_combined = ""
    if has_top3:
        top3_combined = f"{top_dir}/top3_certificates.pdf"
        pdf_top3.output(top3_combined)
    else:
        logger.warning("No top-3 participants found; skipping top3_certificates.pdf")

    all_combined = ""
    if not onlytop:
        all_combined = f"{all_dir}/all_certificates.pdf"
        pdf_all.output(all_combined)

    # Return the most relevant combined PDF:
    # - "only top" mode  → top3 PDF
    # - normal mode      → all-certificates PDF (falls back to top3 if all is empty)
    if onlytop:
        return top3_combined
    return all_combined or top3_combined
