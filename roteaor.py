import socket
import threading
import time


class Roteador:
    def __init__(self, ip, conf_file):
        self.ip = ip
        self.vizinhos = self.carregar_vizinhos(conf_file)
        self.tabela_roteamento = self.inicializar_tabela()
        self.bloqueio = threading.Lock()

    def carregar_vizinhos(self, conf_file):
        vizinhos = []
        with open(conf_file, "r") as file:
            for line in file:
                vizinhos.append(line.strip())
        return vizinhos

    def inicializar_tabela(self):
        tabela = {}
        for vizinho in self.vizinhos:
            tabela[vizinho] = (1, vizinho)
        return tabela

    def imprimir_tabela(self):
        with self.bloqueio:
            print(f"Tabela de roteamento para {self.ip}:")
            for destino, (metrica, saida) in self.tabela_roteamento.items():
                print(f"IP: {destino}, Métrica: {metrica}, Saída: {saida}")
            print("\n")


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

    def iniciar(self):
        threading.Thread(target=self.enviar_periodicamente).start()
        threading.Thread(target=self.receber_mensagem).start()

    def enviar_periodicamente(self):
        while True:
            self.enviar_mensagem_anuncio_rotas()
            self.imprimir_tabela()
            time.sleep(15)


if __name__ == "__main__":
    ip_roteador = "192.168.1.1"  # Exemplo
    arquivo_configuracao = "config.txt"
    roteador = Roteador(ip_roteador, arquivo_configuracao)
    roteador.iniciar()
