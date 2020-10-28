# use to receive and send commands of control video transmission
from socketserver import ThreadingTCPServer, StreamRequestHandler, ThreadingUDPServer, DatagramRequestHandler, BaseRequestHandler
import struct
import enum
import threading
import socket

ai_client_list = {}
desktop_client_list = {}


class ClientType(enum.Enum):
    none = 0,
    desktop = 1,
    ai = 2


class MyStreamRequestHandler(StreamRequestHandler):
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
        print(self.client_address)
        packet_role = self.__socket_receive(6)
        packet_role_type, packet_role_len, packet_role_value = struct.unpack('<BIB', packet_role)
        if packet_role_type == 0x03:  # role packet
            if packet_role_value == 0x01:  # desktop client
                self.client_role = ClientType.desktop
                desktop_client_list[self.client_address] = self.wfile
                print(f"new_desktop_client_count: {len(desktop_client_list)}")
            else:  # AI client
                self.client_role = ClientType.ai
                ai_client_list[self.client_address] = self.wfile
                print(f"new_ai_client_count: {len(ai_client_list)}")
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
                    for desktop_client_wfile in desktop_client_list.values():
                        desktop_client_wfile.write(packet_data_header)
                        desktop_client_wfile.write(packet_data_content)
                elif self.client_role == ClientType.desktop:
                    for ai_client_wfile in ai_client_list.values():
                        ai_client_wfile.write(packet_data_header)
                        ai_client_wfile.write(packet_data_content)
            except ConnectionResetError as e:
                print(f'ConnectionResetError: {str(e)}')
                break

    def finish(self):
        # delete object which not live
        if self.client_role == ClientType.ai:
            ai_client_list.pop(self.client_address)
            print(f"now_ai_client_count: {len(ai_client_list)}")
        elif self.client_role == ClientType.desktop:
            desktop_client_list.pop(self.client_address)
            print(f"now_desktop_client_count: {len(desktop_client_list)}")
        else:
            None


class MyUdpHandler(BaseRequestHandler):
    """
    use to receive and send video
    receive from ai client
    send to desktop client
    """
    def handle(self):
        msg, sock = self.request
        data = msg
        print(f'recv_img: {len(data)} from {self.client_address}')
        # resp = 'ok'
        # sock.sendto(resp.encode('ascii'), self.client_address)
        for desktop_client in desktop_client_list.keys():
            new_udp_remote_address = (desktop_client[0], 9008)
            udp_socket.sendto(data, new_udp_remote_address)
            print(f'send_img: {len(data)} to {new_udp_remote_address}')


def start_udp(udp_server_ip, udp_server_port):
    udp_server = ThreadingUDPServer((udp_server_ip, udp_server_port), MyUdpHandler)
    udp_server.serve_forever()


udp_socket = None # use to send packet
if __name__ == "__main__":
    host = ''
    tcp_server_port = 8008
    tcp_server_endpoint = (host, tcp_server_port)

    udp_port = 9009
    bind_address = (host, udp_port)
    udp_task = threading.Thread(target=start_udp, args=bind_address)
    udp_task.start()

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    tcp_server = ThreadingTCPServer(tcp_server_endpoint, MyStreamRequestHandler)
    tcp_server.serve_forever()

    print('server stop')
