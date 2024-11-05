import os
import socket
import threading
import time

from dotenv import load_dotenv  # type: ignore

load_dotenv()


class Router:
    def __init__(self):
        self.ip = os.getenv("ROUTER_IP")
        neighbors = os.getenv("NEIGHBORS")
        self.neighbors = neighbors.split(",") if neighbors else []
        self.routing_table = self.initialize_table()
        self.lock = threading.Lock()
        self.last_update = {neighbor: time.time() for neighbor in self.neighbors}

    def initialize_table(self):
        table = {}
        for neighbor in self.neighbors:
            table[neighbor] = (1, neighbor)
        return table

    def print_table(self):
        with self.lock:
            print(f"\nRouting table for {self.ip}:")
            for destination, (metric, output) in self.routing_table.items():
                print(f"IP: {destination}, Metric: {metric}, Output: {output}")

    def send_message(self, destination, message):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(message.encode(), (destination, 9000))

    def create_announcement_message(self):
        with self.lock:
            pairs = [
                f"@{destination}-{metric}"
                for destination, (metric, _) in self.routing_table.items()
            ]
        return "".join(pairs)

    def send_route_announcement_message(self):
        message = self.create_announcement_message()
        for neighbor in self.neighbors:
            self.send_message(neighbor, message)

    def receive_message(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind((self.ip, 9000))
            while True:
                data, _ = sock.recvfrom(1024)
                self.process_message(data.decode())

    def process_message(self, message):
        if message.startswith("!"):
            self.process_text_message(message)
        else:
            self.update_routing_table(message)

    def update_routing_table(self, message):
        with self.lock:
            for entry in message.split("@")[1:]:
                destination, metric = entry.split("-")
                metric = int(metric)
                if (
                    destination not in self.routing_table
                    or metric < self.routing_table[destination][0]
                ):
                    self.routing_table[destination] = (metric + 1, destination)
                    self.send_route_announcement_message()

            # Update last update of routes received from neighbors
            for neighbor in self.neighbors:
                if neighbor in message:
                    self.last_update[neighbor] = time.time()

    def send_text_message(self, destination_ip, message):
        text = f"!{self.ip};{destination_ip};{message}"
        next_router = self.routing_table.get(destination_ip, (None, None))[1]

        if next_router:
            self.send_message(next_router, text)
        else:
            print(f"Route to {destination_ip} not found.")

    def process_text_message(self, message):
        parts = message[1:].split(";")
        source_ip, destination_ip, text = parts

        if self.ip == destination_ip:
            print(f"Message received from {source_ip} to {destination_ip}: {text}")
        else:
            print(f"Forwarding message from {source_ip} to {destination_ip}")
            self.send_text_message(destination_ip, text)

    def check_inactive_routers(self):
        while True:
            time.sleep(5)
            with self.lock:
                current_time = time.time()
                for neighbor, last_time in list(self.last_update.items()):
                    if current_time - last_time > 35:
                        print(f"Inactive router detected: {neighbor}. Removing routes.")
                        del self.routing_table[neighbor]
                        self.remove_routes_by_output(neighbor)

    def remove_routes_by_output(self, neighbor):
        removed_routes = [
            destination
            for destination, (_, output) in self.routing_table.items()
            if output == neighbor
        ]
        for destination in removed_routes:
            del self.routing_table[destination]

    def send_periodically(self):
        while True:
            self.send_route_announcement_message()
            self.print_table()
            time.sleep(15)

    def start(self):
        threading.Thread(target=self.send_periodically).start()
        threading.Thread(target=self.receive_message).start()
        threading.Thread(target=self.check_inactive_routers).start()


if __name__ == "__main__":
    router = Router()
    router.start()

    # Simulate sending a text message after some time
    time.sleep(5)
    router.send_text_message("192.168.1.3", "Hi, how are you?")
