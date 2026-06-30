import socket
import logging
from typing import List
from .base import NewportControllerInterface

logger = logging.getLogger(__name__)

class ESP302_Controller(NewportControllerInterface):
    """
    Controlador para ESP302 via Ethernet (TCP/IP).
    O protocolo de comandos é essencialmente o mesmo do ESP300/301,
    porém empacotado sobre Socket TCP ao invés de Serial.
    """
    def __init__(self):
        self.sock = None
        self.port = 5001

    def connect(self, connection_string: str) -> bool:
        # connection_string é o IP, ex: '192.168.0.254'
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(1.0)
            self.sock.connect((connection_string, self.port))
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar no ESP302 em {connection_string}:{self.port} - {e}")
            self.sock = None
            return False

    def disconnect(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Erro ao desconectar ESP302: {e}")
            finally:
                self.sock = None

    def get_stage_list(self) -> List[str]:
        # Em implementações reais, você pode consultar o controlador,
        # mas mantemos o padrão de 3 eixos assumidos para o ESP.
        return ["1", "2", "3"]

    def send_command(self, cmd: str) -> str:
        if not self.sock:
            return ""
        
        try:
            # Envia comando com \r\n (CRLF) padrão Newport
            self.sock.sendall(f"{cmd}\r\n".encode('ascii'))
            
            # Se for uma query (termina com ?), precisamos ler a resposta
            if '?' in cmd:
                response = self.sock.recv(1024).decode('ascii').strip()
                return response
            return ""
        except socket.timeout:
            logger.debug(f"Timeout ao aguardar resposta de {cmd}")
            return ""
        except Exception as e:
            logger.error(f"Erro de comunicação no comando {cmd}: {e}")
            return ""

    def get_current_position(self, stage_id: str) -> float:
        ret = self.send_command(f"{stage_id}TP?")
        try:
            return float(ret)
        except ValueError:
            logger.debug(f"Falha ao converter posição: '{ret}'")
            return 0.0

    def move_absolute(self, stage_id: str, position: float) -> None:
        self.send_command(f"{stage_id}PA{position}")

    def stop_motion(self, stage_id: str) -> None:
        self.send_command(f"{stage_id}ST")

    def home_axis(self, stage_id: str) -> None:
        # Busca origem (Search for Home)
        self.send_command(f"{stage_id}OR")
