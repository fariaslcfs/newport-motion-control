import logging
from typing import List
from .base import NewportControllerInterface, AxisState

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
        """
        Conecta ao controlador XPS C8 via Ethernet (TCP/IP).

        Inicializa a biblioteca 'newportxps' que carrega configurações do hardware.

        Args:
            connection_string (str): Endereço IP do controlador XPS (ex: '192.168.0.254').

        Returns:
            bool: True se conectado e logado com sucesso, False caso contrário.
        """
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
        """
        Fecha as conexões de soquetes e FTP do controlador XPS C8 com segurança.
        """
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
        """
        Retorna a lista de eixos/estágios disponíveis detectados dinamicamente via FTP.

        Returns:
            List[str]: Nomes dos eixos no formato 'Grupo.Eixo' (ex: ['Group1.Pos']).
        """
        # Como o newportxps faz o download do system.ini/objects.sys via FTP no connect(), 
        # a propriedade self.xps.stages é populada 100% dinamicamente!
        if self.xps and hasattr(self.xps, 'stages') and self.xps.stages:
            return list(self.xps.stages.keys())
        
        logger.warning("A biblioteca newportxps não encontrou eixos dinamicamente.")
        return []

    def send_command(self, cmd: str, expect_response: bool = False) -> str:
        """
        Envia um comando customizado bruto para o socket de baixo nível do XPS.

        Args:
            cmd (str): O comando bruto.
            expect_response (bool): Se deve retornar a string de resposta ou código de erro.

        Returns:
            str: Resposta do XPS ou string com código de erro.
        """
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
        """
        Obtém a posição atual do estágio consultando a biblioteca 'newportxps'.

        Args:
            stage_id (str): Identificador do estágio ('Grupo.Eixo').

        Returns:
            float: Posição física ou 0.0 em caso de falha.
        """
        if not self.xps: 
            return 0.0
        try:
            return float(self.xps.get_stage_position(stage_id))
        except Exception as e:
            logger.debug(f"Falha ao ler posição do {stage_id}: {e}")
            return 0.0

    def move_absolute(self, stage_id: str, position: float) -> None:
        """
        Executa um movimento absoluto para o estágio especificado.

        Args:
            stage_id (str): Identificador do estágio ('Grupo.Eixo').
            position (float): Coordenada absoluta de destino.
        """
        if self.xps:
            self.xps.move_stage(stage_id, position)

    def stop_motion(self, stage_id: str) -> None:
        """
        Interrompe imediatamente o movimento chamando 'kill_group' para o grupo do estágio.

        Args:
            stage_id (str): Identificador do estágio ('Grupo.Eixo').
        """
        if self.xps:
            # O comando kill/stop geralmente usa o nome do grupo
            group = stage_id.split('.')[0] if '.' in stage_id else stage_id
            self.xps.kill_group(group)

    def home_axis(self, stage_id: str) -> None:
        """
        Inicia a busca de origem (homing) para o grupo correspondente ao estágio.
        Verifica o estado da máquina e executa as pré-condições necessárias (Kill, Init).
        """
        if self.xps and hasattr(self.xps, '_xps'):
            group = stage_id.split('.')[0] if '.' in stage_id else stage_id
            
            # Consultar status numérico
            err, status_code = self.xps._xps.GroupStatusGet(self.xps._sid, group)
            if err != 0:
                raise RuntimeError(f"Não foi possível obter o estado do grupo para Homing (Err: {err})")
                
            # Inteligência de Estados
            # 0 a 9 = Not Initialized
            if 0 <= status_code <= 9:
                logger.info(f"Grupo {group} não inicializado. Inicializando primeiro...")
                self.xps.initialize_group(group)
            # 20 a 29 = Ready, 40 a 49 = Disabled. (Precisam voltar para Not Referenced)
            elif (20 <= status_code <= 29) or (40 <= status_code <= 49):
                logger.info(f"Grupo {group} já estava Pronto/Desativado. Aplicando Kill -> Init para forçar re-homing...")
                self.xps.kill_group(group)
                self.xps.initialize_group(group)
                
            # Agora tenta o homing normal
            try:
                self.xps.home_group(group)
            except Exception as e:
                logger.warning(f"GroupHomeSearch padrão falhou para {group} ({e}). Tentando fallback para Steppers...")
                try:
                    err, _ = self.xps._xps.GroupHomeSearchAndRelativeMove(self.xps._sid, group, 0.0)
                    if err != 0:
                        raise RuntimeError(f"Falha no fallback de homing. XPS ErrorCode: {err}")
                except Exception as fallback_e:
                    raise RuntimeError(f"Falha absoluta na rotina de homing: {fallback_e}")

    def get_axis_status(self, stage_id: str) -> AxisState:
        """
        Lê o estado da máquina de estados do grupo a que pertence o estágio
        e mapeia rigorosamente para o AxisState padronizado.
        """
        if not self.xps or not hasattr(self.xps, '_xps'):
            return AxisState.UNKNOWN
            
        try:
            group = stage_id.split('.')[0] if '.' in stage_id else stage_id
            err, status_code = self.xps._xps.GroupStatusGet(self.xps._sid, group)
            
            if err != 0:
                return AxisState.ERROR
                
            if 0 <= status_code <= 9:
                return AxisState.UNINITIALIZED
            elif 10 <= status_code <= 19:
                return AxisState.NOT_REFERENCED
            elif 20 <= status_code <= 29:
                return AxisState.READY
            elif 40 <= status_code <= 49:
                return AxisState.DISABLED
            elif 43 <= status_code <= 48: # Movendo, homing, ou executando algo (algumas placas XPS retornam 44 como homing in progress/moving)
                # O XPS tem um estado MOVING em 44. Ajuste fino de subestados numéricos pode variar, mas 44 e afins:
                return AxisState.MOVING
            else:
                # Tratar emergências (50-59) ou falhas
                return AxisState.ERROR

        except Exception as e:
            logger.debug(f"Falha ao ler status numérico do grupo {stage_id}: {e}")
            return AxisState.UNKNOWN

    def initialize_axis(self, stage_id: str) -> None:
        """
        Inicializa o grupo de movimento associado ao estágio.

        Args:
            stage_id (str): Identificador do estágio.
        """
        if self.xps:
            group = stage_id.split('.')[0] if '.' in stage_id else stage_id
            try:
                self.xps.initialize_group(group)
            except Exception as e:
                logger.error(f"Erro ao inicializar grupo {group}: {e}")
                raise

    def enable_axis(self, stage_id: str) -> None:
        """
        Habilita a potência do motor (Motion Enable) para o grupo associado ao estágio.

        Args:
            stage_id (str): Identificador do estágio.
        """
        if self.xps:
            group = stage_id.split('.')[0] if '.' in stage_id else stage_id
            try:
                self.xps.enable_group(group)
            except Exception as e:
                logger.error(f"Erro ao habilitar grupo {group}: {e}")
                raise

    def disable_axis(self, stage_id: str) -> None:
        """
        Desabilita a potência do motor (Motion Disable) para o grupo associado ao estágio.

        Args:
            stage_id (str): Identificador do estágio.
        """
        if self.xps:
            group = stage_id.split('.')[0] if '.' in stage_id else stage_id
            try:
                self.xps.disable_group(group)
            except Exception as e:
                logger.error(f"Erro ao desabilitar grupo {group}: {e}")
                raise

    def kill_axis(self, stage_id: str) -> None:
        """
        Chama 'kill_group' no grupo associado ao estágio para parar movimentos e limpar erros.

        Args:
            stage_id (str): Identificador do estágio.
        """
        if self.xps:
            group = stage_id.split('.')[0] if '.' in stage_id else stage_id
            try:
                self.xps.kill_group(group)
            except Exception as e:
                logger.error(f"Erro ao matar/parar grupo {group}: {e}")
                raise
