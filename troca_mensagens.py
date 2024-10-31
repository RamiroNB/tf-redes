import socket
from threading import Lock, Thread


def enviar_mensagem_anuncio_rotas(self):
    mensagem = self.criar_mensagem_anuncio()
    for vizinho in self.vizinhos:
        self.enviar_mensagem(vizinho, mensagem)


def criar_mensagem_anuncio(self):
    with self.bloqueio:
        pares = [
            f"@{destino}-{metrica}"
            for destino, (metrica, _) in self.tabela_roteamento.items()
        ]
    return "".join(pares)


def enviar_mensagem(self, destino, mensagem):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(mensagem.encode(), (destino, 5000))


def receber_mensagem(self):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((self.ip, 5000))
        while True:
            dados, _ = sock.recvfrom(1024)
            self.processar_mensagem(dados.decode())


def processar_mensagem(self, mensagem):
    with self.bloqueio:
        for entrada in mensagem.split("@")[1:]:
            destino, metrica = entrada.split("-")
            metrica = int(metrica)
            if (
                destino not in self.tabela_roteamento
                or metrica < self.tabela_roteamento[destino][0]
            ):
                self.tabela_roteamento[destino] = (metrica + 1, destino)
                self.enviar_mensagem_anuncio_rotas()
