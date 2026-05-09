"""Generate a PDF report from interview data."""

import io
from typing import Any

from fpdf import FPDF


BRAND_BLUE = (37, 99, 235)
DARK = (17, 24, 39)
GRAY = (107, 114, 128)
LIGHT_GRAY = (243, 244, 246)
RED = (220, 38, 38)
AMBER = (217, 119, 6)
GREEN = (22, 163, 74)
PURPLE = (147, 51, 234)
PINK = (219, 39, 119)
INDIGO = (79, 70, 229)

CATEGORY_COLORS: dict[str, tuple[int, int, int]] = {
    "pain_points": RED,
    "goals": BRAND_BLUE,
    "objections": AMBER,
    "feature_requests": AMBER,
    "workarounds": GRAY,
    "emotional_moments": PINK,
    "strong_quotes": INDIGO,
}

CATEGORY_LABELS: dict[str, str] = {
    "pain_points": "Pain Points",
    "goals": "Goals",
    "objections": "Objections",
    "feature_requests": "Feature Requests",
    "workarounds": "Workarounds",
    "emotional_moments": "Emotional Moments",
    "strong_quotes": "Key Quotes",
}


class ReportPDF(FPDF):
    def __init__(self, title: str):
        super().__init__()
        self.report_title = title
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)

    def header(self):
        self.set_fill_color(*BRAND_BLUE)
        self.rect(0, 0, 210, 2, "F")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 10, f"Customer Research Agent  •  Page {self.page_no()}", align="C")

    def section_header(self, text: str):
        self.ln(6)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*DARK)
        self.cell(0, 8, text, ln=True)
        self.set_draw_color(*BRAND_BLUE)
        self.set_line_width(0.5)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(4)

    def sub_header(self, text: str):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*DARK)
        self.cell(0, 7, text, ln=True)
        self.ln(1)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def label(self, text: str, color: tuple[int, int, int] = GRAY):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*color)
        self.cell(0, 5, text.upper(), ln=True)

    def pill(self, text: str, color: tuple[int, int, int]):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*color)
        self.set_fill_color(color[0], color[1], color[2])
        w = self.get_string_width(text) + 6
        x, y = self.get_x(), self.get_y()
        self.set_fill_color(
            min(color[0] + 200, 255),
            min(color[1] + 200, 255),
            min(color[2] + 200, 255),
        )
        self.rect(x, y, w, 5, "F")
        self.set_xy(x, y)
        self.cell(w, 5, text)
        self.ln(6)

    def confidence_bar(self, confidence: float):
        x, y = self.get_x(), self.get_y()
        bar_w = 30
        filled = bar_w * confidence
        color = GREEN if confidence >= 0.8 else AMBER if confidence >= 0.5 else RED
        self.set_fill_color(*LIGHT_GRAY)
        self.rect(x, y + 1, bar_w, 3, "F")
        self.set_fill_color(*color)
        self.rect(x, y + 1, filled, 3, "F")
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GRAY)
        self.set_xy(x + bar_w + 2, y)
        self.cell(15, 5, f"{int(confidence * 100)}%")
        self.ln(5)


