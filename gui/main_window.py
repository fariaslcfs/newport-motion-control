import logging
import serial.tools.list_ports
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QLineEdit, QPushButton, QMessageBox,
                             QGroupBox)
from PyQt6.QtCore import QTimer, Qt
from core.esp_controller import ESP300_301_Controller
from core.esp302_controller import ESP302_Controller
from core.xps_controller import XPS_Controller
from core.base import NewportControllerInterface

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """
    Janela principal da aplicação Newport Motion Control.
    Gerencia conexões, eixos, ciclos de vida de movimento e envio de comandos.
    """
    def __init__(self):
        """
        Inicializa a janela principal, configura a UI e o timer periódico.
        """
        super().__init__()
        self.setWindowTitle("Newport Motion Control")
        self.resize(500, 400)
        
        self.controller: NewportControllerInterface = None
        
        # UI Elements
        self.init_ui()
        
        # Timer para polling da posição
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.setInterval(200) # 200ms
        
    def init_ui(self):
        """
        Monta a estrutura de widgets da interface gráfica.
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # --- Configuração de Conexão ---
        conn_group = QGroupBox("Conexão")
        conn_layout = QVBoxLayout()
        
        # Tipo de controlador
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Controlador:"))
        self.cb_controller_type = QComboBox()
        self.cb_controller_type.addItems(["ESP300/301 (Serial)", "ESP302 (Ethernet)", "XPS C8 (Ethernet)"])
        type_layout.addWidget(self.cb_controller_type)
        conn_layout.addLayout(type_layout)
        
        # Endereço
        addr_layout = QHBoxLayout()
        addr_layout.addWidget(QLabel("Endereço (COM/IP):"))
        self.le_address = QLineEdit()
        self.le_address.setPlaceholderText("ex: COM3 ou 192.168.0.254")
        
        self.btn_auto_detect = QPushButton("Auto Detectar")
        self.btn_auto_detect.clicked.connect(self.auto_detect_port)
        
        addr_layout.addWidget(self.le_address)
        addr_layout.addWidget(self.btn_auto_detect)
        conn_layout.addLayout(addr_layout)
        
        # Botões Conectar/Desconectar
        btn_layout = QHBoxLayout()
        self.btn_connect = QPushButton("Conectar")
        self.btn_connect.clicked.connect(self.connect_controller)
        self.btn_disconnect = QPushButton("Desconectar")
        self.btn_disconnect.clicked.connect(self.disconnect_controller)
        self.btn_disconnect.setEnabled(False)
        btn_layout.addWidget(self.btn_connect)
        btn_layout.addWidget(self.btn_disconnect)
        conn_layout.addLayout(btn_layout)
        
        conn_group.setLayout(conn_layout)
        main_layout.addWidget(conn_group)
        
        # --- Movimentação ---
        move_group = QGroupBox("Controle de Eixo")
        move_layout = QVBoxLayout()
        
        # Seleção de Eixo
        axis_layout = QHBoxLayout()
        axis_layout.addWidget(QLabel("Eixo:"))
        self.cb_axis = QComboBox()
        axis_layout.addWidget(self.cb_axis)
        move_layout.addLayout(axis_layout)
        
        # Estado do Eixo
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Estado do Eixo:"))
        self.lbl_axis_status = QLabel("Desconectado")
        self.lbl_axis_status.setStyleSheet("font-weight: bold; color: blue;")
        status_layout.addWidget(self.lbl_axis_status)
        status_layout.addStretch()
        move_layout.addLayout(status_layout)
        
        # Botões de Ciclo de Vida do Eixo
        lifecycle_layout = QHBoxLayout()
        self.btn_initialize = QPushButton("Inicializar")
        self.btn_initialize.clicked.connect(self.initialize_axis)
        self.btn_enable = QPushButton("Ativar (Enable)")
        self.btn_enable.clicked.connect(self.enable_axis)
        self.btn_disable = QPushButton("Desativar (Disable)")
        self.btn_disable.clicked.connect(self.disable_axis)
        self.btn_kill = QPushButton("Reset/Kill")
        self.btn_kill.clicked.connect(self.kill_axis)
        
        lifecycle_layout.addWidget(self.btn_initialize)
        lifecycle_layout.addWidget(self.btn_enable)
        lifecycle_layout.addWidget(self.btn_disable)
        lifecycle_layout.addWidget(self.btn_kill)
        move_layout.addLayout(lifecycle_layout)
        
        # Posição Absoluta
        abs_layout = QHBoxLayout()
        abs_layout.addWidget(QLabel("Posição Absoluta:"))
        self.le_position = QLineEdit()
        self.btn_move = QPushButton("Mover")
        self.btn_move.clicked.connect(self.move_absolute)
        abs_layout.addWidget(self.le_position)
        abs_layout.addWidget(self.btn_move)
        move_layout.addLayout(abs_layout)
        
        # Botões Rápidos
        quick_btn_layout = QHBoxLayout()
        self.btn_home = QPushButton("Home")
        self.btn_home.clicked.connect(self.home_axis)
        self.btn_stop = QPushButton("Parar Emergência")
        self.btn_stop.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        self.btn_stop.clicked.connect(self.stop_motion)
        quick_btn_layout.addWidget(self.btn_home)
        quick_btn_layout.addWidget(self.btn_stop)
        move_layout.addLayout(quick_btn_layout)
        
        move_group.setLayout(move_layout)
        
        # Disable move group initially
        self.move_group = move_group
        self.move_group.setEnabled(False)
        main_layout.addWidget(move_group)
        
        # --- Comando Customizado ---
        custom_cmd_group = QGroupBox("Comando Customizado")
        custom_cmd_layout = QVBoxLayout()
        
        cmd_input_layout = QHBoxLayout()
        cmd_input_layout.addWidget(QLabel("Comando:"))
        self.le_custom_cmd = QLineEdit()
        self.btn_send_cmd = QPushButton("Enviar")
        self.btn_send_cmd.clicked.connect(self.send_custom_command)
        cmd_input_layout.addWidget(self.le_custom_cmd)
        cmd_input_layout.addWidget(self.btn_send_cmd)
        
        resp_layout = QHBoxLayout()
        resp_layout.addWidget(QLabel("Resposta:"))
        self.le_cmd_response = QLineEdit()
        self.le_cmd_response.setReadOnly(True)
        resp_layout.addWidget(self.le_cmd_response)
        
        custom_cmd_layout.addLayout(cmd_input_layout)
        custom_cmd_layout.addLayout(resp_layout)
        custom_cmd_group.setLayout(custom_cmd_layout)
        
        self.custom_cmd_group = custom_cmd_group
        self.custom_cmd_group.setEnabled(False)
        main_layout.addWidget(custom_cmd_group)
        
        # --- Display de Posição ---
        display_group = QGroupBox("Posição Atual")
        display_layout = QVBoxLayout()
        self.lbl_position_display = QLabel("0.000")
        self.lbl_position_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_position_display.setStyleSheet("font-size: 48px; font-weight: bold; color: green;")
        display_layout.addWidget(self.lbl_position_display)
        display_group.setLayout(display_layout)
        
        main_layout.addWidget(display_group)
        main_layout.addStretch()

    def auto_detect_port(self):
        """
        Auto-detecta portas seriais que usam conversores Prolific ou preenche o IP padrão.
        """
        ctrl_type = self.cb_controller_type.currentText()
        if "Serial" in ctrl_type:
            found = False
            for port in serial.tools.list_ports.comports():
                # Verifica se a string do fabricante não é vazia e contém 'prolific'
                if port.manufacturer and "prolific" in port.manufacturer.lower():
                    self.le_address.setText(port.device)
                    QMessageBox.information(self, "Detectado", f"Dispositivo Prolific encontrado na porta: {port.device}")
                    found = True
                    break
            
            if not found:
                QMessageBox.warning(self, "Não encontrado", "Nenhum cabo conversor Prolific foi encontrado.")
        elif "Ethernet" in ctrl_type:
            self.le_address.setText("192.168.0.254")

    def connect_controller(self):
        """
        Instancia o controlador selecionado e estabelece a conexão física/rede.
        Populariza a lista de eixos ativos e inicia o timer de leitura de posição.
        """
        ctrl_type = self.cb_controller_type.currentText()
        address = self.le_address.text().strip()
        
        if not address:
            QMessageBox.warning(self, "Aviso", "Por favor, insira o endereço.")
            return
            
        if ctrl_type == "ESP300/301 (Serial)":
            self.controller = ESP300_301_Controller()
        elif ctrl_type == "ESP302 (Ethernet)":
            self.controller = ESP302_Controller()
        elif ctrl_type == "XPS C8 (Ethernet)":
            self.controller = XPS_Controller()
        else:
            QMessageBox.critical(self, "Erro", "Controlador não reconhecido.")
            return
            
        if self.controller.connect(address):
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
            self.cb_controller_type.setEnabled(False)
            self.le_address.setEnabled(False)
            self.btn_auto_detect.setEnabled(False)
            self.move_group.setEnabled(True)
            self.custom_cmd_group.setEnabled(True)
            
            # Popular eixos
            stages = self.controller.get_stage_list()
            self.cb_axis.clear()
            self.cb_axis.addItems(stages)
            
            # Avisa o usuário sobre quais módulos foram detectados
            QMessageBox.information(self, "Conexão Bem-Sucedida", f"Controlador conectado!\nEixos detectados: {', '.join(stages)}")
            
            # Atualiza posição e status imediatamente
            self.update_position()
            self.timer.start()
        else:
            QMessageBox.critical(self, "Erro", f"Falha ao conectar no endereço {address}")

    def disconnect_controller(self):
        """
        Para o timer de atualização e desconecta o controlador de forma limpa.
        """
        self.timer.stop()
        if self.controller:
            self.controller.disconnect()
            self.controller = None
            
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.cb_controller_type.setEnabled(True)
        self.le_address.setEnabled(True)
        self.btn_auto_detect.setEnabled(True)
        self.move_group.setEnabled(False)
        self.custom_cmd_group.setEnabled(False)
        self.cb_axis.clear()
        self.lbl_position_display.setText("0.000")
        self.lbl_axis_status.setText("Desconectado")
        self.lbl_axis_status.setStyleSheet("font-weight: bold; color: blue;")

    def update_position(self):
        """
        Método de polling periódico executado pelo QTimer.
        Atualiza no display a posição atual do estágio selecionado e seu status de erro/energia.
        """
        if not self.controller:
            return
            
        axis = self.cb_axis.currentText()
        if not axis:
            return
            
        try:
            pos = self.controller.get_current_position(axis)
            self.lbl_position_display.setText(f"{pos:.4f}")
        except Exception as e:
            logger.error(f"Erro ao atualizar posição: {e}")

        try:
            status = self.controller.get_axis_status(axis)
            self.lbl_axis_status.setText(status)
            self.update_ui_states(status)
        except Exception as e:
            logger.error(f"Erro ao atualizar status: {e}")

    def update_ui_states(self, status: str):
        """
        Gerencia o estado dos botões da interface baseando-se no estado atual da máquina do eixo.

        Args:
            status (str): Estado atual informado pela controladora.
        """
        status_lower = status.lower()
        
        # Se contiver 'not initialized' ou 'notinit'
        if "not initialized" in status_lower or "notinit" in status_lower:
            self.lbl_axis_status.setStyleSheet("font-weight: bold; color: red;")
            self.btn_initialize.setEnabled(True)
            self.btn_enable.setEnabled(False)
            self.btn_disable.setEnabled(False)
            self.btn_home.setEnabled(False)
            self.btn_move.setEnabled(False)
            self.le_position.setEnabled(False)
            self.btn_kill.setEnabled(True)
        # Se contiver 'not referenced' ou 'notref' ou 'homing'
        elif "not referenced" in status_lower or "notref" in status_lower or "homing" in status_lower:
            self.lbl_axis_status.setStyleSheet("font-weight: bold; color: orange;")
            self.btn_initialize.setEnabled(False)
            self.btn_enable.setEnabled(False)
            self.btn_disable.setEnabled(False)
            self.btn_home.setEnabled(True)
            self.btn_move.setEnabled(False)
            self.le_position.setEnabled(False)
            self.btn_kill.setEnabled(True)
        # Se contiver 'disabled' ou 'motor off'
        elif "disabled" in status_lower or "motor off" in status_lower:
            self.lbl_axis_status.setStyleSheet("font-weight: bold; color: gray;")
            self.btn_initialize.setEnabled(False)
            self.btn_enable.setEnabled(True)
            self.btn_disable.setEnabled(False)
            self.btn_home.setEnabled(False)
            self.btn_move.setEnabled(False)
            self.le_position.setEnabled(False)
            self.btn_kill.setEnabled(True)
        # Se contiver 'ready' ou 'motor on'
        elif "ready" in status_lower or "motor on" in status_lower:
            self.lbl_axis_status.setStyleSheet("font-weight: bold; color: green;")
            self.btn_initialize.setEnabled(False)
            self.btn_enable.setEnabled(False)
            self.btn_disable.setEnabled(True)
            self.btn_home.setEnabled(True)
            self.btn_move.setEnabled(True)
            self.le_position.setEnabled(True)
            self.btn_kill.setEnabled(True)
        else:
            # Qualquer outro estado (Emergency stop, etc.)
            self.lbl_axis_status.setStyleSheet("font-weight: bold; color: darkred;")
            self.btn_initialize.setEnabled(True)
            self.btn_enable.setEnabled(False)
            self.btn_disable.setEnabled(False)
            self.btn_home.setEnabled(False)
            self.btn_move.setEnabled(False)
            self.le_position.setEnabled(False)
            self.btn_kill.setEnabled(True)

    def move_absolute(self):
        """
        Dispara a movimentação absoluta para o valor lido na caixa de texto.
        """
        if not self.controller:
            return
            
        axis = self.cb_axis.currentText()
        pos_str = self.le_position.text().strip()
        
        try:
            pos = float(pos_str)
            self.controller.move_absolute(axis, pos)
        except ValueError:
            QMessageBox.warning(self, "Erro", "Posição inválida. Insira um número.")
        except Exception as e:
            logger.error(f"Erro ao mover eixo: {e}")

    def home_axis(self):
        """
        Envia comando para que o eixo procure sua marca de Home/Zero físico.
        """
        if not self.controller:
            return
            
        axis = self.cb_axis.currentText()
        try:
            self.controller.home_axis(axis)
            QMessageBox.information(self, "Home", f"Busca de origem (Home) iniciada para o eixo {axis}.")
        except Exception as e:
            logger.error(f"Erro ao buscar origem do eixo: {e}")

    def stop_motion(self):
        """
        Dispara comando de abortar movimento e travar o motor.
        """
        if not self.controller:
            return
        
        axis = self.cb_axis.currentText()
        try:
            self.controller.stop_motion(axis)
        except Exception as e:
            logger.error(f"Erro ao parar eixo: {e}")

    def initialize_axis(self):
        """
        Interface com o comando de inicialização de eixo do controlador.
        """
        if not self.controller:
            return
        axis = self.cb_axis.currentText()
        if not axis:
            return
        try:
            self.controller.initialize_axis(axis)
            QMessageBox.information(self, "Inicializar", f"Inicialização do eixo {axis} executada com sucesso.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao inicializar eixo {axis}: {e}")

    def enable_axis(self):
        """
        Envia o comando de ativação de potência (Enable) do motor para o eixo selecionado.
        """
        if not self.controller:
            return
        axis = self.cb_axis.currentText()
        if not axis:
            return
        try:
            self.controller.enable_axis(axis)
            QMessageBox.information(self, "Habilitar", f"Eixo {axis} habilitado (Motor ON).")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao habilitar eixo {axis}: {e}")

    def disable_axis(self):
        """
        Envia o comando de desativação de potência (Disable) do motor para o eixo selecionado.
        """
        if not self.controller:
            return
        axis = self.cb_axis.currentText()
        if not axis:
            return
        try:
            self.controller.disable_axis(axis)
            QMessageBox.information(self, "Desabilitar", f"Eixo {axis} desabilitado (Motor OFF).")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao desabilitar eixo {axis}: {e}")

    def kill_axis(self):
        """
        Envia o comando Kill/Reset do grupo ou estágio para parar e limpar eventuais erros de status.
        """
        if not self.controller:
            return
        axis = self.cb_axis.currentText()
        if not axis:
            return
        try:
            self.controller.kill_axis(axis)
            QMessageBox.warning(self, "Kill/Reset", f"Comando Kill/Reset enviado para o eixo {axis}.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao enviar Kill/Reset para {axis}: {e}")

    def send_custom_command(self):
        """
        Envia comando arbitrário inserido no terminal da GUI e escreve a resposta obtida.
        """
        if not self.controller:
            return
            
        cmd = self.le_custom_cmd.text().strip()
        if not cmd:
            return
            
        try:
            # Para o XPS, nós adicionamos 'expect_response=True' caso seja um comando de query
            # Como o Python ignora kwargs extras caso a assinatura não comporte, 
            # podemos fazer uma verificação de tipo de objeto
            from core.xps_controller import XPS_Controller
            
            if isinstance(self.controller, XPS_Controller):
                # Assumimos que o usuário quer ver a resposta (o XPS às vezes exige isso dependendo do comando)
                # Vamos forçar true para o usuário poder ler
                response = self.controller.send_command(cmd, expect_response=True)
            else:
                response = self.controller.send_command(cmd)
                
            self.le_cmd_response.setText(response if response else "Ok (sem retorno)")
        except Exception as e:
            logger.error(f"Erro ao enviar comando customizado: {e}")
            self.le_cmd_response.setText(f"Erro: {e}")

    def closeEvent(self, event):
        """
        Executado ao fechar a janela da aplicação, garantindo desconexão segura.
        """
        self.disconnect_controller()
        event.accept()
