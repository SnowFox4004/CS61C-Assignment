#!/usr/bin/env python3
"""
ppm_tool.py - 处理 P3 ASCII PPM 图片的工具（纯 Python，无第三方依赖）

子命令:
    png  单帧 PPM -> PNG
    gif  多帧 PPM -> 动画 GIF（替代 ImageMagick 的 convert）

用法:
    ./ppm_tool.py png <input.ppm> [output.png] [-s scale]
    ./ppm_tool.py gif -o <output.gif> [-d delay_cs] [-s scale] [-l loop] <inputs...>

说明:
    inputs 可以是 .ppm 文件，也可以是目录（自动收集目录下所有 .ppm，按自然顺序排序）。
    -d delay_cs 单位是 1/100 秒，与 ImageMagick -delay 一致（20 => 0.2s）。
    -s scale     最近邻整数放大（4 => 400%）。
    -l loop      循环次数，0=无限（默认）。
"""

import sys
import os
import re
import glob
import zlib
import struct
import argparse


# ---------------- PPM 读取 ----------------


def read_ppm(path):
    """解析 P3 ASCII PPM，返回 (width, height, pixels_list)，pixels 为 [r,g,b,...]。"""
    with open(path, "r", encoding="ascii", errors="strict") as f:
        content = f.read()

    lines = []
    for line in content.splitlines():
        idx = line.find("#")
        if idx >= 0:
            line = line[:idx]
        lines.append(line)

    tokens = " ".join(lines).split()
    if not tokens:
        raise ValueError(f"{path}: 空文件")
    if tokens[0] != "P3":
        raise ValueError(f"{path}: 不是 P3 格式（得到 {tokens[0]!r}）")
    if len(tokens) < 4:
        raise ValueError(f"{path}: 头部不完整")

    width = int(tokens[1])
    height = int(tokens[2])
    maxval = int(tokens[3])
    if maxval != 255:
        raise ValueError(f"{path}: 只支持 maxval=255，得到 {maxval}")
    if width <= 0 or height <= 0:
        raise ValueError(f"{path}: 非法尺寸 {width}x{height}")

    values = list(map(int, tokens[4:]))
    expected = width * height * 3
    if len(values) != expected:
        raise ValueError(
            f"{path}: 像素数不对（期望 {expected} 个数值，实际 {len(values)}）"
        )
    return width, height, values


# ---------------- PNG 写入 ----------------


def write_png(path, width, height, pixels):
    raw = bytearray()
    row_bytes = width * 3
    for y in range(height):
        raw.append(0)  # filter byte
        start = y * row_bytes
        raw.extend(bytes(pixels[start : start + row_bytes]))

    def chunk(typ, data):
        body = typ + data
        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 9)
    with open(path, "wb") as f:
        f.write(sig)
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", idat))
        f.write(chunk(b"IEND", b""))


# ---------------- GIF 编码 ----------------
def _lzw_encode(indices, min_code_size):
    clear_code = 1 << min_code_size
    end_code = clear_code + 1

    out = bytearray()
    bitbuf = 0
    bitcnt = 0

    def emit(code, size):
        nonlocal bitbuf, bitcnt
        bitbuf |= code << bitcnt
        bitcnt += size
        while bitcnt >= 8:
            out.append(bitbuf & 0xFF)
            bitbuf >>= 8
            bitcnt -= 8

    code_size = min_code_size + 1
    next_code = end_code + 1
    dictionary = {bytes([i]): i for i in range(clear_code)}

    emit(clear_code, code_size)

    n = len(indices)
    if n == 0:
        emit(end_code, code_size)
        if bitcnt:
            out.append(bitbuf & 0xFF)
        return bytes(out)

    prefix = bytes([indices[0]])
    for i in range(1, n):
        c = bytes([indices[i]])
        combined = prefix + c
        code = dictionary.get(combined)
        if code is not None:
            prefix = combined
            continue

        emit(dictionary[prefix], code_size)

        if next_code < 4096:
            dictionary[combined] = next_code
            next_code += 1
            if next_code > (1 << code_size) and code_size < 12:  # ← 这里
                code_size += 1
        else:
            emit(clear_code, code_size)
            dictionary = {bytes([j]): j for j in range(clear_code)}
            code_size = min_code_size + 1
            next_code = end_code + 1

        prefix = c

    emit(dictionary[prefix], code_size)
    emit(end_code, code_size)
    if bitcnt:
        out.append(bitbuf & 0xFF)
    return bytes(out)


