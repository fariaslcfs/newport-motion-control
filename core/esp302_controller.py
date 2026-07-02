import socket
import logging
from typing import List
from .base import NewportControllerInterface, AxisState

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
        """
        Conecta ao controlador ESP302 via Socket Ethernet (TCP/IP).

        Args:
            connection_string (str): O endereço IP do controlador (ex: '192.168.0.254').

        Returns:
            bool: True se conectado com sucesso, False caso contrário.
        """
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
        """
        Fecha o socket de conexão do ESP302 de forma segura.
        """
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Erro ao desconectar ESP302: {e}")
            finally:
                self.sock = None

    def get_stage_list(self) -> List[str]:
        """
        Identifica dinamicamente os eixos conectados consultando 'ID?' de 1 a 3.

        Returns:
            List[str]: Lista contendo identificadores de eixos encontrados (ex: ['1', '2']).
        """
        # Consulta dinamicamente os eixos de 1 a 3 (máximo comum do ESP302)
        active_stages = []
        for i in range(1, 4):
            stage = str(i)
            # O comando ID? retorna a identificação do estágio conectado.
            ret = self.send_command(f"{stage}ID?")
            if ret and not ret.upper().startswith("ERROR"):
                active_stages.append(stage)
        
        if active_stages:
            return active_stages
            
        logger.warning("Nenhum eixo detectado dinamicamente no ESP302. Retornando padrão.")
        return ["1", "2", "3"]

    def send_command(self, cmd: str) -> str:
        """
        Envia comando ASCII de baixo nível via socket TCP/IP.

        Se for um comando de consulta (contendo '?'), lê e retorna a resposta.

        Args:
            cmd (str): O comando Newport (sem CRLF).

        Returns:
            str: Resposta do controlador ou string vazia.
        """
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
        """
        Lê a posição atual do eixo consultando '{stage_id}TP?'.

        Args:
            stage_id (str): Identificador do eixo (ex: '1').

        Returns:
            float: Posição do eixo ou 0.0 em caso de falha.
        """
        ret = self.send_command(f"{stage_id}TP?")
        try:
            return float(ret)
        except ValueError:
            logger.debug(f"Falha ao converter posição: '{ret}'")
            return 0.0

    def move_absolute(self, stage_id: str, position: float) -> None:
        """
        Move o eixo para uma coordenada absoluta usando '{stage_id}PA{coord}'.

        Args:
            stage_id (str): Identificador do eixo (ex: '1').
            position (float): Posição de destino absoluta.
        """
        self.send_command(f"{stage_id}PA{position}")

    def stop_motion(self, stage_id: str) -> None:
        """
        Para imediatamente o movimento do eixo usando o comando '{stage_id}ST'.

        Args:
            stage_id (str): Identificador do eixo.
        """
        self.send_command(f"{stage_id}ST")

    def home_axis(self, stage_id: str) -> None:
        """
        Comanda o eixo a realizar a busca de origem usando '{stage_id}OR'.

        Args:
            stage_id (str): Identificador do eixo.
        """
        # Busca origem (Search for Home)
        self.send_command(f"{stage_id}OR")

    def get_axis_status(self, stage_id: str) -> AxisState:
        """
        Consulta se o motor do eixo está ligado enviando '{stage_id}MO?'.
        Mapeia para AxisState.READY ou AxisState.DISABLED.
        """
        if not self.sock:
            return AxisState.UNKNOWN
        ret = self.send_command(f"{stage_id}MO?")
        if ret == "1":
            return AxisState.READY
        elif ret == "0":
            return AxisState.DISABLED
        else:
            return AxisState.UNKNOWN

    def initialize_axis(self, stage_id: str) -> None:
        """
        No-op para ESP302. Não requer inicialização de grupo por software.

        Args:
            stage_id (str): Identificador do eixo.
        """
        pass

    def enable_axis(self, stage_id: str) -> None:
        """
        Liga o motor do eixo correspondente usando '{stage_id}MO'.

        Args:
            stage_id (str): Identificador do eixo (ex: '1').
        """
        self.send_command(f"{stage_id}MO")

    def disable_axis(self, stage_id: str) -> None:
        """
        Desliga o motor do eixo correspondente usando '{stage_id}MF'.

        Args:
            stage_id (str): Identificador do eixo (ex: '1').
        """
        self.send_command(f"{stage_id}MF")

    def kill_axis(self, stage_id: str) -> None:
        """
        Para o movimento de forma emergencial (no-op de reinicialização para ESP).

        Args:
            stage_id (str): Identificador do eixo (ex: '1').
        """
        self.stop_motion(stage_id)
