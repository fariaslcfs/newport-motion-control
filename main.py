"""
Módulo de inicialização principal da aplicação Newport Motion Control.
Configura os logs básicos, inicializa a aplicação Qt6 e abre a tela de controle.
"""
import sys
import logging
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    """
    Função principal de inicialização da GUI e inicialização de loggers.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    app = QApplication(sys.argv)
    
    # Ativa o estilo Fusion (flat, acessível e nativo do Qt)
    app.setStyle("Fusion")
    
    # Ajusta a fonte global para melhorar a legibilidade e acessibilidade
    font = app.font()
    font.setPointSize(11)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
