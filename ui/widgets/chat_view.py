# file: ui/widgets/chat_view.py

import os
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets


class ChatBubble(QtWidgets.QFrame):
    openImageRequested = QtCore.Signal(str)

    def __init__(
        self,
        who_name: str,
        text: str,
        is_user: bool = False,
        image_path: Optional[str] = None,
        avatar_path: Optional[str] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("UserBubble" if is_user else "Bubble")

        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 10)
        self._layout.setSpacing(6)
        self._image_button: Optional[QtWidgets.QPushButton] = None

        # Header avatar + nome
        head = QtWidgets.QHBoxLayout()
        head.setSpacing(8)

        name = QtWidgets.QLabel(who_name)
        name.setStyleSheet("color:#6c7a92;font-weight:600;")

        avatar_label = QtWidgets.QLabel()
        if avatar_path and os.path.exists(avatar_path):
            pm = QtGui.QPixmap(avatar_path)
            if not pm.isNull():
                pm = pm.scaled(
                    32,
                    32,
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation,
                )
                avatar_label.setPixmap(pm)

        if is_user:
            head.addWidget(name)
            head.addStretch(1)
            head.addWidget(avatar_label)
        else:
            head.addWidget(avatar_label)
            head.addWidget(name)
            head.addStretch(1)

        self._layout.addLayout(head)

        # Corpo testo
        body = QtWidgets.QLabel(text)
        body.setWordWrap(True)
        self._layout.addWidget(body)

        # Se abbiamo già un'immagine, la agganciamo
        if image_path:
            self.set_image(image_path)

    def set_image(self, image_path: str) -> None:
        """Aggancia o aggiorna il pulsante 'Apri immagine' dentro la bolla."""
        if not image_path:
            return

        if self._image_button is None:
            btn = QtWidgets.QPushButton("Apri immagine")
            btn.setObjectName("Secondary")
            btn.clicked.connect(lambda: self.openImageRequested.emit(image_path))
            self._image_button = btn
            self._layout.addWidget(btn)
        else:
            try:
                self._image_button.clicked.disconnect()
            except TypeError:
                pass
            self._image_button.clicked.connect(
                lambda: self.openImageRequested.emit(image_path)
            )


class ZoomPanView(QtWidgets.QGraphicsView):
    def __init__(
        self,
        scene: Optional[QtWidgets.QGraphicsScene] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(scene, parent)
        self.setRenderHints(
            QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform
        )
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        old_pos = self.mapToScene(event.position().toPoint())
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)
        new_pos = self.mapToScene(event.position().toPoint())
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())


class ImageViewerDialog(QtWidgets.QDialog):
    def __init__(
        self,
        image_path: str,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Anteprima immagine")
        self.resize(800, 600)

        layout = QtWidgets.QVBoxLayout(self)

        scene = QtWidgets.QGraphicsScene(self)
        view = ZoomPanView(scene, self)
        layout.addWidget(view)

        if os.path.exists(image_path):
            pm = QtGui.QPixmap(image_path)
            if not pm.isNull():
                scene.addPixmap(pm)
                scene.setSceneRect(pm.rect())

        btn_close = QtWidgets.QPushButton("Chiudi")
        btn_close.clicked.connect(self.accept)
        hl = QtWidgets.QHBoxLayout()
        hl.addStretch(1)
        hl.addWidget(btn_close)
        layout.addLayout(hl)


class ChatView(QtWidgets.QScrollArea):
    openImageRequested = QtCore.Signal(str)

    def __init__(
        self,
        base_dir: Path,
        app_state: Optional[object] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.base_dir = base_dir
        self.app_state = app_state
        self.avatars_dir = self.base_dir / "assets" / "avatars"
        self._last_character_bubble: Optional[ChatBubble] = None

        self.setObjectName("ChatView")
        self.setWidgetResizable(True)
        self.viewport().setStyleSheet("background:transparent;")

        self._inner = QtWidgets.QWidget(self)
        self.setWidget(self._inner)
        self._v = QtWidgets.QVBoxLayout(self._inner)
        self._v.setContentsMargins(0, 4, 0, 4)
        self._v.setSpacing(8)
        self._v.addStretch(1)

    def _avatar_for(self, who: str, is_user: bool) -> Optional[str]:
        """Ritorna il percorso dell'avatar in assets/avatars."""
        if is_user:
            cand = self.avatars_dir / "user.png"
            return str(cand) if cand.exists() else None

        base_name = who.lower().strip()
        cand = self.avatars_dir / f"{base_name}.png"
        if cand.exists():
            return str(cand)

        return None

    def add_bubble(
        self,
        text: str,
        who: str = "PG",
        is_user: bool = False,
        image_path: Optional[str] = None,
    ) -> None:
        wrapper = QtWidgets.QWidget(self._inner)
        hb = QtWidgets.QHBoxLayout(wrapper)
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(8)

        avatar_path = self._avatar_for(who, is_user)
        bubble = ChatBubble(
            who_name=who,
            text=text,
            is_user=is_user,
            image_path=image_path,
            avatar_path=avatar_path,
            parent=wrapper,
        )
        bubble.openImageRequested.connect(self._on_open_image)

        # User a SINISTRA, personaggio a DESTRA
        if is_user:
            hb.addWidget(bubble, 0)
            hb.addStretch(1)
        else:
            hb.addStretch(1)
            hb.addWidget(bubble, 0)
            self._last_character_bubble = bubble

        self._v.insertWidget(self._v.count() - 1, wrapper)
        QtCore.QTimer.singleShot(50, self.scrollToBottom)

    def attach_image_to_last_character_bubble(self, image_path: str) -> None:
        """Attacca l'immagine all'ultima bolla del personaggio (stessa bolla testo+immagine)."""
        if self._last_character_bubble is not None:
            self._last_character_bubble.set_image(image_path)
            QtCore.QTimer.singleShot(50, self.scrollToBottom)
        else:
            # fallback di sicurezza: crea una nuova bolla solo immagine
            self.add_bubble("", who="PG", is_user=False, image_path=image_path)

    @QtCore.Slot(str)
    def _on_open_image(self, path: str) -> None:
        self.openImageRequested.emit(path)

    @QtCore.Slot()
    def scrollToBottom(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
