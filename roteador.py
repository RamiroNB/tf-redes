import os
import socket
import threading
import time

from dotenv import load_dotenv  # type: ignore

load_dotenv()


class Roteador:
    def __init__(self):
        self.ip = os.getenv("ROUTER_IP")
        neighbors = os.getenv("NEIGHBORS")
        self.vizinhos = neighbors.split(",") if neighbors else []
        self.tabela_roteamento = self.inicializar_tabela()
        self.bloqueio = threading.Lock()
        self.ultima_atualizacao = {vizinho: time.time() for vizinho in self.vizinhos}

    def inicializar_tabela(self):
        tabela = {}
        for vizinho in self.vizinhos:
            tabela[vizinho] = (1, vizinho)
        return tabela

    def imprimir_tabela(self):
        with self.bloqueio:
            print(f"\nTabela de roteamento para {self.ip}:")
            for destino, (metrica, saida) in self.tabela_roteamento.items():
                print(f"IP: {destino}, Métrica: {metrica}, Saída: {saida}")

    def enviar_mensagem(self, destino, mensagem):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(mensagem.encode(), (destino, 9000))

    def criar_mensagem_anuncio(self):
        with self.bloqueio:
            pares = [
                f"@{destino}-{metrica}"
                for destino, (metrica, _) in self.tabela_roteamento.items()
            ]
        return "".join(pares)

    def enviar_mensagem_anuncio_rotas(self):
        mensagem = self.criar_mensagem_anuncio()
        for vizinho in self.vizinhos:
            self.enviar_mensagem(vizinho, mensagem)

    def receber_mensagem(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind((self.ip, 9000))
            while True:
                dados, _ = sock.recvfrom(1024)
                self.processar_mensagem(dados.decode())

    def processar_mensagem(self, mensagem):
        if mensagem.startswith("!"):
            self.processar_mensagem_texto(mensagem)
        else:
            self.atualizar_tabela_roteamento(mensagem)

    def atualizar_tabela_roteamento(self, mensagem):
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

            # Atualizar última atualização de rotas recebidas dos vizinhos
            for vizinho in self.vizinhos:
                if vizinho in mensagem:
                    self.ultima_atualizacao[vizinho] = time.time()

    def enviar_mensagem_texto(self, ip_destino, mensagem):
        texto = f"!{self.ip};{ip_destino};{mensagem}"
        prox_roteador = self.tabela_roteamento.get(ip_destino, (None, None))[1]

        if prox_roteador:
            self.enviar_mensagem(prox_roteador, texto)
        else:
            print(f"Rota para {ip_destino} não encontrada.")

    def processar_mensagem_texto(self, mensagem):
        partes = mensagem[1:].split(";")
        ip_origem, ip_destino, texto = partes

        if self.ip == ip_destino:
            print(f"Mensagem recebida de {ip_origem} para {ip_destino}: {texto}")
        else:
            print(f"Repasse da mensagem de {ip_origem} para {ip_destino}")
            self.enviar_mensagem_texto(ip_destino, texto)

    def verificar_roteadores_inativos(self):
        while True:
            time.sleep(5)
            with self.bloqueio:
                tempo_atual = time.time()
                for vizinho, ultimo_tempo in list(self.ultima_atualizacao.items()):
                    if tempo_atual - ultimo_tempo > 35:
                        print(
                            f"Roteador inativo detectado: {vizinho}. Removendo rotas."
                        )
                        del self.tabela_roteamento[vizinho]
                        self.remover_rotas_por_saida(vizinho)

    def remover_rotas_por_saida(self, vizinho):
        rotas_removidas = [
            destino
            for destino, (_, saida) in self.tabela_roteamento.items()
            if saida == vizinho
        ]
        for destino in rotas_removidas:
            del self.tabela_roteamento[destino]

    def enviar_periodicamente(self):
        while True:
            self.enviar_mensagem_anuncio_rotas()
            self.imprimir_tabela()
            time.sleep(15)

    def iniciar(self):
        threading.Thread(target=self.enviar_periodicamente).start()
        threading.Thread(target=self.receber_mensagem).start()
        threading.Thread(target=self.verificar_roteadores_inativos).start()


if __name__ == "__main__":
    roteador = Roteador()
    roteador.iniciar()

    # Simulação de envio de mensagem de texto após um tempo
    time.sleep(5)
    roteador.enviar_mensagem_texto("192.168.1.3", "Oi tudo bem?")
