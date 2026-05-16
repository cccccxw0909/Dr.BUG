"""PDF report generation."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

logger = logging.getLogger(__name__)


def build_pdf(
    run_dir: Path,
    data_quality_report: Dict[str, Any],
    leakage_report: Dict[str, Any],
    importance_ranking: Dict[str, List[tuple]],
    candidate_sets: List[List[str]],
    cv_results: Dict[str, Any],
    final_features: List[str],
    doctor_history: List[Dict[str, Any]],
    feature_stability: Optional[Dict[str, Dict[str, float]]] = None,
) -> Path:
    """Generate PDF report using reportlab."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak, Image as RLImage
    except ImportError as e:
        logger.warning("reportlab not available: %s. Skipping PDF.", e)
        return Path(run_dir) / "report.pdf"

    path = Path(run_dir) / "report.pdf"
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        title="Training Report",
    )
    styles = getSampleStyleSheet()
    
    # Set Times New Roman font for all styles
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    
    # Use Times-Roman (built-in font that closely matches Times New Roman)
    font_name = 'Times-Roman'
    
    # Try to register Times New Roman TTF if available (optional enhancement)
    try:
        import platform
        if platform.system() == 'Windows':
            # Common Windows font paths
            font_paths = [
                'C:/Windows/Fonts/times.ttf',
                'C:/Windows/Fonts/timesi.ttf',
                'C:/Windows/Fonts/timesbd.ttf',
            ]
            for font_path in font_paths:
                if Path(font_path).exists():
                    pdfmetrics.registerFont(TTFont('TimesNewRoman', font_path))
                    font_name = 'TimesNewRoman'
                    break
    except Exception:
        pass  # Fallback to Times-Roman
    
    # Update styles to use Times New Roman / Times-Roman
    for style_name in ['Title', 'Heading1', 'Heading2', 'Heading3', 'Normal']:
        if style_name in styles:
            styles[style_name].fontName = font_name
    
    story = []

    # Title (training pipeline artifact — not single-sample prediction)
    story.append(Paragraph("Training Report", styles["Title"]))
    story.append(Spacer(1, 0.5 * cm))

    # Data quality
    story.append(Paragraph("1. Data Quality", styles["Heading2"]))
    dq = data_quality_report
    story.append(Paragraph(f"Rows: {dq.get('n_rows', 'N/A')}, Cols: {dq.get('n_cols', 'N/A')}", styles["Normal"]))
    missing_summary = dq.get("missing_summary") or {}
    if isinstance(missing_summary, dict) and missing_summary:
        story.append(Paragraph("Missing rate: proportion of missing values per column (0 = none, 1 = all missing). Columns with missing &gt; 0:", styles["Normal"]))
        data = [["Feature", "Missing rate"]]
        for feat, rate in sorted(missing_summary.items(), key=lambda x: -x[1]):
            data.append([str(feat), f"{float(rate):.2%}"])
        t_miss = Table(data)
        t_miss.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ]))
        story.append(t_miss)
    else:
        story.append(Paragraph("Missing rate: proportion of missing values per column. No missing values reported.", styles["Normal"]))
    story.append(Spacer(1, 0.3 * cm))

    # Leakage
    story.append(Paragraph("2. Leakage Check", styles["Heading2"]))
    story.append(Paragraph(f"Suspected: {leakage_report.get('suspected_columns', [])}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * cm))

    # Variable Importance (per-model: one table per model, all models shown)
    story.append(Paragraph("3. Variable Importance (Top 10)", styles["Heading2"]))
    story.append(Paragraph("Note: Statistical importance indicates contribution to prediction, not clinical causality.", styles["Normal"]))
    story.append(Spacer(1, 0.2 * cm))
    if importance_ranking:
        for model_name, ranking in importance_ranking.items():
            story.append(Paragraph(model_name, styles["Heading3"]))
            top = (ranking or [])[:10]
            data = [["Feature", "Importance"]] + [[str(a), f"{float(b):.4f}"] for a, b in top]
            t = Table(data)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.2 * cm))
    story.append(Spacer(1, 0.2 * cm))

    # Candidate sets
    story.append(Paragraph("4. Candidate Feature Sets", styles["Heading2"]))
    for i, s in enumerate(candidate_sets[:5], 1):
        story.append(Paragraph(f"Set {i}: {', '.join(s[:8])}{'...' if len(s) > 8 else ''}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * cm))

    # Final features
    story.append(Paragraph("5. Final Selected Features", styles["Heading2"]))
    story.append(Paragraph(", ".join(final_features[:20]) + ("..." if len(final_features) > 20 else ""), styles["Normal"]))
    story.append(Spacer(1, 0.3 * cm))

    # CV results: rows = metrics, columns = models; show all models
    story.append(Paragraph("6. Model Performance", styles["Heading2"]))
    if cv_results:
        model_names = [k for k in cv_results.keys() if isinstance(cv_results.get(k), dict)]
        metric_order = ["Accuracy", "Precision", "Recall", "F1-score", "AUROC", "AUPRC"]
        header = ["Metric"] + model_names
        data = [header]
        for m in metric_order:
            row = [str(m)]
            for model_name in model_names:
                val = (cv_results.get(model_name) or {}).get(m)
                if isinstance(val, dict):
                    mean_val = val.get("mean", 0)
                    std_val = val.get("std", 0)
                    row.append(f"{mean_val:.4f} ± {std_val:.4f}")
                elif val is not None:
                    row.append(str(val))
                else:
                    row.append("—")
            data.append(row)
        t_cv = Table(data)
        t_cv.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ]))
        story.append(t_cv)
    story.append(Spacer(1, 0.3 * cm))
    
    # Decision Trajectory
    story.append(Paragraph("7. Decision Trajectory", styles["Heading2"]))
    story.append(Paragraph("This section records the decision-making process: AI recommendations, doctor modifications, and system alerts.", styles["Normal"]))
    story.append(Spacer(1, 0.2 * cm))
    
    if doctor_history:
        for i, entry in enumerate(doctor_history, 1):
            story.append(Paragraph(f"Step {i}:", styles["Heading3"]))
            selected = entry.get("selected", [])
            story.append(Paragraph(f"Selected features ({len(selected)}): {', '.join(selected[:10])}{'...' if len(selected) > 10 else ''}", styles["Normal"]))
            
            warnings = entry.get("warnings", [])
            if warnings:
                story.append(Paragraph("Warnings:", styles["Normal"]))
                for warning in warnings:
                    msg = warning.get("message", "")
                    severity = warning.get("severity", "unknown")
                    story.append(Paragraph(f"  [{severity.upper()}] {msg}", styles["Normal"]))
                ignored = entry.get("ignored", False)
                if ignored:
                    story.append(Paragraph("  → Warnings were ignored", styles["Normal"]))
            story.append(Spacer(1, 0.2 * cm))
    else:
        story.append(Paragraph("No decision history recorded.", styles["Normal"]))
    story.append(Spacer(1, 0.3 * cm))
    
    # Feature Stability Distribution
    if feature_stability:
        story.append(Paragraph("8. Feature Stability Distribution", styles["Heading2"]))
        story.append(Paragraph("Feature stability scores (frequency of entering top 10 across CV folds) are shown below.", styles["Normal"]))
        story.append(Spacer(1, 0.2 * cm))
        
        # Create stability table for each model
        for model_name, stability_dict in list(feature_stability.items())[:3]:
            if not stability_dict:
                continue
            story.append(Paragraph(f"{model_name} Feature Stability", styles["Heading3"]))
            
            # Sort by stability score
            sorted_stability = sorted(stability_dict.items(), key=lambda x: x[1], reverse=True)[:15]
            data = [["Feature", "Stability Score"]] + [[feat, f"{score:.2%}"] for feat, score in sorted_stability]
            t = Table(data)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.2 * cm))
        
        # Feature Stability Boxplot (if matplotlib is available)
        if HAS_MATPLOTLIB and feature_stability:
            try:
                # Collect stability scores across all models for boxplot
                all_stability_scores = []
                model_labels = []
                feature_labels = []
                
                for model_name, stability_dict in list(feature_stability.items())[:5]:  # Limit to 5 models
                    if not stability_dict:
                        continue
                    scores = list(stability_dict.values())
                    all_stability_scores.extend(scores)
                    model_labels.extend([model_name] * len(scores))
                    feature_labels.extend(list(stability_dict.keys()))
                
                if all_stability_scores:
                    # Create boxplot
                    fig, ax = plt.subplots(figsize=(8, 5))
                    ax.boxplot([all_stability_scores], labels=['All Models'])
                    ax.set_ylabel('Stability Score (Frequency)')
                    ax.set_title('Feature Stability Distribution Across Models')
                    ax.grid(True, alpha=0.3)
                    
                    # Save to buffer
                    img_buffer = io.BytesIO()
                    fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
                    img_buffer.seek(0)
                    plt.close(fig)
                    
                    # Add image to PDF: use platypus.Image (a Flowable). ImageReader is only a pixel source;
                    # appending ImageReader directly to story would miss Flowable APIs such as getKeepWithNext during layout.
                    try:
                        from reportlab.lib.utils import ImageReader

                        story.append(Spacer(1, 0.2 * cm))
                        ir = ImageReader(img_buffer)
                        story.append(RLImage(ir, width=14 * cm))
                    except Exception as e:
                        logger.warning(f"Failed to add stability boxplot to PDF: {e}")
            except Exception as e:
                logger.warning(f"Failed to generate stability boxplot: {e}")
        
        story.append(Paragraph("Note: Stability scores represent the frequency (0-100%) of features entering the top 10 across cross-validation folds.", styles["Normal"]))

    # Add footer to all pages
    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font_name, 9)
        footer_text = "This analysis adheres to temporal logic audit standards."
        text_width = canvas.stringWidth(footer_text, font_name, 9)
        page_width = A4[0]
        canvas.drawString((page_width - text_width) / 2, 2 * cm, footer_text)
        canvas.restoreState()
    
    try:
        doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    except Exception as e:
        logger.warning(f"Failed to add footer to PDF: {e}. Building without footer.")
        doc.build(story)
    return path
