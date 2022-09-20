import logging
import json
import asyncio
import time

from homeassistant.exceptions import HomeAssistantError
_LOGGER = logging.getLogger(__name__)

command_seq_number:int = 0

async def get_device_info(ip: str, deviceId: str) -> dict[str, str]:
    return await _send_command(ip, {"commandId":"checkStatus", "deviceId": deviceId, "commandType":"QUERY_DEVICE_INFO"})

async def get_device_states(ip: str, deviceId: str) -> dict[str, str]:
    return await _send_command(ip, {"commandId":"checkStatus", "deviceId": deviceId, "commandType":"QUERY_DEVICE_STATES"})

"""
Turns on the light or adjusts temperature and brightness.

Brightness range is 0 - 100.
Color temperature is in Kelvins, 2600-6000
"""
async def turn_on(ip: str, deviceId: str, brightness:int|None = None, temperature:int|None = None) -> dict[str, str]:
    return await _turn_on_off(ip, deviceId, True, brightness, temperature)

async def turn_off(ip: str, deviceId: str) -> dict[str, str]:
    return await _turn_on_off(ip, deviceId, False)

async def _turn_on_off(ip: str, deviceId: str, on: bool, brightness:int|None = None, temperature:int|None = None) -> dict[str, str]:
    commands = { "commands": [{"ON": on}] }
    if brightness is not None:
        commands["commands"].append({"BRIGHTNESS": brightness})
    if temperature is not None:
        commands["commands"].append({"COLOR": {"TEMPERATURE": temperature}})
    return await _send_command(ip, {"deviceId": deviceId, "commandType":"EXECUTE", "commands": commands})

async def _send_command(ip:str, data:dict[str, str]):
    global command_seq_number
    command_seq_number = command_seq_number + 1
    data["commandId"] = f"hass-{command_seq_number}"
    _LOGGER.info(f"Sending command {data} to {ip}")
    data = json.dumps(data)
    try :
        reader, writer = await asyncio.open_connection(ip, 3333)
        writer.write(bytes(data, encoding="utf-8"))
        await writer.drain()

        try:
            len = int.from_bytes(await reader.read(4), byteorder="big")
            if len > 0 and len < 8192:
                received = await reader.read(len)
                received = received.decode("utf-8")
                _LOGGER.info(f"Received {received}")
            else:
                raise WrongId
        finally:
            writer.close()
            await writer.wait_closed()
    except IOError as e:
        raise CannotConnect

    return json.loads(received)

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class WrongId(HomeAssistantError):
    """Error to indicate there is invalid auth."""