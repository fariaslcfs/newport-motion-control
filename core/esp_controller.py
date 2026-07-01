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
        """
        Conecta ao controlador ESP300/301 via porta serial.

        Args:
            connection_string (str): A porta serial para conexão (ex: 'COM3' ou '/dev/ttyUSB0').

        Returns:
            bool: True se a conexão foi bem-sucedida, False caso contrário.
        """
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
        """
        Fecha a conexão serial de forma segura se estiver aberta.
        """
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception as e:
                logger.error(f"Erro ao desconectar porta serial: {e}")

    def get_stage_list(self) -> List[str]:
        """
        Retorna a lista de eixos suportados por padrão no ESP300/301.

        Returns:
            List[str]: Lista contendo identificadores de eixos ['1', '2', '3'].
        """
        return ["1", "2", "3"]

    def send_command(self, cmd: str) -> str:
        """
        Envia um comando ASCII de baixo nível via serial e retorna a resposta de uma linha.

        Args:
            cmd (str): O comando Newport (sem sufixo CRLF).

        Returns:
            str: Resposta do controlador ou string vazia em caso de falha/sem resposta.
        """
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
        """
        Lê a posição atual de um eixo específico utilizando o comando 'TP?'.

        Args:
            stage_id (str): Identificador do eixo (ex: '1').

        Returns:
            float: A posição atual em unidades físicas do estágio ou 0.0 em caso de erro.
        """
        ret = self.send_command(f"{stage_id}TP?")
        try:
            return float(ret)
        except ValueError:
            logger.debug(f"Falha ao converter posição: '{ret}'")
            return 0.0

    def move_absolute(self, stage_id: str, position: float) -> None:
        """
        Move o eixo para a posição absoluta desejada usando o comando 'PA'.

        Args:
            stage_id (str): Identificador do eixo (ex: '1').
            position (float): Destino absoluto.
        """
        if not self.serial_port or not self.serial_port.is_open:
            return
        try:
            self.serial_port.write(f"{stage_id}PA{position}\r\n".encode('ascii'))
        except Exception as e:
            logger.error(f"Erro ao mover eixo {stage_id}: {e}")

    def stop_motion(self, stage_id: str) -> None:
        """
        Para imediatamente o movimento de um eixo usando o comando 'ST'.

        Args:
            stage_id (str): Identificador do eixo (ex: '1').
        """
        if not self.serial_port or not self.serial_port.is_open:
            return
        try:
            self.serial_port.write(f"{stage_id}ST\r\n".encode('ascii'))
        except Exception as e:
            logger.error(f"Erro ao parar eixo {stage_id}: {e}")

    def home_axis(self, stage_id: str) -> None:
        """
        Comanda o eixo a realizar a busca de sua origem física usando o comando 'OR'.

        Args:
            stage_id (str): Identificador do eixo (ex: '1').
        """
        if not self.serial_port or not self.serial_port.is_open:
            return
        try:
            # Comando de busca de origem padrão para ESP300/301
            self.serial_port.write(f"{stage_id}OR\r\n".encode('ascii'))
        except Exception as e:
            logger.error(f"Erro ao executar home no eixo {stage_id}: {e}")

    def get_axis_status(self, stage_id: str) -> str:
        """
        Consulta o estado de energia do motor para o eixo via 'MO?'.

        Args:
            stage_id (str): Identificador do eixo (ex: '1').

        Returns:
            str: 'Ready (Motor ON)', 'Disabled (Motor OFF)' ou status bruto.
        """
        if not self.serial_port or not self.serial_port.is_open:
            return "Disconnected"
        ret = self.send_command(f"{stage_id}MO?")
        if ret == "1":
            return "Ready (Motor ON)"
        elif ret == "0":
            return "Disabled (Motor OFF)"
        else:
            return f"Unknown ({ret})"

    def initialize_axis(self, stage_id: str) -> None:
        """
        No-op para ESP300/301. Não requer inicialização de grupo por software.

        Args:
            stage_id (str): Identificador do eixo.
        """
        pass

    def enable_axis(self, stage_id: str) -> None:
        """
        Liga o motor do eixo correspondente usando o comando 'MO'.

        Args:
            stage_id (str): Identificador do eixo (ex: '1').
        """
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(f"{stage_id}MO\r\n".encode('ascii'))
            except Exception as e:
                logger.error(f"Erro ao habilitar motor {stage_id}: {e}")

    def disable_axis(self, stage_id: str) -> None:
        """
        Desliga o motor do eixo correspondente usando o comando 'MF'.

        Args:
            stage_id (str): Identificador do eixo (ex: '1').
        """
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(f"{stage_id}MF\r\n".encode('ascii'))
            except Exception as e:
                logger.error(f"Erro ao desabilitar motor {stage_id}: {e}")

    def kill_axis(self, stage_id: str) -> None:
        """
        Para o movimento de forma emergencial (no-op de reinicialização para ESP).

        Args:
            stage_id (str): Identificador do eixo (ex: '1').
        """
        self.stop_motion(stage_id)
