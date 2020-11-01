# use to receive and send commands of control video transmission
from socketserver import ThreadingTCPServer, StreamRequestHandler
import struct
import enum
from queue import Queue
import threading
import datetime

ai_client_list = []  # use to store all connecting ai servers
desktop_client_list = []  # use to store all the connecting desktop clients
ai_client_packet_buffer = Queue(100)
desktop_client_packet_buffer = Queue(10)


class ClientType(enum.Enum):
    none = 0,
    desktop = 1,
    ai = 2


def get_time_now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class MyStreamRequestHandler(StreamRequestHandler):
    last_packet = b''  # use to store the last packet received from desktop client

    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)
        self.client_role = ClientType.none

    def __socket_receive(self, data_len):
        result = self.rfile.read(data_len)
        receive_len = len(result)
        while receive_len < data_len:
            temp_result = self.rfile.read(data_len - receive_len)
            receive_len += len(temp_result)
            result += temp_result
        return result

    def handle(self):
        # receive role packet
        packet_role = self.__socket_receive(6)
        packet_role_type, packet_role_len, packet_role_value = struct.unpack('<BIB', packet_role)
        if packet_role_type == 0x03:  # role packet
            if packet_role_value == 0x01:  # desktop client
                self.client_role = ClientType.desktop
                desktop_client_list.append(self.wfile)
                print(f"{get_time_now()} new_desktop_client from {self.client_address}")
            else:  # AI client
                self.client_role = ClientType.ai
                # send last packet to the new connect ai client,
                # so the connecting desktop clients can auto get the video when ai server restart
                if len(desktop_client_list) > 0:
                    self.wfile.write(MyStreamRequestHandler.last_packet)
                ai_client_list.append(self.wfile)
                print(f"{get_time_now()} new_ai_client from {self.client_address}")
        else:
            return  # not right packet

        # receive packet and send to target
        while True:
            try:
                # receive packet header
                packet_data_header = self.__socket_receive(5)
                packet_data_type, packet_data_len = struct.unpack('<BI', packet_data_header)
                # receive packet content
                packet_data_content = self.__socket_receive(packet_data_len)
                if self.client_role == ClientType.ai:
                    ai_client_packet_buffer.put(packet_data_header+packet_data_content)
                elif self.client_role == ClientType.desktop:  # send video control packets to ai servers
                    MyStreamRequestHandler.last_packet = packet_data_header + packet_data_content
                    desktop_client_packet_buffer.put(packet_data_header+packet_data_content)
            except ConnectionResetError:
                break  # if use break,the connection will disconnect, we don't like it
            except BrokenPipeError:
                break
            except OSError:
                break

        try:
            # delete object which not live
            if self.client_role == ClientType.ai:
                ai_client_list.remove(self.wfile)
                print(f"{get_time_now()} ai_client_disconnect at {self.client_address} now_count: {len(ai_client_list)}")
            elif self.client_role == ClientType.desktop:
                desktop_client_list.remove(self.wfile)
                print(f"{get_time_now()} desktop_client_disconnect at {self.client_address} now_count: {len(desktop_client_list)}")
        except ValueError:
            pass


def send_ai_packets_to_desktop():
    while not is_stop:
            data = ai_client_packet_buffer.get()
            for desktop_client in desktop_client_list:  # send video packets to desktop clients
                try:
                    desktop_client.write(data)
                except BrokenPipeError:
                    remove_item(desktop_client_list, desktop_client)
                except OSError:
                    remove_item(desktop_client_list, desktop_client)


def send_desktop_packets_to_ai():
    while not is_stop:
        data = desktop_client_packet_buffer.get()
        for ai_client in ai_client_list:
            try:
                ai_client.write(data)
            except BrokenPipeError:
                remove_item(ai_client_list, ai_client)
            except OSError:
                remove_item(ai_client_list, ai_client)


def remove_item(item_list, item):
    try:
        item_list.remove(item)
    except ValueError:
        pass


is_stop = False
if __name__ == "__main__":
    host = ''
    port = 8008
    server_endpoint = (host, port)

    task1 = threading.Thread(target=send_desktop_packets_to_ai, args=())
    task1.daemon = True
    task1.start()

    task2 = threading.Thread(target=send_ai_packets_to_desktop, args=())
    task2.daemon = True
    task2.start()

    server = ThreadingTCPServer(server_endpoint, MyStreamRequestHandler)
    server.serve_forever()

    is_stop = True
