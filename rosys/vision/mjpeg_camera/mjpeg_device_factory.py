from collections.abc import Callable

from .axis_mjpeg_device import AxisMjpegDevice
from .mjpeg_device import MjpegDevice
from .motec_mjpeg_device import MotecMjpegDevice
from .vendors import VendorType, mac_to_vendor


class MjpegDeviceFactory:
    @staticmethod
    def create(mac: str, ip: str, *,
               index: int | None = None,
               username: str | None = None,
               password: str | None = None,
               control_port: int | None = None,
               on_new_image: Callable[[bytes], None]) -> MjpegDevice:

        if mac_to_vendor(mac) == VendorType.AXIS:
            return AxisMjpegDevice(mac, ip, index=index, username=username, password=password, on_new_image=on_new_image)

        if mac_to_vendor(mac) == VendorType.MOTEC:
            return MotecMjpegDevice(mac, ip, username=username, password=password, control_port=control_port, on_new_image=on_new_image)

        raise ValueError(f'Unknown vendor for mac="{mac}"')
