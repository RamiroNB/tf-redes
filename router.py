import logging
import logging.handlers
import os
import socket
import threading
import time
from queue import Queue

from dotenv import load_dotenv

load_dotenv()

# Configure logging
log_queue = Queue()
queue_handler = logging.handlers.QueueHandler(log_queue)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(queue_handler)

file_handler = logging.FileHandler("router.log", mode="w")
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

listener = logging.handlers.QueueListener(log_queue, file_handler)
listener.start()


def log_message(message, level="info"):
    if level == "info":
        logger.info(message)
    elif level == "warning":
        logger.warning(message)
    elif level == "error":
        logger.error(message)


class Router:
    def __init__(self):
        self.ip = os.getenv("ROUTER_IP")
        neighbors = os.getenv("NEIGHBORS")
        self.neighbors = neighbors.split(",") if neighbors else []
        self.routing_table = self.initialize_table()
        self.last_update = {neighbor: time.time() for neighbor in self.neighbors}

        log_message(f"Router initialized with IP: {self.ip}")
        log_message(f"Neighbors: {self.neighbors}")

        # Announce the router to its neighbors
        self.announce_router()

    def initialize_table(self):
        table = {}
        for neighbor in self.neighbors:
            table[neighbor] = (1, neighbor)
        log_message("Initial routing table created.")
        return table

    def print_table(self):
        log_message(f"----ROUTING TABLE FOR: {self.ip}:")
        log_message("-------------------------------")

        for destination, (metric, output) in self.routing_table.items():
            log_message(f"IP: {destination}, Metric: {metric}, Output: {output}")
        log_message("--------------------------------")

    def send_message(self, destination, message):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(message.encode(), (destination, 9000))
            log_message(f"Sent message to {destination}: {message}")
        except OSError as e:
            log_message(f"Error sending message to {destination}: {e}", level="error")

    def create_announcement_message(self):
        pairs = [
            f"@{destination}-{metric}"
            for destination, (metric, _) in self.routing_table.items()
        ]
        # Ensure the message is not empty
        return "".join(pairs) if pairs else "@"

    def send_route_announcement_message(self):
        message = self.create_announcement_message()
        for neighbor in self.neighbors:
            self.send_message(neighbor, message)
        log_message("Route announcement SENT TO ALL NEIGHBORS.")

    def receive_messages(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind((self.ip, 9000))
            sock.settimeout(1)  # Set a timeout for non-blocking receive
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    sender_ip = addr[0]
                    log_message(f"Received message from {sender_ip}: {data.decode()}")
                    if sender_ip in self.neighbors:
                        self.last_update[sender_ip] = time.time()
                        log_message(
                            f"Updated last update time for neighbor: {sender_ip}"
                        )
                    self.process_message(data.decode())
                except socket.timeout:
                    continue
                except OSError as e:
                    log_message(f"Error receiving message: {e}", level="error")

    def process_message(self, message):
        if message.startswith("!"):
            self.process_text_message(message)
        elif message.startswith("*"):
            self.process_router_announcement(message)
        else:
            self.update_routing_table(message)

    def update_routing_table(self, message):
        log_message(f"Updating routing table with message: {message}")
        updated = False
        current_destinations = set()
        for entry in message.split("@")[1:]:
            if not entry:
                continue
            destination, metric = entry.split("-")
            metric = int(metric)
            current_destinations.add(destination)

            if destination == self.ip:
                continue

            if (
                destination not in self.routing_table
                or metric < self.routing_table[destination][0]
            ):
                self.routing_table[destination] = (metric + 1, destination)
                updated = True

                log_message("--------------------------------")
                log_message(
                    f"Updated route to {destination} with metric {metric + 1} via {destination}"
                )

        # Remove routes that are no longer advertised
        for destination in list(self.routing_table.keys()):
            if (
                destination not in current_destinations
                and destination not in self.neighbors
            ):
                del self.routing_table[destination]
                updated = True
                log_message(
                    f"Removed route to {destination} as it is no longer advertised."
                )

        for neighbor in self.neighbors:
            if neighbor in message:
                self.last_update[neighbor] = time.time()
                log_message(f"Updated last update time for neighbor: {neighbor}")

        if updated:
            self.send_route_announcement_message()

    def send_text_message(self, destination_ip, message):
        text = f"!{self.ip};{destination_ip};{message}"
        next_router = self.routing_table.get(destination_ip, (None, None))[1]

        if next_router:
            self.send_message(next_router, text)
        else:
            log_message(f"Route to {destination_ip} not found.", level="warning")

    def process_text_message(self, message):
        parts = message[1:].split(";")
        source_ip = parts[0]
        try:
            if source_ip in self.neighbors:
                self.last_update[source_ip] = time.time()
                log_message(f"Updated last update time for source IP: {source_ip}")

            destination_ip = parts[1]
            text = parts[2]

            if self.ip == destination_ip:
                log_message(
                    f"MESSAGE RECEIVED FROM {source_ip} TO {destination_ip}: \n --------------- {text} --------------- \n",
                    level="warning",
                )
            else:
                log_message(f"Forwarding message from {source_ip} to {destination_ip}")
                self.send_text_message(destination_ip, text)
        except:
            log_message(f"Error processing text message: {message}", level="error")

    def process_router_announcement(self, message):
        new_router_ip = message[1:]
        log_message(f"Processing router announcement from: {new_router_ip}")
        if new_router_ip not in self.routing_table:
            self.routing_table[new_router_ip] = (1, new_router_ip)
            log_message(f"Added new router {new_router_ip} to routing table.")
            self.send_route_announcement_message()

    def check_inactive_routers(self):
        while True:
            time.sleep(5)
            current_time = time.time()
            for neighbor, last_time in list(self.last_update.items()):
                if current_time - last_time > 35:
                    if neighbor in self.routing_table:
                        log_message(
                            f"Inactive router detected: {neighbor}. Removing routes."
                        )
                        del self.routing_table[neighbor]
                        self.remove_routes_by_output(neighbor)
                    del self.last_update[neighbor]

    def remove_routes_by_output(self, neighbor):
        removed_routes = [
            destination
            for destination, (_, output) in self.routing_table.items()
            if output == neighbor
        ]
        for destination in removed_routes:
            del self.routing_table[destination]
            log_message(
                f"Removed route to {destination} via inactive router {neighbor}."
            )

    def announce_router(self):
        announcement = f"*{self.ip}"
        for neighbor in self.neighbors:
            self.send_message(neighbor, announcement)
        log_message("Router announcement sent to all neighbors.")

    def send_periodic_announcements(self):
        while True:
            time.sleep(15)
            self.send_route_announcement_message()
            self.print_table()

    def user_input_thread(self):
        while True:
            destination_ip = input("Enter the destination IP: ")
            message = input("Enter the message: ")
            self.send_text_message(destination_ip, message)


if __name__ == "__main__":
    router = Router()
    threading.Thread(target=router.receive_messages, daemon=True).start()
    threading.Thread(target=router.send_periodic_announcements, daemon=True).start()
    threading.Thread(target=router.check_inactive_routers, daemon=True).start()
    router.user_input_thread()
