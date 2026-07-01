import logging
import serial.tools.list_ports
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QLineEdit, QPushButton, QMessageBox,
                             QGroupBox, QGridLayout, QFrame, QSizePolicy)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from core.esp_controller import ESP300_301_Controller
from core.esp302_controller import ESP302_Controller
from core.xps_controller import XPS_Controller
from core.base import NewportControllerInterface

logger = logging.getLogger(__name__)

# --- Modern Professional Dark Theme ---
MODERN_THEME_QSS = """
QMainWindow {
    background-color: #1e1e1e;
}

QWidget {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Arial, sans-serif;
    color: #cccccc;
    font-size: 10pt;
}

/* Group Boxes / Frames */
QGroupBox {
    border: 1px solid #333333;
    border-radius: 6px;
    margin-top: 1.5em;
    padding-top: 0.5em;
    background-color: #252526;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 10px;
    color: #4facfe;
    font-weight: bold;
    font-size: 11pt;
}

/* Inputs */
QLineEdit, QComboBox {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px 8px;
    color: #ffffff;
    selection-background-color: #007acc;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #007acc;
}
QComboBox::drop-down {
    border: none;
}

/* Buttons */
QPushButton {
    background-color: #007acc;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    color: #ffffff;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #0098ff;
}
QPushButton:pressed {
    background-color: #005a9e;
}
QPushButton:disabled {
    background-color: #4d4d4d;
    color: #888888;
}

/* Specific Buttons */
QPushButton#ConnectBtn {
    background-color: #28a745;
}
QPushButton#ConnectBtn:hover {
    background-color: #34ce57;
}
QPushButton#DisconnectBtn {
    background-color: #dc3545;
}
QPushButton#DisconnectBtn:hover {
    background-color: #fa4a5b;
}

/* Position Display */
QLabel#PositionDisplay {
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 56px;
    font-weight: 300;
    color: #4facfe;
    background-color: #1a1a1a;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 10px;
}

/* Status Labels */
QLabel#StatusPill {
    font-weight: bold;
    padding: 4px 10px;
    border-radius: 12px;
    color: white;
    background-color: #6c757d;
}

/* Separation Lines */
QFrame#HLine {
    background-color: #333333;
}
"""

