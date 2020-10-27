import socket
import struct
import cv2
import threading

# dest_ip = '127.0.0.1'
dest_ip = '154.8.225.243'
dest_port = 8008
recv_file = 'recv.jpg'


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

    num = 0
    # 接收图像数据
    while True:
        try:
            packet_video_header = socket_recv(tcp_socket, 9)
            packet_video_type, packet_video_len, camera_id = struct.unpack('<BII', packet_video_header)
            if packet_video_type == 2:
                video_image_bytes = socket_recv(tcp_socket, packet_video_len-4)
                print(f'recv_img_len: {len(video_image_bytes)}')
                with open(recv_file, 'wb') as recv_img_file:
                    recv_img_file.write(video_image_bytes)
                    recv_img_file.flush()
                    recv_img = cv2.imread(recv_file)
                    cv2.imshow(str(camera_id), recv_img)
                    cv2.waitKey(20)
        except KeyboardInterrupt:
            break
        except ConnectionError:
            break
    cv2.destroyAllWindows()

    # 发送关闭图像命令
    packet_stop = struct.pack('<BIIB', 1, 5, 1, 0)
    tcp_socket.send(packet_stop)

    tcp_socket.close()


if __name__ == "__main__":
    main()
