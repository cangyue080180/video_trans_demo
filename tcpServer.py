# use to receive and send commands of control video transmission
from socketserver import ThreadingTCPServer, StreamRequestHandler
import struct
import enum

ai_client_list = []
desktop_client_list = []


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
        packet_role = self.__socket_receive(6)
        packet_role_type, packet_role_len, packet_role_value = struct.unpack('<BIB', packet_role)
        if packet_role_type == 0x03:  # role packet
            if packet_role_value == 0x01:  # desktop client
                self.client_role = ClientType.desktop
                desktop_client_list.append(self.wfile)
                print(f"new_desktop_client_count: {len(desktop_client_list)}")
            else:  # AI client
                self.client_role = ClientType.ai
                ai_client_list.append(self.wfile)
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
                    for desktop_client in desktop_client_list:
                        desktop_client.write(packet_data_header)
                        desktop_client.write(packet_data_content)
                elif self.client_role == ClientType.desktop:
                    for ai_client in ai_client_list:
                        ai_client.write(packet_data_header)
                        ai_client.write(packet_data_content)
            except ConnectionResetError as e:
                print(f'ConnectionResetError: {str(e)}')
                break

    def finish(self):
        # delete object which not live
        if self.client_role == ClientType.ai:
            ai_client_list.remove(self.wfile)
            print(f"now_ai_client_count: {len(ai_client_list)}")
        elif self.client_role == ClientType.desktop:
            desktop_client_list.remove(self.wfile)
            print(f"now_desktop_client_count: {len(desktop_client_list)}")
        else:
            None


if __name__ == "__main__":
    host = ''
    port = 8008
    server_endpoint = (host, port)

    server = ThreadingTCPServer(server_endpoint, MyStreamRequestHandler)
    server.serve_forever()
