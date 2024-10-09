#!/usr/bin/env python3
import logging
from controller import temperature_controller
from caproto.server import (
    pvproperty,
    PVGroup,
    ioc_arg_parser,
    run,
    SubGroup,
    template_arg_parser,
)
import asyncio
import argparse
from typing import Optional
from caproto.server.autosave import AutosaveHelper, RotatingFileManager, autosaved
from pymodbus.client import ModbusTcpClient
from pymodbus.transaction import ModbusRtuFramer
import pathlib

logging.basicConfig(filename='temp_controller_ioc.log',
                             filemode='a',
                             format='%(asctime)s - %(name)s - %(levelname)s\
                                - %(message)s',
                             level=logging.INFO)

logger = logging.getLogger(name='IOClog')

class TCPVGroup(PVGroup):
    "group of PVs for a temperature controller, controlled via ModBus-RTU over RS485 over ethernet"  

    t1_temperature = pvproperty(
        value=0.0,
        dtype=float,
        units="C",
        #precision=1,
        read_only=True,
        doc="Temperature/PV readout",
    )

    t2_temperature = pvproperty(
        value=0.0,
        dtype=float,
        units="C",
        #precision=1,
        read_only=True,
        doc="Temperature/PV readout",
    )

    t3_temperature = pvproperty(
        value=0.0,
        dtype=float,
        units="C",
        #precision=1,
        read_only=True,
        doc="Temperature/PV readout",
    )

    t1_setpoint_read = pvproperty(
        value=0,
        record="ai",
        units="C",
        #precision=1,
        read_only=True,
        doc="setpoint read back value for T1",
    )

    t2_setpoint_read = pvproperty(
        value=0,
        record="ai",
        units="C",
        #precision=1,
        read_only=True,
        doc="setpoint read back value for T2",
    )

    t3_setpoint_read = pvproperty(
        value=0,
        record="ai",
        units="C",
        #precision=1,
        read_only=True,
        doc="setpoint read back value for T3",
    )

    t1_setpoint = pvproperty(
        value=1.01,
        #record="ao",
        units="C",
        #precision=1,
        read_only=False,
        doc="setpoint/SV value",
    )

    t2_setpoint = pvproperty(
        value=1.01,
        #record="ao",
        units="C",
        #precision=1,
        read_only=False,
        doc="setpoint/SV value",
    )

    t3_setpoint = pvproperty(
        value=1.01,
        #record="ao",
        units="C",
        #precision=1,
        read_only=False,
        doc="setpoint/SV value",
    )

    t1_runmode = pvproperty(
        value=0,
        #record="ao",
        read_only=False,
        doc="Run mode value",
    )

    t2_runmode = pvproperty(
        value=0,
        #record="ao",
        read_only=False,
        doc="Run mode value",
    )

    t3_runmode = pvproperty(
        value=0,
        #record="ao",
        read_only=False,
        doc="Run mode value",
    )

    # again copying some style from the fluke ioc example
    def __init__(self, prefix, tc_configs, *args, **kwargs):
        super().__init__(prefix=prefix, *args, **kwargs)
        
        self.controllers = {}

        for tc_name, config in tc_configs.items():
            try:
                controller = temperature_controller(
                    ip = config['ip'],
                    port = config['port'],
                    serial_id = config['serial_id']
                )
                self.controllers[tc_name] = controller
                logger.info(f"Connected to {tc_name}")

            except Exception as e:
                logger.error(f'Failed to initialize {tc_name}: {e}')
                self.controllers[tc_name] = None

    #     self.add(self.update_temperatures())    

    # async def update_temperatures(self):
    #     while True: 
    #         for tc_name, controller in self.controllers.items():
    #             if controller:
    #                 temp = controller.get_temp()
    #                 logger.info(temp)
    #                 if temp is not None:
    #                     getattr(self, f"{tc_name}_temperature")._value = temp
    #                     getattr(self, f"{tc_name}_temperature").changed()

    #                     logger.info("Temperature updated: {temp} C")

    #         await asyncio.sleep(1)

    # async def update_setpoints(self):
    #     while True: 
    #         for tc_name, controller in self.controllers.items():
    #             if controller:
    #                 temp = controller.get_setpoint()
    #                 if temp is not None:
    #                     getattr(self, f"{tc_name}_setpoint")._value = temp
    #                     getattr(self, f"{tc_name}_setpoint").changed()

    #                     logger.info("Setpoint updated: {temp} C")

    #         await asyncio.sleep(1)


    # async def _download_and_update(self):
    #     "download all parameters and put them in the corresponding PVs"

    #     temperature_r = await get_setpoint(self.serial_id)
    #     await self.setpoint_read.write(temperature_r)

    #     # current temperature
    #     temperature_r = await get_temp(self.serial_id, self.client)
    #     await self.temperature.write(temperature_r)

    @t1_temperature.scan(1)
    async def t1_temperature(self, instance, async_lib):
        try:
            controller = self.controllers.get('t1')
            temp = controller.get_temp()/10
            await self.t1_temperature.write(temp)
            logger.info(f'Temperature read from T1 {temp}')
        except:
            raise
    
    @t2_temperature.scan(1)
    async def t2_temperature(self, instance, async_lib):
        try:
            controller = self.controllers.get('t2')
            temp = controller.get_temp()/10
            await self.t2_temperature.write(temp)
            logger.info(f'Temperature read from T2 is {temp}')
        except:
            raise

    @t3_temperature.scan(1)
    async def t3_temperature(self, instance, async_lib):
        try:
            controller = self.controllers.get('t3')
            temp = controller.get_temp()/10
            await self.t3_temperature.write(temp)
            logger.info(f'Temperature read from T3 is {temp}')
        except:
            raise

    @t1_setpoint.putter
    async def t1_setpoint(self, instance, value):
        #logger.debug(f'the values is {value}')
        controller = self.controllers.get('t1')
        #logger.debug(f'the values is {value}')
        if controller:
            set_point_value = controller.set_temp(value)
            if set_point_value:
                instance._value = value
                instance.changed()
                logger.info(f"T1 set to: {value} C")
        else:
            logger.error("T1 controller could not be initialized")
    

    @t2_setpoint.putter
    async def t2_setpoint(self, instance, value):
        controller = self.controllers.get('t2')
        if controller:
            set_point_value = controller.set_temp(value)

            if set_point_value:
                instance._value = value
                instance.changed()
                logger.info(f"T2 set to: {value} C")
            else:
                logger.error(f"T2 controller couldn't be set to {value}")
        
        else:
            logger.error("T2 controller could not be initialized")

    @t3_setpoint.putter
    async def t3_setpoint(self, instance, value):
        controller = self.controllers.get('t3')
        if controller:
            set_point_value = controller.set_temp(value)

            if set_point_value:
                instance._value = value
                instance.changed()
                logger.info(f"T3 set to: {value} C")
            else:
                logger.error(f"T3 controller couldn't be set to {value}")
        
        else:
            logger.error("T3 controller could not be initialized")

    @t1_runmode.putter
    async def t1_runmode(self, instance, value):
        
        controller = self.controllers.get('t1')
        if controller:
            set_point_value = controller.run_mode(value)

            if set_point_value:
                instance._value = value
                instance.changed()
                logger.info(f"T1 run mode set to: {value}")
            else:
                logger.error(f"T1 controller couldn't be set to {value}")
        
        else:
            logger.error("T1 controller could not be initialized")

    @t2_runmode.putter
    async def t2_runmode(self, instance, value):
        
        controller = self.controllers.get('t2')
        if controller:
            runmode_value = controller.run_mode(value)

            if runmode_value:
                instance._value = value
                instance.changed()
                logger.info(f"T2 run mode set to: {value}")
            else:
                logger.error(f"T2 controller couldn't be set to {value}")
        
        else:
            logger.error("T2 controller could not be initialized")

    @t3_runmode.putter
    async def t3_runmode(self, instance, value):
        
        controller = self.controllers.get('t3')
        if controller:
            runmode_value = controller.run_mode(value)

            if runmode_value:
                instance._value = value
                instance.changed()
                logger.info(f"T3 run mode set to: {value}")
            else:
                logger.error(f"T3 controller couldn't be set to {value}")
        
        else:
            logger.error("T3 controller could not be initialized")