def _build_palette(colors):
    """返回 (palette_list, color_to_index_dict)。palette 长度是 2 的幂（>=2）。"""
    colors = list(colors)
    if len(colors) <= 256:
        palette = list(colors)
        color_to_idx = {c: i for i, c in enumerate(palette)}
    else:
        # 3-3-2 量化到固定 256 色
        palette = []
        for i in range(256):
            r = ((i >> 5) & 0x7) * 255 // 7
            g = ((i >> 2) & 0x7) * 255 // 7
            b = (i & 0x3) * 255 // 3
            palette.append((r, g, b))

        def q(c):
            r, g, b = c
            return ((r >> 5) << 5) | ((g >> 5) << 2) | (b >> 6)

        color_to_idx = {c: q(c) for c in colors}

    n = max(1, len(palette))
    size = 2
    while size < n:
        size *= 2
    if len(palette) < size:
        palette = palette + [(0, 0, 0)] * (size - len(palette))
    return palette, color_to_idx


def write_gif(path, frame_paths, delay_cs=20, loop=0, scale=1):
    if not frame_paths:
        raise ValueError("没有输入帧")
    if scale < 1:
        raise ValueError("scale 必须 >= 1")

    # 第一遍：检查尺寸一致、收集所有颜色
    W = H = None
    colors = set()
    for p in frame_paths:
        w, h, pix = read_ppm(p)
        if W is None:
            W, H = w, h
        elif (w, h) != (W, H):
            raise ValueError(f"{p}: 尺寸 {w}x{h} 与首帧 {W}x{H} 不一致")
        for k in range(0, len(pix), 3):
            colors.add((pix[k], pix[k + 1], pix[k + 2]))

    palette, color_to_idx = _build_palette(colors)
    gct_size = len(palette)  # 2 的幂
    n = gct_size.bit_length() - 1
    gct_field = n - 1  # 表大小 = 2^(field+1)
    min_code_size = max(2, (gct_size - 1).bit_length())

    outW, outH = W * scale, H * scale

    with open(path, "wb") as f:
        f.write(b"GIF89a")
        # Logical Screen Descriptor
        f.write(struct.pack("<HH", outW, outH))
        f.write(bytes([0x80 | (0x7 << 4) | gct_field, 0, 0]))
        # Global Color Table
        buf = bytearray()
        for r, g, b in palette:
            buf += bytes((r & 0xFF, g & 0xFF, b & 0xFF))
        f.write(buf)
        # Netscape loop extension
        f.write(b"\x21\xff\x0bNETSCAPE2.0")
        f.write(b"\x03\x01")
        f.write(struct.pack("<H", loop & 0xFFFF))
        f.write(b"\x00")

        # 每帧
        for p in frame_paths:
            w, h, pix = read_ppm(p)

            # 构造索引数组，顺带做最近邻放大
            indices = bytearray(outW * outH)
            for y in range(h):
                row = bytearray(outW)
                base_row = y * w
                for x in range(w):
                    k = (base_row + x) * 3
                    idx = color_to_idx[(pix[k], pix[k + 1], pix[k + 2])]
                    if scale == 1:
                        row[x] = idx
                    else:
                        for sx in range(scale):
                            row[x * scale + sx] = idx
                if scale == 1:
                    indices[y * outW : (y + 1) * outW] = row
                else:
                    for sy in range(scale):
                        start = (y * scale + sy) * outW
                        indices[start : start + outW] = row

            # Graphic Control Extension
            f.write(b"\x21\xf9\x04")
            f.write(bytes([0x04]))  # disposal=1 (do not dispose)
            f.write(struct.pack("<H", delay_cs))
            f.write(b"\x00")  # transparent color index
            f.write(b"\x00")  # block terminator

            # Image Descriptor
            f.write(b"\x2c")
            f.write(struct.pack("<HHHH", 0, 0, outW, outH))
            f.write(bytes([0x00]))  # no local palette, no interlace

            # LZW data
            f.write(bytes([min_code_size]))
            lzw = _lzw_encode(indices, min_code_size)
            for i in range(0, len(lzw), 255):
                chunk = lzw[i : i + 255]
                f.write(bytes([len(chunk)]))
                f.write(chunk)
            f.write(b"\x00")

        f.write(b"\x3b")


