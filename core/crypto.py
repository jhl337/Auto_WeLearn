import base64
import time
from typing import List

def to_hex_byte_array(byte_array: bytes) -> str:
    """将字节数组转换为十六进制字符串"""
    return "".join([f"{byte:02x}" for byte in byte_array])

def generate_cipher_text(password: str) -> List[str]:
    """
    生成加密后的密码
    Returns:
        List[str]: [加密后的密码, 时间戳]
    """
    T0 = int(round(time.time() * 1000))
    P = password.encode("utf-8")
    V = (T0 >> 16) & 0xFF

    for byte in P:
        V ^= byte

    remainder = V % 100
    T1 = int((T0 // 100) * 100 + remainder)
    P1 = to_hex_byte_array(P)
    S = f"{T1}*" + P1
    S_encoded = S.encode("utf-8")
    E = base64.b64encode(S_encoded).decode("utf-8")

    return [E, str(T1)]
