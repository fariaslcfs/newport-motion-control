import logging
from typing import List
from .base import NewportControllerInterface

try:
    from newportxps import NewportXPS
except ImportError:
    NewportXPS = None

logger = logging.getLogger(__name__)

class XPS_Controller(NewportControllerInterface):
    """
    Controlador para XPS C8 via Ethernet (TCP/IP).
    Utiliza a biblioteca 'newportxps' para lidar com login, FTP (para leitura
    dinâmica do objects.sys) e máquina de estados.
    """
    def __init__(self):
        self.xps = None

    def connect(self, connection_string: str) -> bool:
        if NewportXPS is None:
            logger.error("A biblioteca 'newportxps' não está instalada. Execute 'pip install newportxps'")
            return False
            
        try:
            # O connection_string é o IP, ex: '192.168.254.254'
            self.xps = NewportXPS(connection_string, username='Administrator', password='Administrator')
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar no XPS C8 em {connection_string} - {e}")
            self.xps = None
            return False

    def disconnect(self) -> None:
        if self.xps:
            try:
                # Safe disconnect baseado na correção apontada no seu script
                if hasattr(self.xps, 'ftpconn') and self.xps.ftpconn is not None:
                    try:
                        self.xps.ftpconn.close()
                    except Exception:
                        pass
                if hasattr(self.xps, '_xps') and self.xps._xps is not None:
                    try:
                        if hasattr(self.xps, '_sid') and self.xps._sid is not None:
                            self.xps._xps.TCP_CloseSocket(self.xps._sid)
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Erro ao desconectar XPS C8: {e}")
            finally:
                self.xps = None

    def get_stage_list(self) -> List[str]:
        # Como o newportxps faz o download do system.ini/objects.sys via FTP no connect(), 
        # a propriedade self.xps.stages é populada 100% dinamicamente!
        if self.xps and hasattr(self.xps, 'stages') and self.xps.stages:
            return list(self.xps.stages.keys())
        
        logger.warning("A biblioteca newportxps não encontrou eixos dinamicamente.")
        return []

    def send_command(self, cmd: str, expect_response: bool = False) -> str:
        if not self.xps:
            return ""
        try:
            error, response = self.xps._xps.Send(self.xps._sid, cmd)
            if expect_response:
                return response if response else f"ErrCode: {error}"
            return f"ErrCode: {error}"
        except Exception as e:
            logger.error(f"Erro de comunicação XPS no comando {cmd}: {e}")
            return ""

    def get_current_position(self, stage_id: str) -> float:
        if not self.xps: 
            return 0.0
        try:
            return float(self.xps.get_stage_position(stage_id))
        except Exception as e:
            logger.debug(f"Falha ao ler posição do {stage_id}: {e}")
            return 0.0

    def move_absolute(self, stage_id: str, position: float) -> None:
        if self.xps:
            self.xps.move_stage(stage_id, position)

    def stop_motion(self, stage_id: str) -> None:
        if self.xps:
            # O comando kill/stop geralmente usa o nome do grupo
            group = stage_id.split('.')[0] if '.' in stage_id else stage_id
            self.xps.kill_group(group)

    def home_axis(self, stage_id: str) -> None:
        if self.xps:
            group = stage_id.split('.')[0] if '.' in stage_id else stage_id
            self.xps.home_group(group)
