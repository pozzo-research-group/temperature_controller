from pymodbus.client import ModbusTcpClient
from pymodbus.transaction import ModbusRtuFramer
from requests.exceptions import ConnectionError
import logging

logging.basicConfig(filename='controller.log',
                             filemode='a',
                             format='%(asctime)s - %(name)s - %(levelname)s\
                                - %(message)s',
                             level=logging.INFO)

logger = logging.getLogger(name='Controllerlog')

class temperature_controller:

    def __init__(self, ip, port, serial_id):
        self.ip = ip
        self.port = port
        self.serial_id = serial_id

        self.client = ModbusTcpClient(self.ip, port=self.port, framer=ModbusRtuFramer,
                                      timeout=10)
        
        self.logger = logging.getLogger(self.__class__.__name__)

        if self.client.connect():
            self.logger.info("Connected to temperature controller at {ip} with \
                             serial_id {serial_id}")
        else:
            raise ConnectionError(f"Cannot connect to the contoller at {ip} with \
                                  serial_id {serial_id}")
        
    
    def get_temp(self):

        ''' Reads temperature from the RS485 client using the device serial_id'''
            
        temperature = self.client.read_holding_registers(1, slave=self.serial_id)

        temperature = temperature.registers[0]

        return temperature
    

    def get_setpoint(self):

        ''' Reads the temperature setpoint from the RS485 client using the device serial_id'''

        set_point = self.client.read_holding_registers(0, slave=self.serial_id)

        set_point = set_point.registers[0]

        return set_point
    

    def set_temp(self, temperature):

        ''' Writes the temperature setpoint to the RS485 device using the device's serial_id'''

        temperature = int(temperature)
        
        set_point = self.client.write_register(0, temperature, slave=self.serial_id)

        return self.logger.info(f'The temperature controller id: {self.serial_id} \
                                has been set to {temperature} degree C')
    

    def run_mode(self, mode):
        '''
        Changes the temperature controller run value to on or off 
        '''

        mode = int(mode)
        
        temp_mode = self.client.write_register(84, mode,
                                               slave=self.serial_id)

        return self.logger.info(f'The mode of temperature controller \
                                {self.serial_id} has been change to {mode}')

