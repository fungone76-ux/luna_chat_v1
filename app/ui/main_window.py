# file: app/ui/main_window.py

from pathlib import Path
from typing import Optional, Any

from PySide6 import QtWidgets, QtCore, QtGui

from ui.widgets.chat_view import ChatView, ImageViewerDialog
from ui.widgets.participants_bar import ParticipantsBar
from ui.panels.prompt_preview import PromptPreview

from app.chat.engine import ChatEngine
from app.images.engine import ImageEngine, ImagePrompts
from app.images.gate import decide_image_request
from app.services.llm_client import LLMReply
from app.services.sd_client import SDClient


# ---------------------- WORKER THREADS ----------------------


class LLMWorker(QtCore.QObject):
    """
    Worker che chiama ChatEngine.process_user_message in un thread separato.
    """
    finished = QtCore.Signal(object, object)  # new_session, reply
    error = QtCore.Signal(str)

    def __init__(
        self,
        chat_engine: ChatEngine,
        session: Any,
        user_text: str,
        parent: Optional[QtCore.QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._chat_engine = chat_engine
        self._session = session
        self._user_text = user_text

    @QtCore.Slot()
    def run(self) -> None:
        try:
            new_session, reply = self._chat_engine.process_user_message(
                self._session, self._user_text
            )
            self.finished.emit(new_session, reply)
        except Exception as e:
            self.error.emit(str(e))


class SDWorker(QtCore.QObject):
    """
    Worker che chiama SDClient.txt2img in un thread separato.
    """
    finished = QtCore.Signal(dict)   # result dict
    error = QtCore.Signal(str)

    def __init__(
        self,
        sd_client: SDClient,
        positive_prompt: str,
        negative_prompt: str,
        parent: Optional[QtCore.QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._sd_client = sd_client
        self._positive = positive_prompt
        self._negative = negative_prompt

    @QtCore.Slot()
    def run(self) -> None:
        try:
            result = self._sd_client.txt2img(self._positive, self._negative)
            err = result.get("error") or ""
            if err:
                self.error.emit(err)
            else:
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ---------------------- MAIN WINDOW ----------------------


class MainWindow(QtWidgets.QMainWindow):
    """
    Finestra principale 1:1 (con LLM e SD in thread, GUI non bloccata):
    - ParticipantsBar in alto
    - ChatView a sinistra (molto ampia, rapporto fisso)
    - PromptPreview a destra (più stretta, rapporto fisso)
    - Barra di input in basso
    - Status bar in fondo con stato operazione
    """

    def __init__(
        self,
        chat_engine: ChatEngine,
        image_engine: ImageEngine,
        sd_client: SDClient,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.chat_engine = chat_engine
        self.image_engine = image_engine
        self.sd_client = sd_client

        # root del progetto (…/luna_chat_v1)
        self._root_dir = Path(__file__).resolve().parents[2]

        # Sessione 1:1 con il personaggio di default
        self._session = self.chat_engine.start_session("ui-session-1")
        self._character_name = getattr(self._session, "character_name", "Luna")

        self._last_user_text: str = ""
        self._busy: bool = False
        self._geometry_locked: bool = False  # blocco geometria dopo il primo show

        # thread in uso (solo per tenere un riferimento)
        self._llm_thread: Optional[QtCore.QThread] = None
        self._sd_thread: Optional[QtCore.QThread] = None

        self._build_ui()
        self._connect_signals()
        self._init_participants_bar()

        # Focus iniziale sulla barra input
        self.txt_input.setFocus(QtCore.Qt.OtherFocusReason)

    # ----------------- Lock geometria -----------------

    def showEvent(self, event: QtGui.QShowEvent) -> None:  # type: ignore[name-defined]
        """
        Alla prima visualizzazione:
        - ci assicuriamo che la finestra sia massimizzata
        - blocchiamo la dimensione minima all'attuale size (schermo pieno)
        Così, anche se i widget interni cambiano sizeHint, la finestra non si restringe.
        """
        super().showEvent(event)
        if not self._geometry_locked:
            self._geometry_locked = True
            # se non è già massimizzata, massimizza
            if not self.isMaximized():
                self.setWindowState(self.windowState() | QtCore.Qt.WindowMaximized)
            # blocca la dimensione minima alla dimensione attuale
            current_size = self.size()
            self.setMinimumSize(current_size)

    # ----------------- UI setup -----------------

    def _build_ui(self) -> None:
        self.setWindowTitle(f"Luna Chat v1 — 1:1 con {self._character_name}")
        # Dimensione di base (prima della massimizzazione)
        self.resize(1200, 780)

        central = QtWidgets.QWidget(self)
        root_layout = QtWidgets.QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        # Barra partecipanti in alto
        self.participants_bar = ParticipantsBar(
            participants=[self._character_name],
            base_dir=self._root_dir,
            app_state=None,
            services=None,
        )
        root_layout.addWidget(self.participants_bar, 0)

        # Pannello centrale con layout fisso chat / preview
        center_widget = QtWidgets.QWidget(central)
        center_layout = QtWidgets.QHBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)

        # ChatView molto più larga (stretch 4)
        self.chat_view = ChatView(base_dir=self._root_dir, app_state=None)
        center_layout.addWidget(self.chat_view, 4)

        # PromptPreview più stretto (stretch 1) e larghezza limitata
        self.prompt_preview = PromptPreview(base_dir=self._root_dir)
        self.prompt_preview.setMinimumWidth(260)
        self.prompt_preview.setMaximumWidth(380)
        center_layout.addWidget(self.prompt_preview, 1)

        root_layout.addWidget(center_widget, 1)

        # Barra di input in basso
        bottom = QtWidgets.QHBoxLayout()
        bottom.setContentsMargins(0, 4, 0, 0)
        bottom.setSpacing(6)

        self.txt_input = QtWidgets.QLineEdit()
        self.txt_input.setPlaceholderText("Scrivi qualcosa per Luna…")
        self.btn_send = QtWidgets.QPushButton("Invia")

        bottom.addWidget(self.txt_input, 1)
        bottom.addWidget(self.btn_send, 0)

        root_layout.addLayout(bottom)

        self.setCentralWidget(central)

        # Status bar (stato + “busy”)
        sb = self.statusBar()
        self._status_label = QtWidgets.QLabel("Pronto.")
        self._status_progress = QtWidgets.QProgressBar()
        self._status_progress.setMaximumWidth(180)
        self._status_progress.setTextVisible(False)
        self._status_progress.hide()  # mostrata solo quando occupato

        sb.addPermanentWidget(self._status_label, 1)
        sb.addPermanentWidget(self._status_progress, 0)

    def _connect_signals(self) -> None:
        self.btn_send.clicked.connect(self._on_send_clicked)
        self.txt_input.returnPressed.connect(self._on_send_clicked)

        # click sulle immagini nella chat
        self.chat_view.openImageRequested.connect(self._open_image_viewer)
        # click sulla thumbnail nel pannello prompt
        self.prompt_preview.imageOpenRequested.connect(self._open_image_viewer)

    def _init_participants_bar(self) -> None:
        # Per ora: 1:1 con il personaggio principale, niente affinità dinamica
        self.participants_bar.set_participants([self._character_name])
        self.participants_bar.set_affinity(0.0, enabled=False, is_1to1=True)

    # ----------------- Helpers stato -----------------

    def _set_busy(self, text: str) -> None:
        """Mostra stato occupato con barra indeterminata."""
        self._busy = True
        self._status_label.setText(text)
        self._status_progress.show()
        self._status_progress.setRange(0, 0)  # indeterminato
        self.txt_input.setEnabled(False)
        self.btn_send.setEnabled(False)
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents)

    def _set_idle(self) -> None:
        self._busy = False
        self._status_label.setText("Pronto.")
        self._status_progress.hide()
        self._status_progress.setRange(0, 100)
        self._status_progress.setValue(0)
        self.txt_input.setEnabled(True)
        self.btn_send.setEnabled(True)

        # focus automatico sulla barra di input
        self.txt_input.setFocus(QtCore.Qt.OtherFocusReason)

        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents)

    # ----------------- Slot UI -----------------

    def _on_send_clicked(self) -> None:
        if self._busy:
            return

        text = self.txt_input.text().strip()
        if not text:
            return

        self._last_user_text = text

        # mostra subito la bolla dell'utente
        self.chat_view.add_bubble(text, who="Tu", is_user=True)
        self.txt_input.clear()

        # avvia il worker per il LLM in background
        self._start_llm_worker(text)

    # ----------------- LLM async -----------------

    def _start_llm_worker(self, user_text: str) -> None:
        """Crea un QThread e un LLMWorker per eseguire il modello in background."""
        self._set_busy(f"{self._character_name} sta scrivendo…")

        llm_thread = QtCore.QThread(self)
        worker = LLMWorker(self.chat_engine, self._session, user_text)

        worker.moveToThread(llm_thread)

        llm_thread.started.connect(worker.run)
        worker.finished.connect(self._on_llm_finished)
        worker.error.connect(self._on_llm_error)

        # cleanup thread/worker
        worker.finished.connect(llm_thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(llm_thread.quit)
        worker.error.connect(worker.deleteLater)
        llm_thread.finished.connect(llm_thread.deleteLater)

        self._llm_thread = llm_thread
        llm_thread.start()

    @QtCore.Slot(object, object)
    def _on_llm_finished(self, new_session: Any, reply: Any) -> None:
        """Chiamata sul thread UI quando il worker LLM ha finito."""
        self._session = new_session

        if isinstance(reply, LLMReply):
            reply_text = reply.reply_it
        else:
            reply_text = str(getattr(reply, "reply_it", reply))

        # bolla del personaggio
        self.chat_view.add_bubble(
            reply_text,
            who=self._character_name,
            is_user=False,
        )

        # decide se generare immagine
        if isinstance(reply, LLMReply):
            decision = decide_image_request(self._last_user_text, reply)
        else:
            decision = type("D", (), {"will_generate": False})()

        if getattr(decision, "will_generate", False):
            prompts = self.image_engine.build_prompts(self._character_name, reply)
            self._start_sd_worker(prompts)
        else:
            self._set_idle()

    @QtCore.Slot(str)
    def _on_llm_error(self, message: str) -> None:
        QtWidgets.QMessageBox.warning(self, "Errore LLM", message)
        self._set_idle()

    # ----------------- SD async -----------------

    def _start_sd_worker(self, prompts: ImagePrompts) -> None:
        """Avvia un thread per SD txt2img."""
        # aggiorna pannello prompt
        self.prompt_preview.set_text(prompts.positive)
        self.prompt_preview.set_negative_text(prompts.negative)

        self._set_busy("Sto generando l'immagine…")

        sd_thread = QtCore.QThread(self)
        worker = SDWorker(self.sd_client, prompts.positive, prompts.negative)

        worker.moveToThread(sd_thread)

        sd_thread.started.connect(worker.run)
        worker.finished.connect(self._on_sd_finished)
        worker.error.connect(self._on_sd_error)

        # cleanup
        worker.finished.connect(sd_thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(sd_thread.quit)
        worker.error.connect(worker.deleteLater)
        sd_thread.finished.connect(sd_thread.deleteLater)

        self._sd_thread = sd_thread
        sd_thread.start()

    @QtCore.Slot(dict)
    def _on_sd_finished(self, result: dict) -> None:
        image_path = result.get("image_path") or ""
        if not image_path:
            QtWidgets.QMessageBox.warning(
                self,
                "Errore SD",
                "Errore sconosciuto durante la generazione dell'immagine.",
            )
            self._set_idle()
            return

        # aggiorna pannello preview e aggancia l'immagine all'ultima bolla di Luna
        self.prompt_preview.set_image(image_path)
        self.chat_view.attach_image_to_last_character_bubble(image_path)

        self._set_idle()

    @QtCore.Slot(str)
    def _on_sd_error(self, message: str) -> None:
        QtWidgets.QMessageBox.warning(self, "Errore SD", message)
        self._set_idle()

    # ----------------- Image viewer -----------------

    @QtCore.Slot(str)
    def _open_image_viewer(self, path: str) -> None:
        if not path:
            return
        dlg = ImageViewerDialog(path, self)
        dlg.exec()
