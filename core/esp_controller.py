import serial
import time
import logging
from typing import List
from .base import NewportControllerInterface

logger = logging.getLogger(__name__)

class ESP300_301_Controller(NewportControllerInterface):
    """
    Controlador para ESP300/301 via Serial.
    """
    def __init__(self):
        self.serial_port = None
    
    def connect(self, connection_string: str) -> bool:
        try:
            self.serial_port = serial.Serial(
                port=connection_string,
                baudrate=19200,
                timeout=0.5
            )
            # Limpar buffer inicial
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar na porta serial {connection_string}: {e}")
            return False

    def disconnect(self) -> None:
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception as e:
                logger.error(f"Erro ao desconectar porta serial: {e}")

    def get_stage_list(self) -> List[str]:
        return ["1", "2", "3"]

    def send_command(self, cmd: str) -> str:
        if not self.serial_port or not self.serial_port.is_open:
            logger.warning("Porta serial não está aberta.")
            return ""
        
        try:
            self.serial_port.write(f"{cmd}\r\n".encode('ascii'))
            return self.serial_port.readline().decode('ascii').strip()
        except Exception as e:
            logger.error(f"Erro ao enviar comando {cmd}: {e}")
            return ""

    def get_current_position(self, stage_id: str) -> float:
        ret = self.send_command(f"{stage_id}TP?")
        try:
            return float(ret)
        except ValueError:
            logger.debug(f"Falha ao converter posição: '{ret}'")
            return 0.0

    def move_absolute(self, stage_id: str, position: float) -> None:
        if not self.serial_port or not self.serial_port.is_open:
            return
        try:
            self.serial_port.write(f"{stage_id}PA{position}\r\n".encode('ascii'))
        except Exception as e:
            logger.error(f"Erro ao mover eixo {stage_id}: {e}")

    def stop_motion(self, stage_id: str) -> None:
        if not self.serial_port or not self.serial_port.is_open:
            return
        try:
            self.serial_port.write(f"{stage_id}ST\r\n".encode('ascii'))
        except Exception as e:
            logger.error(f"Erro ao parar eixo {stage_id}: {e}")

    def home_axis(self, stage_id: str) -> None:
        if not self.serial_port or not self.serial_port.is_open:
            return
        try:
            # Comando de busca de origem padrão para ESP300/301
            self.serial_port.write(f"{stage_id}OR\r\n".encode('ascii'))
        except Exception as e:
            logger.error(f"Erro ao executar home no eixo {stage_id}: {e}")
