"""Textos do instalador e do iniciador em portugues (Brasil) e ingles. T("chave") devolve no idioma atual."""
import locale
import os

TEXTOS = {
    "passo1": ("JOGO", "GAME"),
    "passo2": ("LOCAL", "LOCATION"),
    "passo3": ("INSTALAR", "INSTALL"),
    "passo4": ("PRONTO", "DONE"),
    "selecionar": ("Selecionar", "Select"),
    "sair": ("Sair", "Quit"),
    "marcar": ("Marcar", "Check"),
    "voltar": ("Voltar", "Back"),
    "cancelar": ("Cancelar", "Cancel"),
    "continuar": ("CONTINUAR", "CONTINUE"),
    "instalar": ("INSTALAR", "INSTALL"),
    "outro_idioma": ("ENGLISH", "PORTUGUÊS"),
    "inicio_texto": ("Instalador do port nativo para Steam Deck.\nVocê precisa da sua própria cópia do jogo de PS4 "
                     "(CUSA00004, versão 1.07). Nada do jogo é baixado.",
                     "Installer for the native Steam Deck port.\nYou need your own copy of the PS4 game "
                     "(CUSA00004, version 1.07). Nothing from the game is downloaded."),
    "creditos_por": ("PORT PARA STEAM DECK POR", "STEAM DECK PORT BY"),
    "creditos_base": ("sobre o iss_pc de HayatoG e o shadPS4", "built on HayatoG's iss_pc and shadPS4"),
    "jogo_titulo": ("ONDE ESTÁ O JOGO?", "WHERE IS THE GAME?"),
    "jogo_achei": ("Achei estes arquivos no Deck e no cartão SD. Marque o jogo e a atualização 1.07.",
                   "I found these files on the Deck and the SD card. Check the game and the 1.07 update."),
    "jogo_nada": ("Não achei os .pkg do jogo. Procure em outra pasta ou use uma pasta já extraída.",
                  "I could not find the game's .pkg files. Look in another folder or use an extracted folder."),
    "tipo_base": ("Jogo base", "Base game"),
    "tipo_update": ("Atualização", "Update"),
    "tipo_": ("Pacote", "Package"),
    "procurar": ("Procurar em outra pasta", "Look in another folder"),
    "procurar_sub": ("Pen drive, Downloads...", "USB drive, Downloads..."),
    "ja_extraido": ("Já tenho a pasta extraída", "I have the extracted folder"),
    "ja_extraido_sub": ("Com eboot.bin e sce_sys", "With eboot.bin and sce_sys"),
    "local_titulo": ("ONDE INSTALAR?", "WHERE TO INSTALL?"),
    "local_texto": ("O jogo extraído ocupa uns 32 GB. Os .pkg podem ser apagados depois, se você quiser.",
                    "The extracted game takes about 32 GB. You can delete the .pkg files afterwards if you want."),
    "ssd": ("Armazenamento interno (SSD)", "Internal storage (SSD)"),
    "ssd_sub": ("Mais rápido para carregar", "Faster loading"),
    "sd": ("Cartão microSD", "microSD card"),
    "sd_sub": ("Libera o SSD", "Keeps the SSD free"),
    "livres": ("livres", "free"),
    "sem_espaco": ("Sem espaço: precisa de 32 GB livres", "Not enough space: needs 32 GB free"),
    "recomendado": ("RECOMENDADO", "RECOMMENDED"),
    "instalando_titulo": ("INSTALANDO", "INSTALLING"),
    "etapa_port": ("Preparando o port", "Preparing the port"),
    "etapa_base": ("Extraindo o jogo base", "Extracting the base game"),
    "etapa_update": ("Aplicando a atualização 1.07", "Applying the 1.07 update"),
    "etapa_preparar": ("Preparando as opções do Deck", "Preparing the Deck settings"),
    "etapa_atalho": ("Criando o atalho na Steam", "Creating the Steam shortcut"),
    "total": ("Total", "Total"),
    "restam": ("cerca de {} min restantes", "about {} min left"),
    "tomada": ("pode deixar o Deck na tomada", "keep the Deck plugged in"),
    "pronto_titulo": ("PRONTO!", "ALL SET!"),
    "pronto_texto": ("inFAMOUS Second Son está na sua biblioteca da Steam, com capa e ícone.\nVolte ao Modo de Jogo "
                     "e abra por lá. Na primeira abertura os shaders são preparados (alguns minutos, uma vez só).",
                     "inFAMOUS Second Son is in your Steam library, with cover art and icon.\nGo back to Game Mode "
                     "and launch it there. The first launch prepares the shaders (a few minutes, only once)."),
    "pronto_menu": ("Menu do port durante o jogo: botão View (o de dois quadradinhos, à esquerda da tela).",
                    "Port menu while playing: the View button (two small squares, left of the screen)."),
    "modo_jogo": ("VOLTAR AO MODO DE JOGO", "BACK TO GAME MODE"),
    "erro_titulo": ("ALGO DEU ERRADO", "SOMETHING WENT WRONG"),
    "erro_texto": ("A instalação parou. Nada foi apagado: dá pra tentar de novo. Se repetir, abra uma issue no "
                   "GitHub com o arquivo ~/.config/infamous-ss-deck/instalador.log.",
                   "The installation stopped. Nothing was deleted: you can try again. If it happens again, open an "
                   "issue on GitHub with the file ~/.config/infamous-ss-deck/instalador.log."),
    "tentar_de_novo": ("TENTAR DE NOVO", "TRY AGAIN"),
    "atualizando": ("ATUALIZANDO", "UPDATING"),
    "atualizando_texto": ("Baixando a versão {} do port. O jogo abre logo em seguida.",
                          "Downloading version {} of the port. The game starts right after."),
}


class _T:
    lang = "pt"

    def __call__(self, chave: str) -> str:
        pt, en = TEXTOS.get(chave, (chave, chave))
        return pt if self.lang == "pt" else en


T = _T()


def idioma_inicial() -> str:
    """Portugues se o sistema estiver em portugues, senao ingles."""
    for v in (os.environ.get("LANG", ""), os.environ.get("LC_ALL", ""), (locale.getlocale()[0] or "")):
        if v.lower().startswith("pt"):
            return "pt"
    return "en"