# ---------------- 参数展开 ----------------

_NAT_RE = re.compile(r"(\d+)")


def _natural_key(s):
    return [int(t) if t.isdigit() else t for t in _NAT_RE.split(s)]


def expand_inputs(inputs):
    paths = []
    for inp in inputs:
        if os.path.isdir(inp):
            found = sorted(
                glob.glob(os.path.join(inp, "*.ppm")),
                key=_natural_key,
            )
            paths.extend(found)
        elif os.path.isfile(inp):
            paths.append(inp)
        else:
            raise FileNotFoundError(f"输入不存在: {inp}")
    return paths


# ---------------- 子命令 ----------------


def cmd_png(args):
    w, h, pix = read_ppm(args.input)
    if args.scale and args.scale > 1:
        s = args.scale
        ow, oh = w * s, h * s
        scaled = []
        for y in range(h):
            for _ in range(s):
                for x in range(w):
                    k = (y * w + x) * 3
                    for _ in range(s):
                        scaled.extend(pix[k : k + 3])
        w, h, pix = ow, oh, scaled

    out = args.output or (os.path.splitext(args.input)[0] + ".png")
    write_png(out, w, h, pix)
    print(f"已生成 {out}  ({w} x {h})")
    return 0


def cmd_gif(args):
    paths = expand_inputs(args.inputs)
    if not paths:
        print("错误：没有找到任何 .ppm 文件", file=sys.stderr)
        return 1
    write_gif(args.output, paths, delay_cs=args.delay, loop=args.loop, scale=args.scale)
    print(
        f"已生成 {args.output}  ({len(paths)} 帧, delay={args.delay}cs, scale={args.scale}x)"
    )
    return 0


def main(argv):
    ap = argparse.ArgumentParser(
        description="P3 PPM -> PNG / GIF 转换工具（纯 Python，无第三方依赖）"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_png = sub.add_parser("png", help="单帧 PPM 转 PNG")
    p_png.add_argument("input", help="输入 .ppm 文件")
    p_png.add_argument("output", nargs="?", default=None, help="输出 .png（默认同名）")
    p_png.add_argument("-s", "--scale", type=int, default=1, help="整数放大倍数")
    p_png.set_defaults(func=cmd_png)

    p_gif = sub.add_parser("gif", help="多帧 PPM 转 GIF")
    p_gif.add_argument("-o", "--output", required=True, help="输出 .gif 文件")
    p_gif.add_argument(
        "-d",
        "--delay",
        type=int,
        default=20,
        help="帧间延时（1/100 秒，默认 20 = 0.2s）",
    )
    p_gif.add_argument(
        "-s", "--scale", type=int, default=1, help="整数放大倍数（最近邻），默认 1"
    )
    p_gif.add_argument(
        "-l", "--loop", type=int, default=0, help="循环次数，0=无限（默认）"
    )
    p_gif.add_argument(
        "inputs",
        nargs="+",
        help="PPM 文件或目录（目录会自动收集 *.ppm 并按自然顺序排序）",
    )
    p_gif.set_defaults(func=cmd_gif)

    args = ap.parse_args(argv)
    try:
        rc = args.func(args)
        return rc if rc is not None else 0
    except (OSError, ValueError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
