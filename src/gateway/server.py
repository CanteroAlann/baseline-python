import logging
import multiprocessing
from multiprocessing.connection import wait
import socket
import time


class GatewayServer:

    def __init__(self, server_socket, client_handler, *, max_clients=4,
                 shutdown_timeout=5.0, process_context=None):
        if max_clients < 1 or shutdown_timeout <= 0:
            raise ValueError("max_clients and shutdown_timeout must be positive")
        self.socket = server_socket
        self.client_handler = client_handler
        self.max_clients = max_clients
        self.shutdown_timeout = shutdown_timeout
        self.context = process_context or multiprocessing.get_context("spawn")
        self.processes = []
        self.running = True

    def stop(self, signum=None, frame=None):
        self.running = False

    def run(self):
        self.socket.settimeout(0.5)
        try:
            while self.running:
                self._cleanup_finished_clients()
                if len(self.processes) >= self.max_clients:
                    wait([process.sentinel for process in self.processes], timeout=0.5)
                    continue
                try:
                    client_socket, address = self.socket.accept()
                except socket.timeout:
                    continue
                try:
                    if not self.running:
                        break
                    process = self.context.Process(
                        target=self.client_handler, args=(client_socket,),
                    )
                    try:
                        process.start()
                    except (OSError, RuntimeError):
                        process.close()
                        logging.exception("Could not start client process for %s", address)
                        continue
                    self.processes.append(process)
                    logging.info("Client connected address=%s pid=%s", address, process.pid)
                finally:
                    # Close only the parent's desc, shutdown would affect the child
                    client_socket.close()
        finally:
            self.socket.close()
            self._stop_clients()

    def _cleanup_finished_clients(self):
        active = []
        for process in self.processes:
            if process.is_alive():
                active.append(process)
            else:
                process.join()
                logging.info("Client process exited pid=%s exitcode=%s", process.pid, process.exitcode)
                process.close()
        self.processes = active

    def _stop_clients(self):
        for process in self.processes:
            if process.is_alive():
                process.terminate()
        deadline = time.monotonic() + self.shutdown_timeout
        for process in self.processes:
            process.join(max(0, deadline - time.monotonic()))
        for process in self.processes:
            if process.is_alive():
                process.kill()
                process.join()
            process.close()
        self.processes.clear()
