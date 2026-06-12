#!/usr/bin/env python3
"""
SQLite + FITS 集成演示
（依赖 fitsio 和 numpy）
"""

import sqlite3
from pathlib import Path
import sys


def create_database():
    """创建数据库和表结构"""
    db_path = Path("fits_metadata.db")
    
    if db_path.exists():
        print(f"数据库已存在: {db_path}")
        return db_path
    
    print(f"创建数据库: {db_path}")
    conn = sqlite3.connect(db_path)
    
    # 创建表结构
    conn.execute("""
        CREATE TABLE fits_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL UNIQUE,
            file_name TEXT NOT NULL,
            file_size INTEGER,
            file_type TEXT,
            date_obs TEXT,
            telescope TEXT,
            instrument TEXT,
            filter_name TEXT,
            exposure_time REAL,
            observer TEXT,
            comment TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建索引
    conn.execute("CREATE INDEX idx_date_obs ON fits_files(date_obs)")
    conn.execute("CREATE INDEX idx_telescope ON fits_files(telescope)")
    
    conn.commit()
    conn.close()
    
    print("✓ 数据库和表结构创建完成")
    return db_path


def check_fitsio():
    """检查 fitsio 库是否可用"""
    try:
        import fitsio
        import numpy as np
        print("✓ fitsio 库已安装")
        return True
    except ImportError as e:
        print(f"✗ 未安装 fitsio 库: {e}")
        print("\n安装命令:")
        print("  pip install fitsio numpy")
        return False


def add_data_point(db_path, file_type):
    """添加单个 FITS 元数据记录"""
    # 模拟数据 - 真实场景中从 FITS 文件读取
    import fitsio
    
    try:
        # 尝试从真实的 FITS 文件读取
        test_file = Path("test_simple.fits")
        if test_file.exists():
            print(f"\n使用真实 FITS 文件: {test_file}")
            hdul = fitsio.read_header(str(test_file))
            
            date_obs = hdul.get('DATE-OBS', 'N/A')
            telescope = hdul.get('TELESCOP', 'N/A')
            instrument = hdul.get('INSTRUME', 'N/A')
            exposure_time = float(hdul.get('EXPTIME', 0.0))
        else:
            # 使用模拟数据
            print(f"\n使用模拟数据（未找到真实 FITS 文件）")
            date_obs = "2025-06-12T15:30:00"
            telescope = "Hubble Space Telescope"
            instrument = "Wide Field Camera 3"
            exposure_time = 300.0
            file_path = None
            print(f"执行命令创建测试 FITS: python3 << 'EOF'")
            print(f"import fitsio; import numpy as np; data = np.random.randint(0,1000,size=(100,200),dtype=np.int16); ")
            print(f"header=[{'name':k,'value':v} for k,v in [('SIMPLE',True),('BITPIX',16),('NAXIS',2),('NAXIS1',200),('NAXIS2',100),('TELESCOP','HST'),('INSTRUME','ACS/WFC'),('DATE-OBS','2025-06-12T15:30:00'),('EXPTIME',300.0)]]")
            print(f"fitsio.write('test_simple.fits',data,header,clobber=True);")
            print("EOF")
            return
        
        # 插入数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查文件是否已存在
        cursor.execute("SELECT id FROM fits_files WHERE file_path = ?", 
                      (str(test_file.absolute()),))
        if cursor.fetchone():
            print(f"⚠ FITS 文件已存在: {test_file.name}")
        else:
            cursor.execute("""
                INSERT INTO fits_files (
                    file_path, file_name, file_size, file_type,
                    date_obs, telescope, instrument, exposure_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(test_file.absolute()),
                test_file.name,
                test_file.stat().st_size,
                file_type,
                date_obs,
                telescope,
                instrument,
                exposure_time,
            ))
            conn.commit()
            print(f"✓ 已添加 FITS 文件: {test_file.name} (ID: {cursor.lastrowid})")
        
        conn.close()
        
    except Exception as e:
        print(f"✗ 添加数据失败: {e}")
        import traceback
        traceback.print_exc()


def query_data(db_path):
    """查询 FITS 元数据"""
    print("\n" + "="*80)
    print("查询 FITS 元数据")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, file_name, file_type, date_obs, telescope, instrument, exposure_time
        FROM fits_files
        ORDER BY date_obs DESC, id DESC
    """)
    
    results = cursor.fetchall()
    
    if not results:
        print("数据库为空，没有记录")
    else:
        print(f"\n找到 {len(results)} 条记录:")
        print("-"*80)
        print(f"{'ID':<4} {'文件名':<25} {'类型':<10} {'日期':<15} {'望远镜':<20} {'仪器':<20} {'曝光(秒)':<10}")
        print("-"*80)
        
        for row in results:
            fid, filename, ftype, fdate, ftel, finst, fexp = row
            date_str = str(fdate)[:19] if fdate != 'N/A' else 'N/A'
            print(f"{fid:<4} {filename:<25} {ftype:<10} "
                  f"{date_str:<15} {ftel:<20} {finst:<20} {fexp:<10.1f}")
    
    conn.close()


def main():
    print("="*80)
    print("SQLite + FITS 集成演示")
    print("="*80)
    
    # 检查依赖
    if not check_fitsio():
        print("\n演示终止：缺少必要的 Python 库")
        return
    
    # 创建数据库
    db_path = create_database()
    
    # 添加模拟数据
    print("\n" + "="*80)
    print("添加 FITS 文件元数据")
    print("="*80)
    
    if Path("test_simple.fits").exists():
        add_data_point(db_path, "image")
    else:
        print("\n⚠ 未找到测试 FITS 文件")
    
    # 查询数据
    query_data(db_path)
    
    print("\n✓ 演示完成")


if __name__ == "__main__":
    main()