class HomingWorker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, controller, axis):
        super().__init__()
        self.controller = controller
        self.axis = axis

    def run(self):
        try:
            self.controller.home_axis(self.axis)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Newport Motion Control")
        self.setMinimumSize(850, 650)
        self.setStyleSheet(MODERN_THEME_QSS)
        
        self.controller: NewportControllerInterface = None
        self.homing_worker = None
        
        self.init_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.setInterval(200)
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main Layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 1. Connection Header
        self.create_connection_panel(main_layout)
        
        # Separator
        line = QFrame()
        line.setObjectName("HLine")
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        main_layout.addWidget(line)
        
        # 2. Main Body (Axis Control & Display)
        body_layout = QHBoxLayout()
        body_layout.setSpacing(20)
        
        self.create_control_panel(body_layout)
        self.create_display_panel(body_layout)
        
        main_layout.addLayout(body_layout)
        
        # 3. Terminal Footer
        self.create_terminal_panel(main_layout)

    def create_connection_panel(self, parent_layout):
        header_layout = QHBoxLayout()
        
        header_layout.addWidget(QLabel("Controlador:"))
        self.cb_controller_type = QComboBox()
        self.cb_controller_type.addItems(["ESP300/301 (Serial)", "ESP302 (Ethernet)", "XPS C8 (Ethernet)"])
        self.cb_controller_type.currentTextChanged.connect(self.on_controller_type_changed)
        header_layout.addWidget(self.cb_controller_type)
        
        header_layout.addSpacing(15)
        
        header_layout.addWidget(QLabel("Endereço:"))
        self.le_address = QLineEdit()
        self.le_address.setPlaceholderText("ex: 192.168.0.254 ou COM3")
        self.le_address.setMinimumWidth(180)
        header_layout.addWidget(self.le_address)
        
        self.btn_auto_detect = QPushButton("Detectar Porta Serial")
        self.btn_auto_detect.clicked.connect(self.auto_detect_port)
        header_layout.addWidget(self.btn_auto_detect)
        
        header_layout.addStretch()
        
        self.btn_connect = QPushButton("Conectar")
        self.btn_connect.setObjectName("ConnectBtn")
        self.btn_connect.setMinimumWidth(100)
        self.btn_connect.clicked.connect(self.connect_controller)
        
        self.btn_disconnect = QPushButton("Desconectar")
        self.btn_disconnect.setObjectName("DisconnectBtn")
        self.btn_disconnect.setMinimumWidth(100)
        self.btn_disconnect.clicked.connect(self.disconnect_controller)
        self.btn_disconnect.setEnabled(False)
        
        header_layout.addWidget(self.btn_connect)
        header_layout.addWidget(self.btn_disconnect)
        
        parent_layout.addLayout(header_layout)

    def create_control_panel(self, parent_layout):
        self.group_controls = QGroupBox("Controle de Eixo")
        layout = QVBoxLayout(self.group_controls)
        layout.setSpacing(15)
        
        # Seleção de Eixo
        axis_layout = QHBoxLayout()
        axis_layout.addWidget(QLabel("Eixo Selecionado:"))
        self.cb_axis = QComboBox()
        self.cb_axis.setMinimumWidth(120)
        axis_layout.addWidget(self.cb_axis)
        axis_layout.addStretch()
        layout.addLayout(axis_layout)
        
        # Ações do Ciclo de Vida
        actions_grid = QGridLayout()
        actions_grid.setSpacing(10)
        
        self.btn_initialize = QPushButton("Inicializar")
        self.btn_initialize.clicked.connect(self.initialize_axis)
        self.btn_kill = QPushButton("Reset / Kill")
        self.btn_kill.clicked.connect(self.kill_axis)
        self.btn_enable = QPushButton("Enable Motor")
        self.btn_enable.clicked.connect(self.enable_axis)
        self.btn_disable = QPushButton("Disable Motor")
        self.btn_disable.clicked.connect(self.disable_axis)
        
        actions_grid.addWidget(self.btn_initialize, 0, 0)
        actions_grid.addWidget(self.btn_kill, 0, 1)
        actions_grid.addWidget(self.btn_enable, 1, 0)
        actions_grid.addWidget(self.btn_disable, 1, 1)
        
        layout.addLayout(actions_grid)
        
        # Ações de Movimento
        move_layout = QHBoxLayout()
        self.le_position = QLineEdit()
        self.le_position.setPlaceholderText("Destino Absoluto")
        self.btn_move = QPushButton("Mover")
        self.btn_move.clicked.connect(self.move_absolute)
        move_layout.addWidget(self.le_position)
        move_layout.addWidget(self.btn_move)
        layout.addLayout(move_layout)
        
        # Ações Críticas
        critical_layout = QHBoxLayout()
        self.btn_home = QPushButton("Home Search")
        self.btn_home.setStyleSheet("background-color: #fd7e14;") # Laranja
        self.btn_home.clicked.connect(self.home_axis)
        
        self.btn_stop = QPushButton("Parada Emergência")
        self.btn_stop.setStyleSheet("background-color: #dc3545;") # Vermelho
        self.btn_stop.clicked.connect(self.stop_motion)
        
        critical_layout.addWidget(self.btn_home)
        critical_layout.addWidget(self.btn_stop)
        layout.addLayout(critical_layout)
        
        layout.addStretch()
        self.group_controls.setEnabled(False)
        parent_layout.addWidget(self.group_controls, stretch=1)

    def create_display_panel(self, parent_layout):
        self.group_display = QGroupBox("Status do Sistema")
        layout = QVBoxLayout(self.group_display)
        
        # Pill de Status
        status_header = QHBoxLayout()
        status_header.addWidget(QLabel("Estado da Máquina:"))
        self.lbl_axis_status = QLabel("DESCONECTADO")
        self.lbl_axis_status.setObjectName("StatusPill")
        self.lbl_axis_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_header.addWidget(self.lbl_axis_status)
        status_header.addStretch()
        layout.addLayout(status_header)
        
        layout.addSpacing(20)
        
        # Display de Posição
        layout.addWidget(QLabel("Posição Atual (Absoluta):"))
        self.lbl_position_display = QLabel("0.0000")
        self.lbl_position_display.setObjectName("PositionDisplay")
        self.lbl_position_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Expande para ocupar o espaço
        self.lbl_position_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.lbl_position_display)
        
        parent_layout.addWidget(self.group_display, stretch=2)

    def create_terminal_panel(self, parent_layout):
        self.group_terminal = QGroupBox("Terminal de Comandos")
        layout = QVBoxLayout(self.group_terminal)
        
        # Assistant (Apenas XPS)
        self.widget_xps_assistant = QWidget()
        xps_layout = QHBoxLayout(self.widget_xps_assistant)
        xps_layout.setContentsMargins(0, 0, 0, 0)
        xps_layout.addWidget(QLabel("XPS Assistant:"))
        self.cb_xps_commands = QComboBox()
        self.cb_xps_commands.addItem("Selecione um comando da API XPS...")
        self.cb_xps_commands.currentIndexChanged.connect(self.on_xps_command_selected)
        xps_layout.addWidget(self.cb_xps_commands, stretch=1)
        layout.addWidget(self.widget_xps_assistant)
        self.widget_xps_assistant.hide()
        
        # Terminal I/O
        io_layout = QHBoxLayout()
        self.le_custom_cmd = QLineEdit()
        self.le_custom_cmd.setPlaceholderText("Digite um comando raw (ex: 1TP?)")
        
        self.btn_send_cmd = QPushButton("Enviar Comando")
        self.btn_send_cmd.clicked.connect(self.send_custom_command)
        
        io_layout.addWidget(self.le_custom_cmd, stretch=2)
        io_layout.addWidget(self.btn_send_cmd)
        
        self.le_cmd_response = QLineEdit()
        self.le_cmd_response.setPlaceholderText("Resposta da controladora...")
        self.le_cmd_response.setReadOnly(True)
        io_layout.addWidget(self.le_cmd_response, stretch=3)
        
        layout.addLayout(io_layout)
        
        self.group_terminal.setEnabled(False)
        parent_layout.addWidget(self.group_terminal)

    # =========================================================================
    # LÓGICA DE NEGÓCIO E MÉTODOS DE AÇÃO
    # =========================================================================

    def on_controller_type_changed(self, text):
        if "Serial" in text:
            self.btn_auto_detect.setEnabled(True)
        else:
            self.btn_auto_detect.setEnabled(False)

    def auto_detect_port(self):
        ctrl_type = self.cb_controller_type.currentText()
        if "Serial" in ctrl_type:
            for port in serial.tools.list_ports.comports():
                if port.manufacturer and "prolific" in port.manufacturer.lower():
                    self.le_address.setText(port.device)
                    QMessageBox.information(self, "Detectado", f"Cabo serial detectado na porta: {port.device}")
                    return
            QMessageBox.warning(self, "Aviso", "Nenhuma porta serial correspondente encontrada.")

    def connect_controller(self):
        ctrl_type = self.cb_controller_type.currentText()
        address = self.le_address.text().strip()
        
        if not address:
            QMessageBox.warning(self, "Aviso", "Endereço inválido.")
            return
            
        if ctrl_type == "ESP300/301 (Serial)":
            self.controller = ESP300_301_Controller()
        elif ctrl_type == "ESP302 (Ethernet)":
            self.controller = ESP302_Controller()
        elif ctrl_type == "XPS C8 (Ethernet)":
            self.controller = XPS_Controller()
            
        if self.controller.connect(address):
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
            self.cb_controller_type.setEnabled(False)
            self.le_address.setEnabled(False)
            self.btn_auto_detect.setEnabled(False)
            
            self.group_controls.setEnabled(True)
            self.group_terminal.setEnabled(True)
            
            stages = self.controller.get_stage_list()
            self.cb_axis.clear()
            self.cb_axis.addItems(stages)
            
            if ctrl_type == "XPS C8 (Ethernet)":
                self.populate_xps_commands()
                self.widget_xps_assistant.show()
            else:
                self.widget_xps_assistant.hide()
            
            self.update_position()
            self.timer.start()
        else:
            QMessageBox.critical(self, "Erro de Conexão", f"Falha ao tentar conectar no endereço: {address}")

    def disconnect_controller(self):
        self.timer.stop()
        if self.controller:
            self.controller.disconnect()
            self.controller = None
            
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.cb_controller_type.setEnabled(True)
        self.le_address.setEnabled(True)
        self.btn_auto_detect.setEnabled(True)
        
        self.group_controls.setEnabled(False)
        self.group_terminal.setEnabled(False)
        self.cb_axis.clear()
        
        self.lbl_position_display.setText("0.0000")
        self.update_status_pill("DESCONECTADO", "#6c757d") # Cinza
        
        self.widget_xps_assistant.hide()

    def update_position(self):
        if not self.controller: return
        axis = self.cb_axis.currentText()
        if not axis: return
            
        try:
            pos = self.controller.get_current_position(axis)
            self.lbl_position_display.setText(f"{pos:.4f}")
        except Exception:
            pass

        try:
            status = self.controller.get_axis_status(axis)
            self.update_ui_states(status)
        except Exception:
            pass

    def update_status_pill(self, text, color):
        self.lbl_axis_status.setText(text)
        self.lbl_axis_status.setStyleSheet(f"background-color: {color}; color: white;")

    def update_ui_states(self, status: str):
        if self.homing_worker and self.homing_worker.isRunning():
            return
            
        status_lower = status.lower()
        
        # Mapeamento semântico de cores
        if "not initialized" in status_lower or "notinit" in status_lower:
            self.update_status_pill(status.upper(), "#dc3545") # Red
            self.btn_initialize.setEnabled(True)
            self.btn_enable.setEnabled(False)
            self.btn_disable.setEnabled(False)
            self.btn_home.setEnabled(False)
            self.btn_move.setEnabled(False)
            self.le_position.setEnabled(False)
            self.btn_kill.setEnabled(True)
            
        elif "not referenced" in status_lower or "notref" in status_lower or "homing" in status_lower:
            self.update_status_pill(status.upper(), "#fd7e14") # Orange
            self.btn_initialize.setEnabled(False)
            self.btn_enable.setEnabled(False)
            self.btn_disable.setEnabled(False)
            self.btn_home.setEnabled(True)
            self.btn_move.setEnabled(False)
            self.le_position.setEnabled(False)
            self.btn_kill.setEnabled(True)
            
        elif "disable" in status_lower or "motor off" in status_lower:
            self.update_status_pill(status.upper(), "#6f42c1") # Purple
            self.btn_initialize.setEnabled(False)
            self.btn_enable.setEnabled(True)
            self.btn_disable.setEnabled(False)
            self.btn_home.setEnabled(False)
            self.btn_move.setEnabled(False)
            self.le_position.setEnabled(False)
            self.btn_kill.setEnabled(True)
            
        elif "ready" in status_lower or "motor on" in status_lower:
            self.update_status_pill(status.upper(), "#28a745") # Green
            self.btn_initialize.setEnabled(False)
            self.btn_enable.setEnabled(False)
            self.btn_disable.setEnabled(True)
            self.btn_home.setEnabled(True)
            self.btn_move.setEnabled(True)
            self.le_position.setEnabled(True)
            self.btn_kill.setEnabled(True)
            
        else:
            self.update_status_pill(status.upper(), "#343a40") # Dark Gray
            self.btn_initialize.setEnabled(True)
            self.btn_enable.setEnabled(False)
            self.btn_disable.setEnabled(False)
            self.btn_home.setEnabled(False)
            self.btn_move.setEnabled(False)
            self.le_position.setEnabled(False)
            self.btn_kill.setEnabled(True)

    def move_absolute(self):
        if not self.controller: return
        axis = self.cb_axis.currentText()
        try:
            pos = float(self.le_position.text().strip())
            self.controller.move_absolute(axis, pos)
        except ValueError:
            QMessageBox.warning(self, "Aviso", "Por favor, insira um valor numérico válido para a posição.")

    def home_axis(self):
        if not self.controller: return
        axis = self.cb_axis.currentText()
        
        self.btn_home.setEnabled(False)
        self.btn_initialize.setEnabled(False)
        self.btn_enable.setEnabled(False)
        self.btn_disable.setEnabled(False)
        self.btn_kill.setEnabled(False)
        self.update_status_pill("HOMING EM PROGRESSO...", "#ffc107") # Yellow
        self.lbl_axis_status.setStyleSheet("background-color: #ffc107; color: #212529;")
        
        self.homing_worker = HomingWorker(self.controller, axis)
        self.homing_worker.finished.connect(self._on_home_finished)
        self.homing_worker.error.connect(self._on_home_error)
        self.homing_worker.start()

    def _on_home_finished(self):
        pass # Status será atualizado automaticamente pelo Timer
        
    def _on_home_error(self, err_msg):
        QMessageBox.critical(self, "Falha no Homing", f"A controladora retornou um erro durante a busca de home:\n\n{err_msg}")
        self.btn_kill.setEnabled(True)

    def stop_motion(self):
        if not self.controller: return
        axis = self.cb_axis.currentText()
        self.controller.stop_motion(axis)

    def initialize_axis(self):
        if not self.controller: return
        axis = self.cb_axis.currentText()
        try:
            self.controller.initialize_axis(axis)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao inicializar: {e}")

    def enable_axis(self):
        if not self.controller: return
        axis = self.cb_axis.currentText()
        try:
            self.controller.enable_axis(axis)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao habilitar: {e}")

    def disable_axis(self):
        if not self.controller: return
        axis = self.cb_axis.currentText()
        try:
            self.controller.disable_axis(axis)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao desabilitar: {e}")

    def kill_axis(self):
        if not self.controller: return
        axis = self.cb_axis.currentText()
        try:
            self.controller.kill_axis(axis)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro no comando Kill: {e}")

    def send_custom_command(self):
        if not self.controller: return
        cmd = self.le_custom_cmd.text().strip()
        if not cmd: return
        try:
            from core.xps_controller import XPS_Controller
            if isinstance(self.controller, XPS_Controller):
                resp = self.controller.send_command(cmd, expect_response=True)
            else:
                resp = self.controller.send_command(cmd)
            self.le_cmd_response.setText(resp if resp else "Sucesso (Sem Retorno)")
        except Exception as e:
            self.le_cmd_response.setText(f"Erro: {e}")

    def populate_xps_commands(self):
        try:
            import inspect
            from newportxps.XPS_C8_drivers import XPS
            commands = []
            for name, func in inspect.getmembers(XPS, inspect.isroutine):
                if name[0].isupper() and not name.startswith("TCP_") and not name.startswith("Login"):
                    sig = inspect.signature(func)
                    params = [p for p in sig.parameters.keys() if p not in ('self', 'socketId')]
                    commands.append(f"{name}({', '.join(params)})")
            self.cb_xps_commands.clear()
            self.cb_xps_commands.addItem("Selecione um comando da API XPS...")
            self.cb_xps_commands.addItems(sorted(commands))
        except Exception:
            pass

    def on_xps_command_selected(self, index):
        if index > 0:
            self.le_custom_cmd.setText(self.cb_xps_commands.itemText(index))

    def closeEvent(self, event):
        self.disconnect_controller()
        event.accept()
