import socket
import struct
import cv2
from queue import Queue
import threading
import io
from socketserver import UDPServer, DatagramRequestHandler

dest_ip = '127.0.0.1'
# dest_ip = '154.8.225.243'
dest_port = 8008
recv_file = 'recv.jpg'
udp_listen_port = 9008
img_packet_queue = Queue(100)


def udp_recv(udp_socket):
    while True:
        try:
            data_header = udp_socket.recvfrom(8192)
            if len(data_header[0]) == 9:
                packet_video_type, packet_video_len, camera_id = struct.unpack('<BII', data_header[0])
            else:
                print('miss img packet>>>>>>>>>>>>>>>>>.......')
                continue
            data_all = b''
            once_recv_len = 548

            # 找尾
            recv_img_subpacket_dict = {}
            end_packet_content = 'end'
            end_packet_size = len(end_packet_content.encode('ascii'))
            data_next = udp_socket.recvfrom(once_recv_len)
            while not len(data_next[0]) == end_packet_size or not data_next[0].decode('ascii') == end_packet_content:
                packet_index = int.from_bytes(data_next[0][0:2], 'little')
                recv_img_subpacket_dict[packet_index] = data_next[0][2:]

                data_next = udp_socket.recvfrom(once_recv_len)

            keys_sorted = recv_img_subpacket_dict.keys()
            keys_sorted = sorted(keys_sorted)
            print(f'recv_packet_index_count: {len(keys_sorted)}')
            for item in keys_sorted:
                data_all += recv_img_subpacket_dict[item]

            img_packet_queue.put(data_all)
        except KeyboardInterrupt:
            break
        except IOError as e:
            print(str(e))


def play():
    while True:
        try:
            print('start play')
            img_packet = img_packet_queue.get()
            print(f'show img: {len(img_packet)}')
            with open(recv_file, 'wb') as recv_img_file:
                recv_img_file.write(img_packet)
                recv_img_file.flush()
                recv_img = cv2.imread(recv_file)
                cv2.imshow(str(1), recv_img)
                cv2.waitKey(20)
        except Exception:
            pass


# tcp 接收方法封装，避免一次接收不全引起其他问题
def socket_recv(tcp_socket, data_len):
    result = tcp_socket.recv(data_len)
    recv_len = len(result)
    while recv_len < data_len:
        temp_result = tcp_socket.recv(data_len-recv_len)
        recv_len += len(temp_result)
        result += temp_result
    return result


def main():
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.connect((dest_ip, dest_port))
    # 发送角色数据包
    packet_role = struct.pack('<BIB', 3, 1, 1)
    tcp_socket.send(packet_role)

    # 发送获取图像请求命令包
    packet_request = struct.pack('<BIIB', 1, 5, 1, 1)
    tcp_socket.send(packet_request)

    # 开始播放
    t = threading.Thread(target=play, args=())
    t.daemon = True
    t.start()

    # 开始接收图像数据
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((dest_ip, udp_listen_port))
    udp_recv(udp_socket)

    # 发送关闭图像命令
    packet_stop = struct.pack('<BIIB', 1, 5, 1, 0)
    tcp_socket.send(packet_stop)

    cv2.destroyAllWindows()
    tcp_socket.close()


if __name__ == "__main__":
    main()
