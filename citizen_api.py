""" Printer staff. """
import re
import subprocess
from typing import Tuple, Optional

from PIL.Image import Image, BILINEAR
from escpos.printer import Usb

from text_to_img import TEXT_PROCESSOR


def get_usb_device_id():
    """ Get CITIZEN ST-S2000 device id. Printer must be connected. """
    device_re = re.compile(r"Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$", re.I)
    df = subprocess.check_output("lsusb").decode()
    for i in df.split('\n'):
        info = device_re.match(i)
        if info and info.group("tag") == "Citizen Thermal Printer ":
            return info.group("id")
    else:
        raise ValueError("Printer not found")


def get_device_io(device_id: str) -> Tuple[int, int]:
    """
    Parse two lines:
        bEndpointAddress     0x81  EP 1 IN
        bEndpointAddress     0x02  EP 2 OUT
    Returns:
        usb in addr
        usb out addr
    """
    device_re = re.compile(r"\s+bEndpointAddress\s+(?P<addr>[\w\d]+)\s+EP\s+\d\s+(?P<dst>\w+)\s*$", re.I)
    df = subprocess.check_output(f"lsusb -v -d {device_id}".split(' ')).decode()
    res = {}
    for i in df.split('\n'):
        info = device_re.match(i)
        if info:
            res[info.group("dst")] = int(info.group("addr"), base=16)
    return res["IN"], res["OUT"]


def get_usb_connection() -> Usb:
    """ Obtain usb connection. Need sudo privileges. """
    device_id = get_usb_device_id()
    id_vendor, id_product = map(lambda x: int(x, base=16), device_id.split(":"))
    in_, out_ = get_device_io(device_id)
    printer = Usb(id_vendor, id_product, 0, in_, out_)
    return printer


PRINTER = get_usb_connection()


class NothingToPrint(ValueError):
    pass


CITIZEN_CT_S2000_WIDTH = 600


def resize_img(img: Image) -> Image:
    """
    Resize images for printer boundaries.

    Args:
        img: input img

    Returns:
        resized img
    """
    new_size = (CITIZEN_CT_S2000_WIDTH, int(img.size[1] / img.size[0] * CITIZEN_CT_S2000_WIDTH))
    return img.resize(new_size, resample=BILINEAR)


def citizen_print_msg(text: Optional[str], img: Optional[Image], user_name: str) -> None:
    """
    Print text+image pair.

    Args:
        text: text to print
        img: img to print
        user_name: user signature
    """
    if not text and not img:
        raise NothingToPrint

    images_to_print = []
    if img:
        images_to_print.append(resize_img(img))
    if text:
        images_to_print.append(resize_img(TEXT_PROCESSOR.compile_text(text)))

    for img_ in images_to_print:
        PRINTER.image(img_)
        PRINTER.text("\n")
    PRINTER.text(f"@{user_name}\n")
    PRINTER.cut()


if __name__ == '__main__':
    res = get_usb_connection()
    print(res)