def generate_report_pdf(
    interview: dict[str, Any],
    transcript: dict[str, Any] | None,
    analysis: dict[str, Any] | None,
    report: dict[str, Any] | None,
) -> bytes:
    """Generate a PDF and return it as bytes."""
    pdf = ReportPDF(title=interview.get("title", "Interview Report"))
    pdf.add_page()

    # ------------------------------------------------------------------ #
    # Cover / title block
    # ------------------------------------------------------------------ #
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*DARK)
    pdf.multi_cell(0, 10, interview.get("title", "Interview Report"))
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*GRAY)
    meta_parts = []
    if interview.get("original_filename"):
        meta_parts.append(interview["original_filename"])
    if interview.get("language_detected"):
        meta_parts.append(interview["language_detected"].upper())
    if interview.get("created_at"):
        meta_parts.append(interview["created_at"][:10])
    pdf.cell(0, 6, "  •  ".join(meta_parts), ln=True)
    pdf.ln(4)

    # ------------------------------------------------------------------ #
    # Executive Summary
    # ------------------------------------------------------------------ #
    if report and report.get("executive_summary"):
        pdf.section_header("Executive Summary")
        pdf.body_text(report["executive_summary"])

    # ------------------------------------------------------------------ #
    # Themes
    # ------------------------------------------------------------------ #
    themes = (report or {}).get("themes") or []
    if themes:
        pdf.section_header("Themes")
        for theme in themes:
            pdf.sub_header(theme.get("name", ""))
            if theme.get("description"):
                pdf.body_text(theme["description"])
            evidence = theme.get("evidence_count", 0)
            if evidence:
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(*GRAY)
                pdf.cell(0, 5, f"{evidence} supporting evidence items", ln=True)
            pdf.ln(2)

    # ------------------------------------------------------------------ #
    # Recommendations
    # ------------------------------------------------------------------ #
    recommendations = (report or {}).get("recommendations") or []
    if recommendations:
        pdf.section_header("Recommendations")
        for rec in recommendations:
            if not isinstance(rec, dict):
                continue
            pdf.sub_header(rec.get("title", ""))
            priority = rec.get("priority", "").upper()
            effort = rec.get("effort", "").upper()
            color = RED if priority == "HIGH" else AMBER if priority == "MEDIUM" else GREEN
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*color)
            tag = f"Priority: {priority}"
            if effort:
                tag += f"   Effort: {effort}"
            pdf.cell(0, 5, tag, ln=True)
            pdf.ln(1)
            if rec.get("description"):
                pdf.body_text(rec["description"])

    # ------------------------------------------------------------------ #
    # Insights by category
    # ------------------------------------------------------------------ #
    if analysis:
        pdf.section_header("Insights")
        for cat_key, cat_label in CATEGORY_LABELS.items():
            insights = analysis.get(cat_key) or []
            if not insights:
                continue

            color = CATEGORY_COLORS.get(cat_key, GRAY)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*color)
            pdf.cell(0, 7, f"{cat_label} ({len(insights)})", ln=True)
            pdf.set_draw_color(*color)
            pdf.set_line_width(0.3)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(3)

            for insight in insights:
                if not isinstance(insight, dict):
                    continue

                # Summary
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(*DARK)
                pdf.multi_cell(0, 5.5, insight.get("text", ""))
                pdf.ln(1)

                # Quote
                quote = insight.get("quote", "")
                if quote:
                    pdf.set_fill_color(*LIGHT_GRAY)
                    x, y = pdf.get_x(), pdf.get_y()
                    pdf.set_draw_color(*GRAY)
                    pdf.set_line_width(0.8)
                    pdf.line(22, y, 22, y + 12)
                    pdf.set_line_width(0.2)
                    pdf.set_x(26)
                    pdf.set_font("Helvetica", "I", 9)
                    pdf.set_text_color(*GRAY)
                    pdf.multi_cell(160, 5, f'"{quote}"')
                    pdf.ln(1)

                # Translation
                translated = insight.get("translated_quote") or insight.get("translated_text")
                if translated:
                    pdf.set_x(26)
                    pdf.set_font("Helvetica", "I", 9)
                    pdf.set_text_color(*BRAND_BLUE)
                    pdf.multi_cell(160, 5, f"Translation: {translated}")
                    pdf.ln(1)

                # Meta: speaker, timestamp, confidence
                speaker = insight.get("speaker", "")
                timestamp = insight.get("timestamp")
                confidence = insight.get("confidence", 0)

                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(*DARK)
                meta = speaker
                if timestamp is not None:
                    m = int(timestamp // 60)
                    s = int(timestamp % 60)
                    meta += f"  @{m}:{s:02d}"
                pdf.cell(60, 5, meta)
                if confidence:
                    pdf.confidence_bar(confidence)
                else:
                    pdf.ln(5)

                pdf.ln(3)

            pdf.ln(2)

    # ------------------------------------------------------------------ #
    # Transcript
    # ------------------------------------------------------------------ #
    if transcript and transcript.get("segments"):
        pdf.add_page()
        pdf.section_header("Transcript")
        segments = transcript["segments"]
        current_speaker = None

        for seg in segments:
            if not isinstance(seg, dict):
                continue
            speaker = seg.get("speaker", "Unknown")
            text = seg.get("text", "")
            translated = seg.get("translated_text")

            if speaker != current_speaker:
                pdf.ln(2)
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(*BRAND_BLUE)
                pdf.cell(0, 5, speaker, ln=True)
                current_speaker = speaker

            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*DARK)
            pdf.multi_cell(0, 5.5, text)

            if translated:
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(*GRAY)
                pdf.multi_cell(0, 5, f"[{translated}]")

            pdf.ln(1)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
