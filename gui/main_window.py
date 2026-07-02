import logging
import serial.tools.list_ports
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QLineEdit, QPushButton, QMessageBox,
                             QGroupBox, QGridLayout, QFrame, QSizePolicy, QTabWidget)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from core.esp_controller import ESP300_301_Controller
from core.esp302_controller import ESP302_Controller
from core.xps_controller import XPS_Controller
from core.base import NewportControllerInterface, AxisState

logger = logging.getLogger(__name__)

# --- Clean Light HMI Theme ---
# Removido a pedido do usuário
LIGHT_HMI_QSS = ""

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
        self.setWindowTitle("Newport Motion Control - HMI")
        self.setMinimumSize(900, 700)
        
        self.controller: NewportControllerInterface = None
        self.homing_worker = None
        self.current_state = AxisState.UNKNOWN
        
        self.init_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.setInterval(200)
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main Layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # 1. Connection Header
        self.create_connection_panel(main_layout)
        
        # 2. Main Body Tabs
        self.tabs = QTabWidget()
        
        # Tab 1: Controle Principal
        tab_control = QWidget()
        control_layout = QHBoxLayout(tab_control)
        control_layout.setContentsMargins(10, 10, 10, 10)
        control_layout.setSpacing(20)
        
        self.create_control_panel(control_layout)
        self.create_display_panel(control_layout)
        self.tabs.addTab(tab_control, "Controle de Eixo Principal")
        
        # Tab 2: Terminal RAW (Escondido em uma aba para não poluir)
        tab_terminal = QWidget()
        terminal_layout = QVBoxLayout(tab_terminal)
        self.create_terminal_panel(terminal_layout)
        self.tabs.addTab(tab_terminal, "Terminal e Comandos (Avançado)")
        
        main_layout.addWidget(self.tabs)

    def create_connection_panel(self, parent_layout):
        self.group_connection = QGroupBox("Hardware e Conexão")
        header_layout = QHBoxLayout(self.group_connection)
        
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
        self.btn_connect.setMinimumWidth(120)
        self.btn_connect.clicked.connect(self.connect_controller)
        
        self.btn_disconnect = QPushButton("Desconectar")
        self.btn_disconnect.setObjectName("DisconnectBtn")
        self.btn_disconnect.setMinimumWidth(120)
        self.btn_disconnect.clicked.connect(self.disconnect_controller)
        self.btn_disconnect.setEnabled(False)
        
        header_layout.addWidget(self.btn_connect)
        header_layout.addWidget(self.btn_disconnect)
        
        parent_layout.addWidget(self.group_connection)

    def create_control_panel(self, parent_layout):
        self.panel_left = QWidget()
        layout = QVBoxLayout(self.panel_left)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Seleção de Eixo
        self.group_axis = QGroupBox("Seleção de Eixo")
        axis_layout = QHBoxLayout(self.group_axis)
        axis_layout.addWidget(QLabel("Eixo Ativo:"))
        self.cb_axis = QComboBox()
        self.cb_axis.setMinimumWidth(150)
        axis_layout.addWidget(self.cb_axis)
        layout.addWidget(self.group_axis)
        
        # Ações do Ciclo de Vida
        self.group_lifecycle = QGroupBox("Ações de Estado (State Machine)")
        actions_grid = QGridLayout(self.group_lifecycle)
        actions_grid.setSpacing(10)
        
        self.btn_initialize = QPushButton("Initialize")
        self.btn_initialize.setObjectName("ActionBtn")
        self.btn_initialize.clicked.connect(self.initialize_axis)
        
        self.btn_enable = QPushButton("Enable Motor")
        self.btn_enable.setObjectName("ActionBtn")
        self.btn_enable.clicked.connect(self.enable_axis)
        
        self.btn_disable = QPushButton("Disable Motor")
        self.btn_disable.clicked.connect(self.disable_axis)
        
        self.btn_kill = QPushButton("Kill / Reset")
        self.btn_kill.clicked.connect(self.kill_axis)
        
        actions_grid.addWidget(self.btn_initialize, 0, 0)
        actions_grid.addWidget(self.btn_kill, 0, 1)
        actions_grid.addWidget(self.btn_enable, 1, 0)
        actions_grid.addWidget(self.btn_disable, 1, 1)
        layout.addWidget(self.group_lifecycle)
        
        # Ações de Movimento
        self.group_movement = QGroupBox("Movimentação Manual")
        move_layout = QVBoxLayout(self.group_movement)
        
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Target Absoluto:"))
        self.le_position = QLineEdit()
        self.le_position.setPlaceholderText("0.00")
        input_layout.addWidget(self.le_position)
        move_layout.addLayout(input_layout)
        
        self.btn_move = QPushButton("Executar Movimento")
        self.btn_move.setObjectName("ActionBtn")
        self.btn_move.clicked.connect(self.move_absolute)
        move_layout.addWidget(self.btn_move)
        layout.addWidget(self.group_movement)
        
        layout.addStretch()
        self.panel_left.setEnabled(False)
        parent_layout.addWidget(self.panel_left, stretch=1)

    def create_display_panel(self, parent_layout):
        self.panel_right = QWidget()
        layout = QVBoxLayout(self.panel_right)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.group_display = QGroupBox("Monitor de Eixo (Dashboard)")
        display_layout = QVBoxLayout(self.group_display)
        
        # Pill de Status
        status_header = QHBoxLayout()
        status_header.addWidget(QLabel("Estado Reportado:"))
        self.lbl_axis_status = QLabel("DESCONECTADO")
        self.lbl_axis_status.setObjectName("StatusPill")
        self.lbl_axis_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_header.addWidget(self.lbl_axis_status)
        status_header.addStretch()
        display_layout.addLayout(status_header)
        
        display_layout.addSpacing(15)
        
        # Display de Posição
        display_layout.addWidget(QLabel("Posição Atual (Units):"))
        self.lbl_position_display = QLabel("0.0000")
        self.lbl_position_display.setObjectName("PositionDisplay")
        self.lbl_position_display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_position_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        display_layout.addWidget(self.lbl_position_display)
        
        display_layout.addSpacing(20)
        
        # Ações Críticas (Superiores em Destaque)
        critical_layout = QHBoxLayout()
        self.btn_home = QPushButton("EXECUTAR HOMING")
        self.btn_home.setObjectName("HomeBtn")
        self.btn_home.setMinimumHeight(50)
        self.btn_home.clicked.connect(self.home_axis)
        
        self.btn_stop = QPushButton("PARADA EMERGÊNCIA")
        self.btn_stop.setObjectName("StopBtn")
        self.btn_stop.setMinimumHeight(50)
        self.btn_stop.clicked.connect(self.stop_motion)
        
        critical_layout.addWidget(self.btn_home)
        critical_layout.addWidget(self.btn_stop)
        display_layout.addLayout(critical_layout)
        
        layout.addWidget(self.group_display)
        
        self.panel_right.setEnabled(False)
        parent_layout.addWidget(self.panel_right, stretch=2)

    def create_terminal_panel(self, parent_layout):
        self.group_terminal = QGroupBox("Console")
        layout = QVBoxLayout(self.group_terminal)
        
        # Assistant (Apenas XPS)
        self.widget_xps_assistant = QWidget()
        xps_layout = QHBoxLayout(self.widget_xps_assistant)
        xps_layout.setContentsMargins(0, 0, 0, 0)
        xps_layout.addWidget(QLabel("Dicionário XPS:"))
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
        
        self.btn_send_cmd = QPushButton("Enviar")
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
            
            self.panel_left.setEnabled(True)
            self.panel_right.setEnabled(True)
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
        
        self.panel_left.setEnabled(False)
        self.panel_right.setEnabled(False)
        self.group_terminal.setEnabled(False)
        self.cb_axis.clear()
        
        self.lbl_position_display.setText("0.0000")
        self.update_status_pill("DESCONECTADO", "#95a5a6") # Cinza
        
        self.widget_xps_assistant.hide()

    def update_position(self):
        if self.homing_worker and self.homing_worker.isRunning():
            return
            
        if not self.controller: return
        axis = self.cb_axis.currentText()
        if not axis: return
            
        try:
            pos = self.controller.get_current_position(axis)
            self.lbl_position_display.setText(f"{pos:.4f}")
        except Exception:
            pass

        try:
            state = self.controller.get_axis_status(axis)
            if state != self.current_state:
                self.current_state = state
                self.update_ui_states(state)
        except Exception:
            pass

    def update_status_pill(self, text, color):
        self.lbl_axis_status.setText(text)
        self.lbl_axis_status.setStyleSheet(f"background-color: {color}; color: white;")

    def update_ui_states(self, state: AxisState):
        if self.homing_worker and self.homing_worker.isRunning():
            return
            
        # Desabilita tudo e habilita apenas o que faz sentido pro estado da Máquina
        self.btn_initialize.setEnabled(False)
        self.btn_enable.setEnabled(False)
        self.btn_disable.setEnabled(False)
        self.btn_home.setEnabled(False)
        self.btn_move.setEnabled(False)
        self.le_position.setEnabled(False)
        self.btn_kill.setEnabled(True) # Kill deve ser universal
        
        if state == AxisState.UNINITIALIZED:
            self.update_status_pill("NÃO INICIALIZADO", "#e74c3c") # Red
            self.btn_initialize.setEnabled(True)
            self.btn_home.setEnabled(True) # O XPS Controller agora faz init automático no home
            
        elif state == AxisState.NOT_REFERENCED:
            self.update_status_pill("REQUER HOMING", "#f39c12") # Orange
            self.btn_home.setEnabled(True)
            
        elif state == AxisState.DISABLED:
            self.update_status_pill("MOTOR DESLIGADO", "#8e44ad") # Purple
            self.btn_enable.setEnabled(True)
            self.btn_home.setEnabled(True) # O XPS Controller fará Kill -> Init -> Home
            
        elif state == AxisState.READY:
            self.update_status_pill("PRONTO (READY)", "#27ae60") # Green
            self.btn_disable.setEnabled(True)
            self.btn_home.setEnabled(True)
            self.btn_move.setEnabled(True)
            self.le_position.setEnabled(True)
            
        elif state == AxisState.MOVING:
            self.update_status_pill("EM MOVIMENTO", "#3498db") # Blue
            # Nada habilitado além do kill/stop
            
        elif state == AxisState.ERROR:
            self.update_status_pill("FALHA / ERRO", "#c0392b") # Dark Red
            self.btn_initialize.setEnabled(True)
            
        else:
            self.update_status_pill("DESCONHECIDO", "#7f8c8d") # Gray

    def move_absolute(self):
        if not self.controller: return
        axis = self.cb_axis.currentText()
        try:
            pos = float(self.le_position.text().strip().replace(',', '.'))
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
        self.btn_move.setEnabled(False)
        
        self.update_status_pill("HOMING EM PROGRESSO...", "#f1c40f") # Yellow
        self.lbl_axis_status.setStyleSheet("background-color: #f1c40f; color: #2c3e50;")
        
        self.homing_worker = HomingWorker(self.controller, axis)
        self.homing_worker.finished.connect(self._on_home_finished)
        self.homing_worker.error.connect(self._on_home_error)
        self.homing_worker.start()

    def _on_home_finished(self):
        # Força uma atualização do estado para limpar o HOMING EM PROGRESSO
        self.current_state = AxisState.UNKNOWN 
        
    def _on_home_error(self, err_msg):
        QMessageBox.critical(self, "Falha no Homing", f"A controladora retornou um erro durante a busca de origem:\n\n{err_msg}")
        self.btn_kill.setEnabled(True)
        self.current_state = AxisState.UNKNOWN 

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