def parse_arguments():
    
    parser = argparse.ArgumentParser(description="Arguments for Temperature Controller IOC")

    for i in range(1, 4):

        parser.add_argument(
            f"--t{i}-ip", 
            help="Hostname or IP of the network-to-serial converter", 
            required=False, 
            default='192.168.0.4',
            type=str,
        )

        parser.add_argument(
            f"--t{i}-port",
            help="Network port of the network-to-serial converter",
            default=502,
            type=int,
        )
        parser.add_argument(
            f"--t{i}-serial_id",
            help="Serial Id of the RS485 device",
            default=i,
            type=int,
        )
    # print(parser.parse_known_args())
    
    args, remaining_args = parser.parse_known_args()

    return args, remaining_args


if __name__ == "__main__":
    """ Primary command-line entry point """
   
    args, caproto_args = parse_arguments()

    ioc_options, run_options = ioc_arg_parser(argv=caproto_args, default_prefix='Temp:',
                                              desc='Temperature Controller IOC')

    tc_configs = {
        't1': {
            'ip': args.t1_ip,
            'port': args.t1_port,
            'serial_id': args.t1_serial_id
        },

        't2': {
            'ip': args.t2_ip,
            'port': args.t2_port,
            'serial_id': args.t2_serial_id
        },

        't3': {
            'ip': args.t3_ip,
            'port': args.t3_port,
            'serial_id': args.t3_serial_id
        },
    }

    ioc = TCPVGroup(prefix=ioc_options['prefix'], tc_configs=tc_configs)

    run(ioc.pvdb, **run_options)