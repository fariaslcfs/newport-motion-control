import socket
import logging
from typing import List
from .base import NewportControllerInterface

logger = logging.getLogger(__name__)

class XPS_Controller(NewportControllerInterface):
    """
    Controlador para XPS C8 via Ethernet (TCP/IP).
    O XPS geralmente possui uma API baseada em métodos complexos (via biblioteca TCL/C/Python).
    Esta é uma implementação básica Socket para enviar os comandos ASCII nativos.
    """
    def __init__(self):
        self.sock = None
        self.port = 5001

    def connect(self, connection_string: str) -> bool:
        # connection_string é o IP
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(1.0)
            self.sock.connect((connection_string, self.port))
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar no XPS C8 em {connection_string}:{self.port} - {e}")
            self.sock = None
            return False

    def disconnect(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Erro ao desconectar XPS C8: {e}")
            finally:
                self.sock = None

    def get_stage_list(self) -> List[str]:
        # Tenta obter a lista de objetos (grupos/posicionadores) dinamicamente do XPS C8
        ret = self.send_command("ObjectsListGet()", expect_response=True)
        
        if ret:
            # Geralmente a resposta vem no formato: "0, Group1, Group2, Group1.Pos"
            parts = ret.split(',')
            if len(parts) > 1 and parts[0] == "0":
                # Extrai apenas os nomes válidos, ignorando o código de erro inicial '0'
                objects = [obj.strip() for obj in parts[1:] if obj.strip()]
                if objects:
                    return objects
        
        # Fallback de segurança se o controlador não responder corretamente
        logger.warning("Não foi possível ler a lista de eixos dinamicamente. Retornando lista padrão.")
        return ["Group1", "Group2", "Group3"]

    def send_command(self, cmd: str, expect_response: bool = False) -> str:
        if not self.sock:
            return ""
        
        try:
            # XPS usa formato string terminada sem precisar obrigatoriamente de \r\n,
            # mas vamos manter o padrão ASCII seguro
            self.sock.sendall(f"{cmd}\r\n".encode('ascii'))
            
            if expect_response:
                response = self.sock.recv(1024).decode('ascii').strip()
                return response
            return ""
        except socket.timeout:
            logger.debug(f"Timeout ao aguardar resposta do XPS para o comando: {cmd}")
            return ""
        except Exception as e:
            logger.error(f"Erro de comunicação XPS no comando {cmd}: {e}")
            return ""

    def get_current_position(self, stage_id: str) -> float:
        # O comando real pode variar dependendo se é Grupo ou Positioner.
        # Ex: GroupPositionCurrentGet(GroupName, double *CurrentPosition) -> retorna "0, position"
        # Mapeando de forma simplificada:
        ret = self.send_command(f"GroupPositionCurrentGet({stage_id})", expect_response=True)
        try:
            # Em geral, retorna "CódigoDeErro, Posição" -> ex: "0, 10.5"
            parts = ret.split(',')
            if len(parts) >= 2:
                return float(parts[1])
            return float(ret)
        except ValueError:
            logger.debug(f"Falha ao converter posição XPS: '{ret}'")
            return 0.0

    def move_absolute(self, stage_id: str, position: float) -> None:
        self.send_command(f"GroupMoveAbsolute({stage_id}, {position})")

    def stop_motion(self, stage_id: str) -> None:
        self.send_command(f"GroupMoveAbort({stage_id})")

    def home_axis(self, stage_id: str) -> None:
        self.send_command(f"GroupHomeSearch({stage_id})")
