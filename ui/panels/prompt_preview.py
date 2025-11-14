# app/ui/panels/prompt_preview.py
from __future__ import annotations
from PySide6 import QtWidgets, QtGui, QtCore
from pathlib import Path
import os

class ClickImg(QtWidgets.QLabel):
    clicked = QtCore.Signal()
    def mousePressEvent(self, e: QtGui.QMouseEvent):
        self.clicked.emit()
        super().mousePressEvent(e)

class PromptPreview(QtWidgets.QWidget):
    """
    Pannello anteprima: mostra prompt positivo (e negativo opzionale) + thumbnail immagine.
    Al click sulla thumbnail emette imageOpenRequested(path_assoluto).
    """
    imageOpenRequested = QtCore.Signal(str)

    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = Path(base_dir)
        self._image_abs: Path | None = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        title = QtWidgets.QLabel("Anteprima (clic per aprire)")
        title.setObjectName("Hint")
        layout.addWidget(title)

        self.img = ClickImg()
        self.img.setMinimumSize(260, 160)
        self.img.setAlignment(QtCore.Qt.AlignCenter)
        self.img.setScaledContents(False)  # gestiamo noi lo scaling
        self.img.setStyleSheet("background:#ffffff;border:1px solid #e6eaf2;border-radius:8px;")
        layout.addWidget(self.img, 0)

        prompt_lbl = QtWidgets.QLabel("Prompt SD (positivo):")
        prompt_lbl.setObjectName("Hint")
        layout.addWidget(prompt_lbl)

        self.txt = QtWidgets.QPlainTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setMinimumHeight(280)
        layout.addWidget(self.txt, 1)

        # Negativo opzionale (se vuoi usarlo da main.py)
        self._neg = None  # creato on-demand

        # Signals
        self.img.clicked.connect(self._open)

    # --------- API pubblica ----------
    def set_text(self, s: str | None):
        self.txt.setPlainText(s or "")

    def set_negative_text(self, s: str | None):
        if self._neg is None:
            lbl = QtWidgets.QLabel("Prompt SD (negativo):")
            lbl.setObjectName("Hint")
            self.layout().addWidget(lbl)
            self._neg = QtWidgets.QPlainTextEdit()
            self._neg.setReadOnly(True)
            self._neg.setMinimumHeight(140)
            self.layout().addWidget(self._neg)
        self._neg.setPlainText(s or "")

    def set_image(self, path: str | None):
        """
        Accetta path assoluto o relativo alla base_dir.
        Aggiorna la thumbnail; se il file non esiste, pulisce la preview.
        """
        self._image_abs = None
        if not path:
            self.img.setPixmap(QtGui.QPixmap())
            return

        p = Path(path)
        if not p.is_absolute():
            p = (self.base_dir / p).resolve()

        if p.exists():
            self._image_abs = p
            self._update_thumbnail()
        else:
            self.img.setPixmap(QtGui.QPixmap())

    # --------- Interni ----------
    def _update_thumbnail(self):
        if not self._image_abs:
            self.img.setPixmap(QtGui.QPixmap())
            return
        pm = QtGui.QPixmap(str(self._image_abs))
        if pm.isNull():
            self.img.setPixmap(QtGui.QPixmap())
            return
        # fit inside label while keeping aspect ratio
        target = self.img.size()
        scaled = pm.scaled(target, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.img.setPixmap(scaled)

    def resizeEvent(self, e: QtGui.QResizeEvent):
        super().resizeEvent(e)
        self._update_thumbnail()

    def _open(self):
        if self._image_abs:
            # Niente webbrowser/as_uri: emettiamo un segnale e lascia che MainWindow apra il viewer
            self.imageOpenRequested.emit(str(self._image_abs))
