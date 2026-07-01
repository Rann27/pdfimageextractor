#!/usr/bin/env python3
"""PDF Image Extractor — Modern Glassy Desktop App"""

import sys
import os
import math
import subprocess
import zipfile
from pathlib import Path

import fitz  # PyMuPDF

_EPUB_IMG_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".bmp", ".svg"}

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QProgressBar, QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFileDialog, QMessageBox, QSizePolicy,
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QRect, QPoint, QPointF, QSize,
)
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient,
    QPalette, QPixmap, QIcon, QFont,
)


# ─── Worker Thread ────────────────────────────────────────────────────────────

class ExtractWorker(QThread):
    progress = pyqtSignal(int, int)   # page_done, total_pages
    found    = pyqtSignal(str)        # path of saved image
    done     = pyqtSignal(int, str)   # total_count, output_folder
    failed   = pyqtSignal(str)        # error message

    def __init__(self, pdf_path: str):
        super().__init__()
        self.pdf_path = pdf_path

    def run(self):
        try:
            ext = Path(self.pdf_path).suffix.lower()
            if ext == ".epub":
                self._extract_epub()
            else:
                self._extract_pdf()
        except Exception as exc:
            self.failed.emit(str(exc))

    def _extract_pdf(self):
        p = Path(self.pdf_path)
        out = p.parent / p.stem
        out.mkdir(exist_ok=True)

        doc = fitz.open(str(p))
        total = len(doc)
        seen = set()
        count = 0

        for pno in range(total):
            self.progress.emit(pno + 1, total)
            for img in doc[pno].get_images(full=True):
                xref = img[0]
                if xref in seen:
                    continue
                seen.add(xref)
                data = doc.extract_image(xref)
                fname = out / f"p{pno + 1:03d}_{count + 1:04d}.{data['ext']}"
                fname.write_bytes(data["image"])
                count += 1
                self.found.emit(str(fname))

        doc.close()
        self.done.emit(count, str(out))

    def _extract_epub(self):
        p = Path(self.pdf_path)
        out = p.parent / p.stem
        out.mkdir(exist_ok=True)

        with zipfile.ZipFile(str(p), "r") as z:
            img_entries = [
                name for name in z.namelist()
                if Path(name).suffix.lower() in _EPUB_IMG_EXTS
            ]
            total = len(img_entries)
            count = 0

            for i, name in enumerate(img_entries):
                self.progress.emit(i + 1, total)
                suffix = Path(name).suffix.lower()
                fname = out / f"img_{count + 1:04d}{suffix}"
                fname.write_bytes(z.read(name))
                count += 1
                self.found.emit(str(fname))

        self.done.emit(count, str(out))


# ─── Responsive 5-Column Thumbnail Grid ──────────────────────────────────────

