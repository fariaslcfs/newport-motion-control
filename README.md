# Newport Motion Control

Este projeto consiste em uma interface gráfica (GUI) desenvolvida em Python e PyQt6 para controlar e automatizar estágios de translação e rotação utilizando controladoras da **Newport**. A arquitetura do projeto foi desenhada para ser modular e abstrair a complexidade de comunicação, provendo suporte nativo para os seguintes modelos:

- **ESP300 / ESP301**: Comunicação via Serial (Cabo RS232 / USB Prolific).
- **ESP302**: Comunicação via Ethernet (TCP/IP) utilizando comandos em formato ASCII padrão.
- **XPS C8**: Comunicação via Ethernet (TCP/IP) disparando comandos específicos da biblioteca de firmware XPS.

## Funcionalidades

- **Detecção Automática de Porta**: Identificação inteligente de portas COM que utilizem chips conversores Prolific.
- **Leitura em Tempo Real (Polling)**: O sistema atualiza a posição do eixo selecionado a cada 200ms na interface.
- **Movimentação Absoluta**: Deslocamento direto informando o ponto de destino.
- **Busca de Origem (Home)**: Botão de atalho para enviar o eixo selecionado para sua marca de zero de fábrica.
- **Parada de Emergência (Abort)**: Comando rápido e imediato para interromper a trajetória do controlador.
- **Envio de Comandos Customizados**: Permite o envio de comandos arbitrários e sintaxes complexas (para debugar a placa ou usar funções não mapeadas na interface gráfica) e a leitura direta das respostas.

## Pré-requisitos

Certifique-se de ter o Python 3 instalado no sistema.
Instale todas as dependências necessárias executando o comando a seguir:

```bash
pip install -r requirements.txt
```

## Como Usar

1. No terminal, navegue até a raiz do projeto (onde se encontra o `main.py`).
2. Execute a aplicação:

```bash
python main.py
```

3. Na interface gráfica:
   - Selecione a controladora no menu **Controlador**.
   - Insira o Endereço (ex: `COM3` para serial ou `192.168.0.254` para rede). Se utilizar cabos USB-Serial da Prolific, você pode utilizar o botão "Auto Detectar".
   - Clique em **Conectar**.
   - Utilize a área "Controle de Eixo" para se mover ou a área "Comando Customizado" para sintaxes de terminal.

## Geração do Executável (PyInstaller)

Para empacotar a aplicação em um arquivo executável autônomo (que não necessita do Python instalado na máquina de destino), você pode utilizar o **PyInstaller**. 

> [!NOTE]
> O PyInstaller gera binários nativos do sistema onde o comando é executado. Para gerar o executável de Windows (.exe), você deve rodar o comando no Windows; para Linux, no Ubuntu/Mint.

### 1. No Windows 10/11
Abra o PowerShell ou Prompt de Comando na raiz do projeto e execute:

```powershell
pyinstaller --noconfirm --onefile --windowed --name="NewportMotionControl" main.py
```
* O executável final será gerado na pasta `dist/NewportMotionControl.exe`.

### 2. No Linux (Ubuntu/Mint)
Instale o PyInstaller no seu ambiente, abra o terminal na raiz do projeto e execute:

```bash
pyinstaller --noconfirm --onefile --windowed --name="NewportMotionControl" main.py
```
* O binário executável final será gerado em `dist/NewportMotionControl`.
* Se necessário, certifique-se de dar permissões de execução com `chmod +x dist/NewportMotionControl` antes de executá-lo.

## Estrutura do Projeto

```text
newport-motion-control/
├── core/
│   ├── base.py                 # Interface Abstrata para Controladores
│   ├── esp_controller.py       # Lógica Serial do ESP300/301
│   ├── esp302_controller.py    # Lógica Socket do ESP302
│   └── xps_controller.py       # Lógica Socket do XPS C8
├── gui/
│   ├── __init__.py
│   └── main_window.py          # Telas, Botões e Eventos do PyQt6
├── main.py                     # Entry point da aplicação
└── README.md
```

## Tratamento de Erros e Extensibilidade
A base em `core/base.py` define os métodos obrigatórios (`connect`, `disconnect`, `move_absolute`, `get_current_position`, `stop_motion`, `home_axis`, `send_command`). Para incluir um novo modelo de placa ou braço robótico no futuro, basta criar um novo script em `core/` herdando de `NewportControllerInterface` e adicioná-lo ao menu suspenso em `main_window.py`.
