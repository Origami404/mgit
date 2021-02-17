
def sha_raw_to_str(raw: bytes) -> str:
    '''将以 20 位大端序 unsigned int 储存的 sha1 转化成字符串'''
    # 大端序
    sha1_int = int.from_bytes(raw, 'big')
    # 去除前导的 0x
    return hex(sha1_int)[2:]