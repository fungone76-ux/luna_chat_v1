# file: app/ui/widgets/participants_bar.py
from __future__ import annotations
from PySide6 import QtWidgets, QtGui, QtCore
from pathlib import Path
from typing import Optional

try:
    from app.core.models import AppState, Services
except ImportError:
    class AppState:
        pass


    class Services:
        pass


# --- MODIFICA: Nuovo widget per l'indicatore di stato d'animo ---
class MoodIndicator(QtWidgets.QWidget):
    """Disegna un cerchio colorato con il nome dello stato d'animo."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._mood_name = "..."
        self._color = QtGui.QColor("#9ca3af")  # Grigio di default
        self._diameter = 48  # Doppio dei 24px dell'avatar
        self.setFixedSize(self._diameter, self._diameter)
        self.setToolTip("Stato d'animo attuale del personaggio")

    def setMood(self, mood_name: str, color_hex: str):
        self._mood_name = mood_name.upper()
        self._color = QtGui.QColor(color_hex)
        self.update()  # Forza il ridisegno

    def paintEvent(self, event: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.rect()

        # Disegna il cerchio
        painter.setBrush(self._color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(rect)

        # Disegna il testo
        painter.setPen(QtGui.QColor("#ffffff"))  # Testo bianco
        font = painter.font()

        # Adatta dinamicamente la dimensione del font
        font_size = 9
        if len(self._mood_name) > 8:
            font_size = 7
        elif len(self._mood_name) > 6:
            font_size = 8

        font.setPointSizeF(font_size)
        font.setBold(True)
        painter.setFont(font)

        painter.drawText(rect, QtCore.Qt.AlignCenter, self._mood_name)


# --- FINE MODIFICA ---


class ParticipantsBar(QtWidgets.QWidget):
    inviteClicked = QtCore.Signal()
    removed = QtCore.Signal(str)
    affinityToggled = QtCore.Signal(bool)

    # --- MODIFICA: Accetta app_state e services ---
    def __init__(self, participants: list[str], base_dir: Path, app_state: Optional[AppState] = None,
                 services: Optional[Services] = None):
        super().__init__()
        self.base_dir = base_dir
        self.app_state = app_state
        self.services = services
        # --- FINE MODIFICA ---

        self._parts = participants[:] if participants else []

        # stato per la barra di affinità
        self._last_aff: float | None = None
        self._revert_timer = QtCore.QTimer(self)
        self._revert_timer.setSingleShot(True)
        self._revert_timer.timeout.connect(lambda: self._set_bar_color("#22c55e"))  # verde "default"

        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # toggle affinity
        self.chk_aff = QtWidgets.QCheckBox("Affinity")
        self.chk_aff.setChecked(True)
        self.chk_aff.toggled.connect(self.affinityToggled.emit)
        root.addWidget(self.chk_aff)

        # barra + numerino
        wrap = QtWidgets.QHBoxLayout()
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.setSpacing(6)
        holder = QtWidgets.QWidget()
        holder.setLayout(wrap)

        self.aff_bar = QtWidgets.QProgressBar()
        self.aff_bar.setRange(0, 100)
        self.aff_bar.setFixedWidth(140)
        self.aff_bar.setTextVisible(False)
        self.aff_bar.setVisible(False)
        self._set_bar_base_style()
        self._set_bar_color("#22c55e")  # verde base

        self.lbl_val = QtWidgets.QLabel("--")
        f = self.lbl_val.font();
        f.setFamily("Consolas, Courier New, monospace");
        f.setPointSizeF(f.pointSizeF() * 0.95)
        self.lbl_val.setFont(f)
        self.lbl_val.setFixedWidth(42)  # es. "0.00"
        self.lbl_val.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.lbl_val.setVisible(False)
        self.lbl_val.setToolTip("Affinity value (0..1)")

        wrap.addWidget(self.aff_bar)
        wrap.addWidget(self.lbl_val)
        root.addWidget(holder)

        root.addStretch(1)

        self._chips = QtWidgets.QHBoxLayout()
        self._chips.setContentsMargins(0, 0, 0, 0)
        self._chips.setSpacing(6)
        w = QtWidgets.QWidget();
        w.setLayout(self._chips)
        root.addWidget(w, 1)
        self._refresh_chips()

        plus = QtWidgets.QToolButton()
        plus.setText("+")
        plus.clicked.connect(self.inviteClicked.emit)
        root.addWidget(plus)

    # ---------- UI helpers ----------
    def _set_bar_base_style(self):
        # stile neutro; il colore della chunk viene impostato da _set_bar_color
        self.aff_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e0e5ee;
                border-radius: 6px;
                background: #f7f8fb;
                padding: 1px;
                height: 10px;
            }
            QProgressBar::chunk {
                border-radius: 5px;
                background-color: #22c55e; /* verde di default */
            }
        """)

    def _set_bar_color(self, color_hex: str):
        # cambia solo la chunk; lascia invariato il resto dello stile
        self.aff_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #e0e5ee;
                border-radius: 6px;
                background: #f7f8fb;
                padding: 1px;
                height: 10px;
            }}
            QProgressBar::chunk {{
                border-radius: 5px;
                background-color: {color_hex};
            }}
        """)

    # --- MODIFICA: Rimossa logica avatar ---
    # def _avatar_for(self, name: str) -> QtGui.QPixmap | None: ...
    # --- FINE MODIFICA ---

    def _refresh_chips(self):
        while self._chips.count():
            item = self._chips.takeAt(0)
            if w := item.widget():
                w.deleteLater()

        # Non fare nulla se i servizi non sono pronti
        if not self.app_state or not self.services or not self.services.characters:
            self._chips.addStretch(1)
            return

        for p_name in self._parts:
            chip = QtWidgets.QFrame();
            chip.setObjectName("Chip")
            chip.setStyleSheet("QFrame#Chip{border:1px solid #e0e5ee;border-radius:12px;background:#ffffff;}")
            h = QtWidgets.QHBoxLayout(chip);
            h.setContentsMargins(8, 2, 8, 2);
            h.setSpacing(6)

            # --- MODIFICA: Aggiungi il MoodIndicator invece dell'avatar ---

            # 1. Trova lo stato d'animo e il colore
            mood_name = "..."
            mood_color = "#9ca3af"  # Grigio

            try:
                # 2. Prendi tutti gli stati per questo personaggio
                all_moods = self.services.characters.get_mood_states(p_name, 0.0)  # Prendi tutti

                # 3. Trova lo stato attuale
                current_mood_name = self.app_state.chat_state.character_moods.get(p_name)

                # 4. Se non c'è, usa il primo della lista come default
                if not current_mood_name and all_moods:
                    current_mood_name = all_moods[0].get("name")

                # 5. Trova il colore per lo stato attuale
                if current_mood_name:
                    mood_name = current_mood_name
                    for mood_data in all_moods:
                        if mood_data.get("name") == current_mood_name:
                            mood_color = mood_data.get("color", "#9ca3af")
                            break
            except Exception as e:
                print(f"[WARN] Errore nel caricare mood per {p_name}: {e}")

            # 6. Crea e imposta il widget
            mood_widget = MoodIndicator()
            mood_widget.setMood(mood_name, mood_color)

            h.addWidget(mood_widget)
            # --- FINE MODIFICA ---

            h.addWidget(QtWidgets.QLabel(p_name))
            x = QtWidgets.QToolButton();
            x.setText("×");
            x.clicked.connect(lambda _, name=p_name: self.removed.emit(name));
            h.addWidget(x)
            self._chips.addWidget(chip)

        self._chips.addStretch(1)

    # ---------- Public API ----------
    def set_participants(self, parts: list[str]):
        """Aggiorna la lista dei partecipanti e ridisegna i chip."""
        self._parts = parts[:] if parts else []
        self._refresh_chips()  # Ridisegna i chip (e aggiorna gli stati d'animo)

    def set_affinity(self, value: float, enabled: bool, is_1to1: bool):
        """
        Aggiorna barra + numerino.
        - Verde quando cresce, Rosso quando cala (transitorio 1.2s), poi ritorna verde.
        - Se disabilitato o non 1:1, nasconde barra e numero.
        """
        self.chk_aff.setChecked(enabled)
        show = bool(enabled and is_1to1)
        self.aff_bar.setVisible(show)
        self.lbl_val.setVisible(show)
        if not show:
            return

        # clampa e aggiorna
        v = 0.0 if value is None else max(0.0, min(1.0, float(value)))
        self.aff_bar.setValue(int(v * 100))
        self.lbl_val.setText(f"{v:.2f}")

        # decidi colore in base alla variazione
        changed = False
        if self._last_aff is not None:
            eps = 0.005
            if v > self._last_aff + eps:
                # up → verde vivo
                self._set_bar_color("#16a34a")  # green-600
                changed = True
            elif v < self._last_aff - eps:
                # down → rosso
                self._set_bar_color("#ef4444")  # red-500
                changed = True
        else:
            # prima volta: imposta verde base
            self._set_bar_color("#22c55e")

        self._last_aff = v

        # se il colore è cambiato, dopo 1.2s torna al verde base
        if changed:
            self._revert_timer.start(1200)