import os
import socket
import threading
import time

from dotenv import load_dotenv  # Ensure you have python-dotenv installed

load_dotenv()  # Load environment variables from a .env file


class Router:
    def __init__(self):
        self.ip = os.getenv("ROUTER_IP")
        neighbors = os.getenv("NEIGHBORS")
        self.neighbors = neighbors.split(",") if neighbors else []
        self.routing_table = self.initialize_table()
        self.last_update = {neighbor: time.time() for neighbor in self.neighbors}

        print(f"Router initialized with IP: {self.ip}")
        print(f"Neighbors: {self.neighbors}")

        # Announce the router to its neighbors
        self.announce_router()

    def initialize_table(self):
        table = {}
        for neighbor in self.neighbors:
            table[neighbor] = (1, neighbor)
        print("Initial routing table created.")
        return table

    def print_table(self):
        print(f"\nRouting table for {self.ip}:")
        for destination, (metric, output) in self.routing_table.items():
            print(f"IP: {destination}, Metric: {metric}, Output: {output}")

    def send_message(self, destination, message):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(message.encode(), (destination, 9000))
            print(f"Sent message to {destination}: {message}")
        except OSError as e:
            print(f"Error sending message to {destination}: {e}")

    def create_announcement_message(self):
        pairs = [
            f"@{destination}-{metric}"
            for destination, (metric, _) in self.routing_table.items()
        ]
        return "".join(pairs)

    def send_route_announcement_message(self):
        message = self.create_announcement_message()
        for neighbor in self.neighbors:
            self.send_message(neighbor, message)
        print("Route announcement sent to all neighbors.")

    def receive_messages(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind((self.ip, 9000))
            sock.settimeout(1)  # Set a timeout for non-blocking receive
            while True:
                try:
                    data, _ = sock.recvfrom(1024)
                    self.process_message(data.decode())
                except socket.timeout:
                    continue
                except OSError as e:
                    print(f"Error receiving message: {e}")

    def process_message(self, message):
        if message.startswith("!"):
            self.process_text_message(message)
        elif message.startswith("*"):
            self.process_router_announcement(message)
        else:
            self.update_routing_table(message)

    def update_routing_table(self, message):
        updated = False
        current_destinations = set()
        for entry in message.split("@")[1:]:
            destination, metric = entry.split("-")
            metric = int(metric)
            current_destinations.add(destination)
            if (
                destination not in self.routing_table
                or metric < self.routing_table[destination][0]
            ):
                self.routing_table[destination] = (metric + 1, destination)
                updated = True
                print(
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
                print(f"Removed route to {destination} as it is no longer advertised.")

        # Update last update of routes received from neighbors
        for neighbor in self.neighbors:
            if neighbor in message:
                self.last_update[neighbor] = time.time()

        if updated:
            self.send_route_announcement_message()

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

    def process_router_announcement(self, message):
        new_router_ip = message[1:]
        if new_router_ip not in self.routing_table:
            self.routing_table[new_router_ip] = (1, new_router_ip)
            print(f"Added new router {new_router_ip} to routing table.")
            self.send_route_announcement_message()

    def check_inactive_routers(self):
        while True:
            time.sleep(5)
            current_time = time.time()
            for neighbor, last_time in list(self.last_update.items()):
                if current_time - last_time > 35:
                    if neighbor in self.routing_table:
                        print(f"Inactive router detected: {neighbor}. Removing routes.")
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
            print(f"Removed route to {destination} via inactive router {neighbor}.")

    def announce_router(self):
        announcement = f"*{self.ip}"
        for neighbor in self.neighbors:
            self.send_message(neighbor, announcement)
        print("Router announcement sent to all neighbors.")

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
    # Start the router operations in separate threads
    threading.Thread(target=router.receive_messages, daemon=True).start()
    threading.Thread(target=router.send_periodic_announcements, daemon=True).start()
    threading.Thread(target=router.check_inactive_routers, daemon=True).start()

    # Start the user input handling in the main thread
    router.user_input_thread()
