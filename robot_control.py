import serial
import serial.tools.list_ports
import struct
import threading
import time
from PySide6.QtCore import Signal, QObject


class Robot(QObject):
    spd_signal = Signal(int, float)  # id, spd
    port_erro_signal = Signal()
    def __init__(self,COM_num=None):
        super(Robot, self).__init__()
        self.read_lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.ser = serial.Serial()
        self.ser.baudrate = 115200
        self.ser.timeout = 0.05
        self.gear_level  = 0.2
        self.now_rotate = 0
        if COM_num is not None:
            self.ser.port = COM_num
            self.ser.open()
            self.position = self.get_position()
        else:
            self.ser.port = None
            self.position = None
        self.port_list = []

    def get_position(self):
        '''查询电机位置信息'''
        buffer = None
        if self.ser.isOpen:
            self.read_lock.acquire()
            self.write_lock.acquire()
            try:
                self.ser.read_all()
                msg = b"?\r\n"
                self.ser.write(msg)
                a = self.ser.read()
                for _ in range(10):
                    b = self.ser.read()
                    if a == b":" and b == b":":
                        buffer = self.ser.read(16)
                        break
                    else:
                        a = b
            except BaseException as e:
                print(e)
                self.port_erro_signal.emit()
            self.read_lock.release()
            self.write_lock.release()
        
        if buffer is not None:
            x, y = struct.unpack("2q", buffer)
            x = x / 100000 * 1.875
            y = y / 100000 * 1.875
        else:
            x, y = None, None
        return (x, y)

    def set_speed_freq(self, id, freq):
        """设置步进电机的驱动频率"""
        msg = f":{id} {round(freq, 2)}\r\n".encode()
        if self.ser.isOpen():
            self.write_lock.acquire()
            try:
                self.ser.write(msg)
            except:
                self.port_erro_signal.emit()
            self.write_lock.release()
        else:
            print(msg)
    
    def set_speed(self, id, spd):
        """设置某一轴的速度"""
        if id != 2:
            freq = (spd/3) * 160
            spd = self.gear_level * spd
            self.spd_signal.emit(id, spd)
            self.set_speed_freq(id, freq)
        else:
            self.now_rotate += spd * 0.001
            self.now_rotate = 20.0 if self.now_rotate > 20 else self.now_rotate
            self.now_rotate = -20.0 if self.now_rotate < -20 else self.now_rotate
            freq = int(self.now_rotate * 1600)
            self.spd_signal.emit(id, self.now_rotate)
            self.set_speed_freq(id, freq)
    
    def scan_ports(self):
        """查询有哪些串口可用，返回一个列表"""
        options = serial.tools.list_ports.comports()
        ports = [i.device for i in options]
        names = [i.description for i in options]
        self.port_list = ports
        return ports, names
    
    def open_robot_port(self, port):
        """在输入的串口号上打开机器人通讯"""
        if (self.ser.isOpen() and port != self.ser.port):
            self.ser.close()
        self.ser.port = port
        if not self.ser.isOpen():
            try:
                self.ser.open()
            except:
                self.port_erro_signal.emit()
    
    def close_robot_port(self):
        """关闭机器人串口"""
        if self.ser.isOpen():
            self.ser.close()
    
    def plus_gear_level(self):
        """加快机器人的速度"""
        self.gear_level += 0.2
        if self.gear_level > 1:
            self.gear_level = 1
        return self.gear_level
    
    def minus_gear_level(self):
        """降低机器人的速度"""
        self.gear_level -= 0.2
        if self.gear_level < 0.2:
            self.gear_level = 0.2
        return self.gear_level
    
    def write_ser(self, content):
        """直接写内容到机器人的串口"""
        if isinstance(content, bytes):
            content = content
        elif isinstance(content, str):
            content = content.encode()
        else:
            return False
        if self.ser.isOpen():
            self.write_lock.acquire()
            try:
                self.ser.write(content)
            except:
                self.port_erro_signal.emit()
            self.write_lock.release()
            return True
        else:
            return False
        
    def run_spd_time(self, id, spd, time_s):
        self.set_speed(id, spd)
        time.sleep(time_s)
        self.set_speed(id, 0)
    
    def step(self, id, dis, spd=5):
        """通过线程定时定速运转机器人"""
        tim = dis / spd
        thr = threading.Thread(target=lambda: self.run_spd_time(id, 3200, tim))
        thr.start()
    
    def all_stop(self):
        """停止所有的电机运动"""
        for i in range(3):
            self.now_rotate = 0
            self.set_speed_freq(i,0)
    
    def flush_ser(self):
        """清除串口缓冲区的内容"""
        if self.ser.isOpen():
            self.read_lock.acquire()
            try:
                self.ser.read_all()
            except:
                self.port_erro_signal.emit()
            self.read_lock.release()
    
    def change_disable_state(self, id, state):
        """更改介入器械的锁定-启用状态"""
        pass
            
        
        



if __name__ == "__main__":
    pass