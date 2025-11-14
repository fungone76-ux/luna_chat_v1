from __future__ import annotations
from PySide6 import QtWidgets

class Start1to1Dialog(QtWidgets.QDialog):
    def __init__(self, characters: list[str]):
        super().__init__()
        self.setWindowTitle("Nuova chat 1:1")
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel("Scegli con chi iniziare:"))
        self.cmb = QtWidgets.QComboBox(); self.cmb.addItems(characters); lay.addWidget(self.cmb)
        btns = QtWidgets.QHBoxLayout()
        ok = QtWidgets.QPushButton("OK"); ok.clicked.connect(self.accept)
        btns.addStretch(1); btns.addWidget(ok); lay.addLayout(btns)

    def selected(self) -> str:
        return self.cmb.currentText()
