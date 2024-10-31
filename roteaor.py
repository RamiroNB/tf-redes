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
