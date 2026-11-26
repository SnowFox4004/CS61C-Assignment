#!/usr/bin/env python3
"""
ppm2png.py - 把 P3 格式的 ASCII PPM 图片转换成 PNG
用法:
    ./ppm2png.py input.ppm            # 输出 input.png
    ./ppm2png.py input.ppm out.png    # 指定输出路径
"""

import sys
import os
import zlib
import struct


def read_ppm(path):
    """解析 P3 ASCII PPM 文件，返回 (width, height, pixels)。

    pixels 是扁平列表 [r, g, b, r, g, b, ...]，按行优先排列。
    支持 # 注释行（出现在任意位置都可以）。
    """
    with open(path, "r") as f:
        content = f.read()

    # 去掉 # 开始的注释（直到行尾）
    lines = []
    for line in content.splitlines():
        if "#" in line:
            line = line[: line.index("#")]
        lines.append(line)

    tokens = " ".join(lines).split()
    if not tokens:
        raise ValueError("空的 PPM 文件")

    if tokens[0] != "P3":
        raise ValueError(f"不支持的文件格式: {tokens[0]!r}（需要 P3）")

    width = int(tokens[1])
    height = int(tokens[2])
    maxval = int(tokens[3])

    if maxval != 255:
        raise ValueError(f"只支持 maxval=255，得到 {maxval}")

    pixels = [int(x) for x in tokens[4:]]
    expected = width * height * 3
    if len(pixels) != expected:
        raise ValueError(
            f"像素数量不对: 期望 {expected} 个值，实际 {len(pixels)} 个"
        )

    return width, height, pixels


def write_png(path, width, height, pixels):
    """把 RGB 像素写成 8-bit truecolor PNG 文件。"""

    # 每一行开头要加一个 filter byte (0 = None)
    raw = bytearray()
    row_bytes = width * 3
    for y in range(height):
        raw.append(0)
        start = y * row_bytes
        raw.extend(bytes(pixels[start:start + row_bytes]))

    def chunk(typ, data):
        body = typ + data
        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    # IHDR: width, height, bit depth=8, color type=2 (RGB),
    #       compression=0, filter=0, interlace=0
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 9)

    png = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")

    with open(path, "wb") as f:
        f.write(png)


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(f"用法: {argv[0]} input.ppm [output.png]")
        return 1

    in_path = argv[1]
    if len(argv) >= 3:
        out_path = argv[2]
    else:
        out_path = os.path.splitext(in_path)[0] + ".png"

    w, h, pixels = read_ppm(in_path)
    write_png(out_path, w, h, pixels)
    print(f"已生成 {out_path}  ({w} x {h})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