class ThumbGrid(QWidget):
    """5-column grid that recalculates cell sizes when the widget is resized."""
    COLS = 5
    GAP  = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._cards: list = []
        self._grid = QGridLayout(self)
        self._grid.setSpacing(self.GAP)
        self._grid.setContentsMargins(4, 4, 4, 4)

    def add_card(self, img_path: str, index: int):
        card = ThumbCard(img_path, index)
        row = (index - 1) // self.COLS
        col = (index - 1) % self.COLS
        self._grid.addWidget(card, row, col)
        self._cards.append(card)
        self._resize_cards()

    def clear_all(self):
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()

    def _resize_cards(self):
        vw = self.width()
        if vw < 10:
            return
        m = self._grid.contentsMargins()
        avail = vw - m.left() - m.right() - (self.COLS - 1) * self.GAP
        cell_w = max(80, avail // self.COLS)
        cell_h = int(cell_w * 1.35)
        for card in self._cards:
            card.setFixedSize(cell_w, cell_h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_cards()


# ─── Thumbnail Card ───────────────────────────────────────────────────────────

class ThumbCard(QFrame):
    def __init__(self, img_path: str, index: int, parent=None):
        super().__init__(parent)
        self.setObjectName("thumbCard")
        self._pix = QPixmap(img_path)   # keep original; scale on every resize

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 6)
        lay.setSpacing(4)

        self.img_lbl = QLabel()
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_lbl.setStyleSheet("background: transparent; border: none;")

        self.num_lbl = QLabel(f"#{index}")
        self.num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.num_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.35); font-size: 10px; "
            "background: transparent; border: none;"
        )

        lay.addWidget(self.img_lbl, 1)
        lay.addWidget(self.num_lbl, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_pixmap()

    def _refresh_pixmap(self):
        if self._pix.isNull():
            return
        w = max(1, self.width() - 16)
        h = max(1, self.height() - 26)
        self.img_lbl.setPixmap(
            self._pix.scaled(w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
        )

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(0, 0, -1, -1)
        p.setBrush(QColor(255, 255, 255, 12))
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.drawRoundedRect(r, 10, 10)


# ─── Drop Zone ────────────────────────────────────────────────────────────────

class DropZone(QFrame):
    dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(280)
        self._hover = False
        self._t = 0

        anim = QTimer(self)
        anim.timeout.connect(self._tick)
        anim.start(40)

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(16)

        self.icon_lbl = QLabel("🗂")
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setStyleSheet(
            "font-size: 56px; background: transparent; border: none;"
        )

        self.title_lbl = QLabel("Drop your PDF here")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_lbl.setStyleSheet(
            "font-size: 26px; font-weight: 700; color: white; "
            "background: transparent; border: none;"
        )

        self.sub_lbl = QLabel("or click anywhere to browse")
        self.sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_lbl.setStyleSheet(
            "font-size: 13px; color: rgba(255,255,255,0.40); "
            "background: transparent; border: none;"
        )

        self.hint_lbl = QLabel("Supports PDF & EPUB  ·  Extracts JPG, PNG, TIFF, WebP, …")
        self.hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_lbl.setStyleSheet(
            "font-size: 11px; color: rgba(255,255,255,0.20); "
            "background: transparent; border: none;"
        )

        for w in (self.icon_lbl, self.title_lbl, self.sub_lbl, self.hint_lbl):
            lay.addWidget(w)

    # ── animation ──────────────────────────────────────────────────────────

    def _tick(self):
        self._t += 1
        self.update()

    # ── drag events ────────────────────────────────────────────────────────

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(
            u.toLocalFile().lower().endswith((".pdf", ".epub"))
            for u in e.mimeData().urls()
        ):
            e.acceptProposedAction()
            self._hover = True
            self.update()

    def dragLeaveEvent(self, _):
        self._hover = False
        self.update()

    def dropEvent(self, e):
        self._hover = False
        for u in e.mimeData().urls():
            path = u.toLocalFile()
            if path.lower().endswith((".pdf", ".epub")):
                self.dropped.emit(path)
                break
        self.update()

    # ── click to browse ────────────────────────────────────────────────────

    def enterEvent(self, _):
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def leaveEvent(self, _):
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            path, _ = QFileDialog.getOpenFileName(
                self, "Select File", "",
                "Supported Files (*.pdf *.epub);;PDF Files (*.pdf);;EPUB Files (*.epub)"
            )
            if path:
                self.dropped.emit(path)

    # ── paint ──────────────────────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()

        # Background fill
        bg_alpha = 35 if self._hover else 8
        bg_color = QColor(108, 99, 255, bg_alpha) if self._hover else QColor(255, 255, 255, bg_alpha)
        p.setBrush(bg_color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 22, 22)

        # Inner glow on hover
        if self._hover:
            glow = QRadialGradient(QPointF(r.center()), float(min(r.width(), r.height())) * 0.55)
            glow.setColorAt(0.0, QColor(108, 99, 255, 22))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(glow)
            p.drawRoundedRect(r, 22, 22)

        # Animated dashed border
        phase = self._t * 0.055
        pulse = int(55 + 38 * math.sin(phase))
        if self._hover:
            pen = QPen(QColor(108, 99, 255, 220), 2.0)
            pen.setStyle(Qt.PenStyle.SolidLine)
        else:
            pen = QPen(QColor(255, 255, 255, pulse), 1.5)
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setDashPattern([10.0, 5.0])

        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(2, 2, -2, -2), 22, 22)


# ─── Glass Panel helper ───────────────────────────────────────────────────────

def make_panel() -> QFrame:
    f = QFrame()
    f.setObjectName("glassPanel")
    f.setStyleSheet("""
        QFrame#glassPanel {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 16px;
        }
    """)
    return f


# ─── Main Window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Image Extractor")
        self.setMinimumSize(840, 660)
        self.resize(940, 740)
        self._worker: ExtractWorker | None = None
        self._found_count = 0
        self._output_folder = ""
        self._progress_unit = "pages"
        self._build_ui()
        self._apply_global_style()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self):
        root_widget = QWidget()
        self.setCentralWidget(root_widget)
        root = QVBoxLayout(root_widget)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(18)

        # ── Header ─────────────────────────────────────────────────────────
        hdr = QHBoxLayout()

        title = QLabel("PDF Image Extractor")
        title.setStyleSheet(
            "font-size: 21px; font-weight: 800; color: #8b7fff; "
            "background: transparent;"
        )
        tagline = QLabel("Extract every embedded image from your PDF — instantly")
        tagline.setStyleSheet(
            "font-size: 11px; color: rgba(255,255,255,0.35); "
            "background: transparent; margin-top: 3px;"
        )
        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title_col.addWidget(title)
        title_col.addWidget(tagline)

        badge = QLabel("v1.0  ·  PyMuPDF")
        badge.setStyleSheet(
            "color: rgba(255,255,255,0.30); font-size: 10px; "
            "background: rgba(255,255,255,0.06); border-radius: 8px; "
            "border: 1px solid rgba(255,255,255,0.08); padding: 3px 10px;"
        )

        hdr.addLayout(title_col)
        hdr.addStretch()
        hdr.addWidget(badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(hdr)

        # ── Drop Zone ───────────────────────────────────────────────────────
        self.drop_zone = DropZone()
        self.drop_zone.dropped.connect(self._on_file)
        root.addWidget(self.drop_zone, 1)

        # ── Progress Panel ──────────────────────────────────────────────────
        self.prog_panel = make_panel()
        self.prog_panel.hide()
        prog_lay = QVBoxLayout(self.prog_panel)
        prog_lay.setContentsMargins(22, 18, 22, 18)
        prog_lay.setSpacing(10)

        ph = QHBoxLayout()
        self.proc_lbl = QLabel("Processing…")
        self.proc_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: white; "
            "background: transparent; border: none;"
        )
        self.page_lbl = QLabel("0 / 0 pages")
        self.page_lbl.setStyleSheet(
            "font-size: 12px; color: rgba(255,255,255,0.45); "
            "background: transparent; border: none;"
        )
        ph.addWidget(self.proc_lbl)
        ph.addStretch()
        ph.addWidget(self.page_lbl)

        self.prog_bar = QProgressBar()
        self.prog_bar.setTextVisible(False)
        self.prog_bar.setFixedHeight(7)
        self.prog_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255,255,255,0.08);
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #6c63ff, stop:1 #00d4ff);
                border-radius: 3px;
            }
        """)

        self.found_lbl = QLabel("Images found: 0")
        self.found_lbl.setStyleSheet(
            "font-size: 12px; color: rgba(255,255,255,0.45); "
            "background: transparent; border: none;"
        )

        prog_lay.addLayout(ph)
        prog_lay.addWidget(self.prog_bar)
        prog_lay.addWidget(self.found_lbl)
        root.addWidget(self.prog_panel, 1)

        # ── Results Panel ───────────────────────────────────────────────────
        self.res_panel = make_panel()
        self.res_panel.hide()
        res_lay = QVBoxLayout(self.res_panel)
        res_lay.setContentsMargins(22, 18, 22, 18)
        res_lay.setSpacing(12)

        # results header
        rh = QHBoxLayout()
        self.res_title = QLabel("Extracted Images")
        self.res_title.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: white; "
            "background: transparent; border: none;"
        )

        self.btn_folder = QPushButton("📂  Open Folder")
        self.btn_new    = QPushButton("↩  New File")
        for btn in (self.btn_folder, self.btn_new):
            btn.setFixedHeight(34)
        self.btn_folder.clicked.connect(self._open_folder)
        self.btn_new.clicked.connect(self._reset)

        rh.addWidget(self.res_title)
        rh.addStretch()
        rh.addWidget(self.btn_folder)
        rh.addWidget(self.btn_new)

        # thumbnail scroll area — expands to fill available space
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )

        self.grid = ThumbGrid()
        self.scroll.setWidget(self.grid)

        # status label
        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #00d4aa; "
            "background: transparent; border: none; padding: 6px;"
        )

        res_lay.addLayout(rh)
        res_lay.addWidget(self.scroll, 1)   # scroll takes all spare vertical space
        res_lay.addWidget(self.status_lbl)
        root.addWidget(self.res_panel, 1)

    def _apply_global_style(self):
        self.setStyleSheet("""
            QMainWindow { background: transparent; }
            QWidget { background: transparent; }

            QPushButton {
                background: rgba(108, 99, 255, 0.18);
                color: white;
                border: 1px solid rgba(108, 99, 255, 0.45);
                border-radius: 9px;
                font-size: 12px;
                font-weight: 600;
                padding: 4px 16px;
            }
            QPushButton:hover {
                background: rgba(108, 99, 255, 0.38);
                border-color: rgba(108, 99, 255, 0.80);
            }
            QPushButton:pressed {
                background: rgba(108, 99, 255, 0.55);
            }

            QScrollBar:vertical {
                width: 5px;
                background: rgba(255,255,255,0.04);
                border-radius: 2px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.18);
                border-radius: 2px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

    # ── Background painting (gradient + orbs) ─────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Deep dark base
        grad = QLinearGradient(0.0, 0.0, float(w), float(h))
        grad.setColorAt(0.0, QColor(7,  7, 18))
        grad.setColorAt(0.5, QColor(11, 9, 24))
        grad.setColorAt(1.0, QColor(7,  7, 18))
        p.fillRect(self.rect(), grad)

        # Purple orb — top-left
        o1 = QRadialGradient(QPointF(w * 0.12, h * 0.18), w * 0.28)
        o1.setColorAt(0.0, QColor(108, 99, 255, 28))
        o1.setColorAt(1.0, QColor(0,   0,   0,   0))
        p.fillRect(self.rect(), o1)

        # Cyan orb — bottom-right
        o2 = QRadialGradient(QPointF(w * 0.88, h * 0.82), w * 0.30)
        o2.setColorAt(0.0, QColor(0, 212, 255, 20))
        o2.setColorAt(1.0, QColor(0,   0,   0,  0))
        p.fillRect(self.rect(), o2)

        # Faint mid orb
        o3 = QRadialGradient(QPointF(w * 0.50, h * 0.50), w * 0.22)
        o3.setColorAt(0.0, QColor(80, 60, 180, 10))
        o3.setColorAt(1.0, QColor(0,   0,   0,  0))
        p.fillRect(self.rect(), o3)

    # ── Slots ──────────────────────────────────────────────────────────────

    def _on_file(self, path: str):
        """Start extraction when a file is dropped / selected."""
        self._progress_unit = "images" if path.lower().endswith(".epub") else "pages"

        self.res_panel.hide()
        self._clear_thumbs()
        self.drop_zone.hide()
        self.prog_panel.show()

        self._found_count = 0
        self.found_lbl.setText("Images found: 0")
        self.page_lbl.setText(f"0 / 0 {self._progress_unit}")
        self.proc_lbl.setText(f"Processing:  {Path(path).name}")
        self.prog_bar.setValue(0)

        self._worker = ExtractWorker(path)
        self._worker.progress.connect(self._on_progress)
        self._worker.found.connect(self._on_found)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int):
        self.prog_bar.setMaximum(total)
        self.prog_bar.setValue(current)
        self.page_lbl.setText(f"{current} / {total} {self._progress_unit}")

    def _on_found(self, img_path: str):
        self._found_count += 1
        self.found_lbl.setText(f"Images found: {self._found_count}")
        if self._found_count <= 100:        # cap thumbnails for performance
            self.grid.add_card(img_path, self._found_count)

    def _on_done(self, count: int, folder: str):
        self._output_folder = folder
        self.prog_panel.hide()
        self.res_panel.show()
        self.res_title.setText(f"Extracted Images  ({count})")

        if count == 0:
            self.status_lbl.setText("No embedded images found in this PDF.")
            self.status_lbl.setStyleSheet(
                "font-size: 13px; color: #ff4757; "
                "background: transparent; border: none; padding: 6px;"
            )
        else:
            noun = "image" if count == 1 else "images"
            self.status_lbl.setText(f"✓   {count} {noun} extracted successfully!")
            self.status_lbl.setStyleSheet(
                "font-size: 13px; font-weight: 600; color: #00d4aa; "
                "background: transparent; border: none; padding: 6px;"
            )

    def _on_error(self, msg: str):
        self.prog_panel.hide()
        self.drop_zone.show()
        QMessageBox.critical(self, "Extraction Error", f"Failed to process PDF:\n\n{msg}")

    def _open_folder(self):
        if self._output_folder and os.path.exists(self._output_folder):
            if sys.platform == "win32":
                os.startfile(self._output_folder)
            elif sys.platform == "darwin":
                subprocess.run(["open", self._output_folder])
            else:
                subprocess.run(["xdg-open", self._output_folder])

    def _reset(self):
        self._clear_thumbs()
        self._output_folder = ""
        self.res_panel.hide()
        self.drop_zone.show()

    def _clear_thumbs(self):
        self.grid.clear_all()
        self._found_count = 0


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PDF Image Extractor")
    app.setStyle("Fusion")

    palette = QPalette()
    dark = QColor(8, 8, 18)
    palette.setColor(QPalette.ColorRole.Window,          dark)
    palette.setColor(QPalette.ColorRole.WindowText,      Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base,            QColor(14, 14, 28))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(20, 18, 38))
    palette.setColor(QPalette.ColorRole.Text,            Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button,          QColor(28, 26, 50))
    palette.setColor(QPalette.ColorRole.ButtonText,      Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(108, 99, 255))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    app.setPalette(palette)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
