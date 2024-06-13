#!/usr/bin/env python3
import logging
from caproto.server import (
    pvproperty,
    PVGroup,
    ioc_arg_parser,
    run,
    SubGroup,
    template_arg_parser,
)
import asyncio
from typing import Optional
from caproto.server.autosave import AutosaveHelper, RotatingFileManager, autosaved
from pymodbus.client import ModbusTcpClient
from pymodbus.transaction import ModbusRtuFramer
import pathlib

logger = logging.getLogger("caproto")


def get_temp(serial_id: int, client):
    ''' Reads temperature from the RS485 client using the device serial_id'''
    
    temperature = client.read_holding_registers(1, slave=serial_id)

    temperature = temperature.registers[0]

    return temperature


def get_setpoint(serial_id: int, client):
    ''' Reads the temperature setpoint from the RS485 client using the device serial_id'''

    set_point = client.read_holding_registers(0, slave=serial_id)

    set_point = set_point.registers[0]

    return set_point


def set_temp(temp_value: float, serial_id: int, client):
    ''' Writes the temperature setpoint to the RS485 device using the device's serial_id'''

    set_point = client.write_register(0x0001, temp_value, slave=serial_id)

    return print(f'The temperature controller id: {serial_id} has been set to {temp_value} degree C')


def run_mode(mode: int, serial_id: int, client):
    '''
    Changes the temperature controller run value to on or off 
    '''

    temp_mode = client.write_register(0x0084, mode, slave=serial_id)

    return print(f'The mode of temperature controller {serial_id} has been change to {mode}')


class TCPVGroup(PVGroup):
    "group of PVs for a temperature controller, controlled via ModBus-RTU over RS485 over ethernet"  

    # again copying some style from the fluke ioc example
    def __init__(self, *args, host, port, serial_id, **kwargs):
        super().__init__(*args, **kwargs)
        # note port is second argument of host.. see startup..
        self.host = host
        self.port = port
        self.serial_id = serial_id
        self.client =  ModbusTcpClient(self.host, port=self.port, framer = ModbusRtuFramer, timeout = 10)
        print(self.client)
    
    async def _download_and_update(self):
        "download all parameters and put them in the corresponding PVs"

        temperature_r = await get_setpoint(self.serial_id)
        await self.setpoint_read.write(temperature_r)

        # current temperature
        temperature_r = await get_temp(self.serial_id, self.client)
        await self.temperature.write(temperature_r)

    temperature = pvproperty(
        value=get_temp(1, client=ModbusTcpClient('192.168.0.4', port=502, framer=ModbusRtuFramer,
                                                 timeout= 10)),
        record="ai",
        units="C",
        #precision=1,
        read_only=True,
        doc="temperature/PV readout",
    )

    setpoint_read = pvproperty(
        value=1.01,
        record="ai",
        units="C",
        #precision=1,
        read_only=True,
        doc="setpoint read back value",
    )

    setpoint = pvproperty(
        value=1.01,
        record="ao",
        units="C",
        #precision=1,
        read_only=False,
        doc="setpoint/SV value",
    )

    read_mode = pvproperty(
        value=0,
        record="ao",
        read_only=False,
        doc="Run mode value",
    )

    @setpoint.putter
    async def setpoint(self, instance, value):
        serial_id = self.serial_id
        logger.debug(f'setting temperature setpoint of serialId {serial_id} to value: {value}')
        await set_temp(value, serial_id, self.client)

    @read_mode.putter
    async def read_mode(self, instance, value):
        serial_id = self.serial_id.value
        logger.debug(f'settig temp controller run_mode of serialId {serial_id} to value: {value}')
        await run_mode(value, serial_id)


def create_ioc(
        prefix: str, *, host: str, port: int, serial_id: int, autosave: str, **ioc_options
) -> TCPVGroup:
    """ Create a new arduino IOC """
    autosave = pathlib.Path(autosave).resolve().absolute()

    class TCMain(TCPVGroup):
        autosave_helper = SubGroup(
            AutosaveHelper, file_manager=RotatingFileManager(autosave)
        )
        autosave_helper.filename = autosave
    print(prefix)
    return TCPVGroup(prefix=prefix, host=host, port=port, serial_id=serial_id, **ioc_options)


def create_parser():
    parser, split_args = template_arg_parser(
        default_prefix="temp:",
        desc="PID Temp clontroller",
        supported_async_libs=("asyncio",),
    )

    parser.add_argument(
        "--host", 
        help="Hostname or IP of the network-to-serial converter", 
        required=True, 
        default='192.168.0.4',
        type=str,
    )

    parser.add_argument(
        "--port",
        help="Network port of the network-to-serial converter",
        default=502,
        type=int,
    )
    parser.add_argument(
        "--serial_id",
        help="Serial Id of the RS485 device",
        default=1,
        type=int,
    )
    parser.add_argument(
        "--autosave",
        help="Path to the autosave file",
        default="autosave.json",
        type=str,
    )
    return parser, split_args


if __name__ == "__main__":
    """ Primary command-line entry point """
    parser, split_args = create_parser()
    args = parser.parse_args()
    ioc_options, run_options = split_args(args)

    ioc = create_ioc(
        autosave=args.autosave, host=args.host, port=args.port, serial_id=args.serial_id, **ioc_options
    )

    run(ioc.pvdb, **run_options)