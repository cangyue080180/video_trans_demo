import socket
import os
import struct
from threading import Thread
import time
import cv2


class TcpClient:
    # 每个摄像头处理线程都独享一个tcp连接
    def __init__(self, server_ip, server_port, camera_id, room_id):
        self.tcp_server_ip = server_ip
        self.tcp_server_port = server_port
        self.camera_id = camera_id
        self.room_id = room_id

        self.is_stop = True
        self.is_room_video_send = False
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.connect((self.tcp_server_ip, self.tcp_server_port))

    def __socket_receive(self, data_len):
        result = self.tcp_socket.recv(data_len)
        receive_len = len(result)
        while receive_len < data_len:
            temp_result = self.tcp_socket.recv(data_len - receive_len)
            receive_len += len(temp_result)
            result += temp_result
        return result

    def send_img(self, img):
        # TODO:可考虑是否需要另起一个线程进行发送来提高性能
        if self.is_room_video_send and not self.is_stop:
            # 图片压缩为jpg格式，节省传输数据量
            # prev = cv2.resize(prev, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_NEAREST)
            send_file = str(self.camera_id) + '.jpg'
            cv2.imwrite(send_file, img)

            # 发送图像数据包头
            file_size = os.path.getsize(send_file)
            packet_header = struct.pack('<BII', 2, file_size + 4, self.camera_id)

            # 发送图像数据
            with open(send_file, 'rb') as img_file:
                if self.is_room_video_send:
                    self.tcp_socket.send(packet_header)
                    self.tcp_socket.send(img_file.read(file_size))

    def start(self):
        self.is_stop = False
        # 发送角色数据包
        packet_role = struct.pack('<BIB', 3, 1, 2)
        self.tcp_socket.send(packet_role)
        t = Thread(target=self.__receive, args=())
        t.daemon = True
        t.start()

    def stop(self):
        self.is_stop = True

    def __receive(self):
        # 等待接收图像传输命令
        while not self.is_stop:
            packet_video_request_header = self.__socket_receive(5)
            packet_video_request_type, packet_video_request_len = struct.unpack('<BI', packet_video_request_header)
            if packet_video_request_type == 1:  # 图像传输控制命令包
                room_id, video_status = struct.unpack('<IB', self.__socket_receive(5))
                if self.room_id == room_id:
                    if video_status == 1:  # 发送此房间图像
                        self.is_room_video_send = True
                    else:  # 关闭此房间图像
                        self.is_room_video_send = False
                    print(f'is_video_send: {self.is_room_video_send}')

        self.tcp_socket.close()


if __name__ == "__main__":
    # tcp_server_ip = '154.8.225.243'
    tcp_server_ip = '127.0.0.1'
    tcp_server_port = 8008
    camera_id = 1
    room_id = 1
    tcpClient = TcpClient(tcp_server_ip, tcp_server_port, camera_id, room_id)
    tcpClient.start()

    print('start capture')
    # 读取视频
    capture = cv2.VideoCapture("test.mp4")
    if capture.isOpened():
        print('capture open')
        while True:
            ret, prev = capture.read()
            print(f'ret: {ret}')
            if ret:
                tcpClient.send_img(prev)
            else:
                break
            time.sleep(0.1)

    print('stop')
    tcpClient.stop()