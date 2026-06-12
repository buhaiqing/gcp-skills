#!/usr/bin/env python3
"""
创建测试 FITS 文件
"""

import fitsio
import numpy as np
from pathlib import Path


def create_test_fits(filename="test_image.fits"):
    """创建测试用的 FITS 文件"""

    # 创建测试数据 (2D 长方形数组) - 需要 numpy
    import numpy as np
    data = np.array([[i * 10 + j for j in range(100)] for i in range(100)], dtype=np.int16)

    # 创建 FITS 头表 - 需要 list of dict
    header = [
        {'name': 'SIMPLE', 'value': True},
        {'name': 'BITPIX', 'value': 16},
        {'name': 'NAXIS', 'value': 2},
        {'name': 'NAXIS1', 'value': 100},
        {'name': 'NAXIS2', 'value': 100},
        {'name': 'DATE', 'value': '2025-06-12T13:14:00'},
        {'name': 'DATE-OBS', 'value': '2025-06-12T13:14:00'},
        {'name': 'TELESCOP', 'value': 'Hubble Space Telescope'},
        {'name': 'INSTRUME', 'value': 'Wide Field Camera 3'},
        {'name': 'FILTER', 'value': 'F606W'},
        {'name': 'EXPTIME', 'value': 1200.0},
        {'name': 'OBSERVER', 'value': 'Test User'},
        {'name': 'OBJECT', 'value': 'Test Galaxy'},
        {'name': 'COMMENTS', 'value': 'Test FITS file for SQLite integration'},
    ]

    # 写入文件
    file_path = Path(filename)
    with fitsio.write(str(file_path), data, header, clobber=True):
        pass

    print(f"✓ 创建测试 FITS 文件: {file_path}")
    print(f"  文件大小: {file_path.stat().st_size} bytes")
    print(f"  日期: {header[5]['value']}")
    print(f"  望远镜: {header[6]['value']}")
    print(f"  滤光片: {header[7]['value']}")
    print(f"  曝光时间: {header[8]['value']} 秒")

    return str(file_path)

    print(f"✓ 创建测试 FITS 文件: {file_path}")
    print(f"  文件大小: {file_path.stat().st_size} bytes")
    print(f"  日期: {header['DATE-OBS']}")
    print(f"  望远镜: {header['TELESCOP']}")
    print(f"  滤光片: {header['FILTER']}")
    print(f"  曝光时间: {header['EXPTIME']} 秒")

    return str(file_path)


if __name__ == "__main__":
    create_test_fits("test_image.fits")
