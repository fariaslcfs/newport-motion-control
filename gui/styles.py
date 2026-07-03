"""
Módulo de Estilo da aplicação Newport Motion Control.
Define uma folha de estilo QSS premium escura.
"""

DARK_THEME_QSS = """
QMainWindow {
    background-color: #1e1e2e;
}

QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", -apple-system, sans-serif;
}

QLabel {
    color: #cdd6f4;
}

/* Painel de Grupo / Containers */
QGroupBox {
    border: 1px solid #585b70;
    border-radius: 8px;
    margin-top: 2.2ex;
    font-weight: bold;
    color: #cba6f7; /* Roxo pastel para destaque de títulos */
    padding: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 12px;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #585b70;
    border-radius: 8px;
    background-color: #181825;
}

QTabBar::tab {
    background-color: #11111b;
    color: #a6adc8;
    border: 1px solid #585b70;
    border-bottom-color: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 10px 20px;
    margin-right: 4px;
}

QTabBar::tab:selected {
    background-color: #181825;
    color: #cdd6f4;
    border-color: #585b70;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    background-color: #313244;
    color: #cdd6f4;
}

/* Botões Padrão */
QPushButton {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 8px 16px;
    color: #cdd6f4;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #45475a;
}

QPushButton:pressed {
    background-color: #585b70;
}

QPushButton:disabled {
    background-color: #181825;
    border-color: #313244;
    color: #585b70;
}

/* Botões Especiais por ID */
QPushButton#ConnectBtn {
    background-color: #a6e3a1; /* Verde pastel */
    color: #11111b;
    border: 1px solid #8ccf87;
}

QPushButton#ConnectBtn:hover {
    background-color: #b4befe; /* Azul roxo */
    color: #11111b;
}

QPushButton#ConnectBtn:disabled {
    background-color: #181825;
    border-color: #313244;
    color: #585b70;
}

QPushButton#DisconnectBtn {
    background-color: #f38ba8; /* Vermelho pastel */
    color: #11111b;
    border: 1px solid #e07a96;
}

QPushButton#DisconnectBtn:hover {
    background-color: #f5c2e7; /* Rosa */
    color: #11111b;
}

QPushButton#DisconnectBtn:disabled {
    background-color: #181825;
    border-color: #313244;
    color: #585b70;
}

QPushButton#HomeBtn {
    background-color: #89b4fa; /* Azul pastel */
    color: #11111b;
    border: 1px solid #77a2e8;
}

QPushButton#HomeBtn:hover {
    background-color: #b4befe;
    color: #11111b;
}

QPushButton#HomeBtn:disabled {
    background-color: #181825;
    border-color: #313244;
    color: #585b70;
}

QPushButton#StopBtn {
    background-color: #f38ba8; /* Vermelho vibrante */
    color: #11111b;
    border: 1px solid #e07a96;
}

QPushButton#StopBtn:hover {
    background-color: #eba0b0;
    color: #11111b;
}

QPushButton#ActionBtn {
    background-color: #cba6f7; /* Roxo pastel */
    color: #11111b;
    border: 1px solid #b893e4;
}

QPushButton#ActionBtn:hover {
    background-color: #f5c2e7;
    color: #11111b;
}

QPushButton#ActionBtn:disabled {
    background-color: #181825;
    border-color: #313244;
    color: #585b70;
}

/* Inputs de Texto e Caixas de Seleção */
QLineEdit, QComboBox {
    background-color: #313244;
    border: 1px solid #585b70;
    border-radius: 6px;
    padding: 6px 10px;
    color: #cdd6f4;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #b4befe;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #181825;
    border: 1px solid #585b70;
    selection-background-color: #313244;
    selection-color: #cdd6f4;
    color: #cdd6f4;
}

/* Display de Posição Gigante */
QLabel#PositionDisplay {
    background-color: #11111b;
    color: #a6e3a1; /* Verde brilhante */
    border: 1px solid #585b70;
    border-radius: 8px;
    padding: 12px;
    font-family: "Consolas", monospace;
    font-weight: bold;
}

/* Barra de Status */
QStatusBar {
    background-color: #11111b;
    color: #a6adc8;
}

QStatusBar::item {
    border: none;
}
"""

def apply_dark_theme(app):
    """
    Aplica o tema escuro na instância do QApplication.
    """
    app.setStyleSheet(DARK_THEME_QSS)
