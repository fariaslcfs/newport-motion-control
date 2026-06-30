# core/base.py
import abc
from typing import List, Dict, Any

class NewportControllerInterface(abc.ABC):
    """
    Interface unificada para controladores Newport.
    Garante que a GUI funcione de forma idêntica para Sockets (XPS/ESP302)
    e conexões Seriais (ESP300/301).
    """

    @abc.abstractmethod
    def connect(self, connection_string: str) -> bool:
        """
        XPS/ESP302: 'connection_string' será o IP (ex: '192.168.0.254')
        ESP300/301: 'connection_string' será a porta COM/TTY (ex: 'COM3' ou '/dev/ttyUSB0')
        """
        pass

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Fecha as conexões físicas de Socket ou Serial com segurança."""
        pass

    @abc.abstractmethod
    def get_stage_list(self) -> List[str]:
        """Retorna uma lista com os nomes dos eixos/estágios disponíveis."""
        pass

    @abc.abstractmethod
    def get_current_position(self, stage_id: str) -> float:
        """
        Retorna a posição atual do eixo.
        XPS: Consulta via get_stage_position.
        ESP300: Envia comando ASCII '{eixo}TP?' e faz o parse do retorno.
        """
        pass

    @abc.abstractmethod
    def move_absolute(self, stage_id: str, position: float) -> None:
        """
        Move o eixo para uma posição absoluta.
        Trata internamente as diferenças de inicialização e comandos (ex: 1PA vs move_stage).
        """
        pass

    @abc.abstractmethod
    def stop_motion(self, stage_id: str) -> None:
        """Para imediatamente o movimento do eixo selecionado (Abort/Kill)."""
        pass

    @abc.abstractmethod
    def home_axis(self, stage_id: str) -> None:
        """Executa a rotina de busca de origem (Home) do eixo."""
        pass

    @abc.abstractmethod
    def send_command(self, cmd: str) -> str:
        """Envia um comando customizado para a controladora e retorna a resposta (se houver)."""
        pass