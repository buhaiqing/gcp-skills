#!/usr/bin/env python3
"""
SQLite + FITS 支持集成示例
方案: 使用 fitsio 库 + SQLite 存储 FITS 文件路径 + 元数据
"""

from pathlib import Path
import sqlite3
import fitsio
from typing import Optional


class FITSMetadataDB:
    """FITS 元数据数据库管理器"""

    def __init__(self, db_path: str | Path = "fits_metadata.db"):
        """
        初始化数据库

        Args:
            db_path: SQLite 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.conn = None
        self._init_db()

    def _init_db(self):
        """初始化数据库表结构"""
        self.conn = sqlite3.connect(self.db_path)

        # 创建 FITS 文件元数据表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS fits_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                file_name TEXT NOT NULL,
                file_size INTEGER,
                file_type TEXT,
                date_obs TEXT,  -- 观测日期
                telescope TEXT,  -- 望远镜信息
                instrument TEXT,  -- 仪器信息
                filter TEXT,  -- 滤光片
                exposure_time REAL,  -- 曝光时间(秒)
                observer TEXT,  -- 观测者
                comment TEXT,  -- 备注
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引加速查询
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_date_obs ON fits_files(date_obs)
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_telescope ON fits_files(telescope)
        """)

        self.conn.commit()

    def add_fits_file(
        self,
        file_path: str | Path,
        file_type: Optional[str] = None,
        date_obs: Optional[str] = None,
        telescope: Optional[str] = None,
        instrument: Optional[str] = None,
        filter_name: Optional[str] = None,
        exposure_time: Optional[float] = None,
        observer: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> int:
        """
        添加 FITS 文件元数据到 SQLite

        Args:
            file_path: FITS 文件路径
            file_type: FITS 文件类型（如 'image', 'cube', 'catalog'）
            date_obs: 观测日期
            telescope: 望远镜名称
            instrument: 仪器名称
            filter_name: 滤光片名称
            exposure_time: 曝光时间（秒）
            observer: 观测者
            comment: 备注信息

        Returns:
            插入的记录 ID
        """
        fits_path = Path(file_path)

        # 检查文件是否存在且为 FITS
        if not fits_path.exists():
            raise FileNotFoundError(f"FITS 文件不存在: {fits_path}")

        if not fits_path.suffix.lower() == '.fits':
            raise ValueError(f"文件不是 FITS 格式: {fits_path.name}")

        # 使用 fitsio 读取 FITS 文件元数据
        try:
            hdul = fitsio.read_header(str(fits_path))

            # 提取 FITS 标准头表关键字
            fits_type = file_type or "image"
            date_obs = date_obs or hdul.get('DATE-OBS', 'N/A').encode().decode('ascii') if hdul.get('DATE-OBS') else 'N/A'
            telescope = telescope or hdul.get('TELESCOP', 'N/A').encode().decode('ascii') if hdul.get('TELESCOP') else 'N/A'
            instrument = instrument or hdul.get('INSTRUME', 'N/A').encode().decode('ascii') if hdul.get('INSTRUME') else 'N/A'
            filter_name = filter_name or hdul.get('FILTER', 'N/A').encode().decode('ascii') if hdul.get('FILTER') else 'N/A'
            exposure_time = exposure_time or float(hdul.get('EXPTIME', 0.0))
            observer = observer or hdul.get('OBSERVER', 'N/A').encode().decode('ascii') if hdul.get('OBSERVER') else 'N/A'

        except Exception as e:
            print(f"警告: 读取 FITS 头表失败 ({fits_path.name}), 使用提供的参数: {e}")
            # 继续使用用户提供的参数

        # 插入数据库
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO fits_files (
                    file_path, file_name, file_size, file_type,
                    date_obs, telescope, instrument, filter_name,
                    exposure_time, observer, comment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(fits_path.absolute()),
                fits_path.name,
                fits_path.stat().st_size,
                fits_type,
                date_obs,
                telescope,
                instrument,
                filter_name,
                exposure_time,
                observer,
                comment,
            ))
            self.conn.commit()
            print(f"✓ 已添加 FITS 文件: {fits_path.name} (ID: {cursor.lastrowid})")
            return cursor.lastrowid

        except sqlite3.IntegrityError:
            print(f"⚠ 文件已存在: {fits_path.name} (ID: {cursor.execute('SELECT id FROM fits_files WHERE file_path = ?', (str(fits_path),)).fetchone()[0]})")
            # 更新现有记录
            cursor.execute("""
                UPDATE fits_files SET
                    file_size = ?, file_type = ?, date_obs = ?, telescope = ?,
                    instrument = ?, filter_name = ?, exposure_time = ?, observer = ?, comment = ?
                WHERE file_path = ?
            """, (
                fits_path.stat().st_size, fits_type, date_obs, telescope,
                instrument, filter_name, exposure_time, observer, comment, str(fits_path)
            ))
            self.conn.commit()
            return cursor.lastrowid

    def query_fits(
        self,
        telescope: Optional[str] = None,
        date_obs: Optional[str] = None,
        file_type: Optional[str] = None,
        instrument: Optional[str] = None,
    ):
        """
        查询 FITS 文件

        Args:
            telescope: 望远镜名称
            date_obs: 观测日期
            file_type: 文件类型
            instrument: 仪器名称
        """
        cursor = self.conn.cursor()

        # 构建查询条件
        conditions = []
        params = []

        if telescope:
            conditions.append("telescope = ?")
            params.append(telescope)
        if date_obs:
            conditions.append("date_obs = ?")
            params.append(date_obs)
        if file_type:
            conditions.append("file_type = ?")
            params.append(file_type)
        if instrument:
            conditions.append("instrument = ?")
            params.append(instrument)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT id, file_name, file_type, date_obs, telescope, instrument, exposure_time
            FROM fits_files
            WHERE {where_clause}
            ORDER BY date_obs DESC, id DESC
        """

        cursor.execute(query, params)
        results = cursor.fetchall()

        if not results:
            print("未找到匹配的 FITS 文件")
            return []

        # 格式化输出
        print(f"\n找到 {len(results)} 个 FITS 文件:")
        print("-" * 100)
        print(f"{'ID':<4} {'文件名':<30} {'类型':<10} {'日期':<12} {'望远镜':<15} {'仪器':<15} {'曝光时间(秒)':<10}")
        print("-" * 100)

        for row in results:
            (
                fid, filename, ftype, fdate, ftel, finst, fexp
            ) = row
            date_str = fdate[:10] if fdate and fdate != 'N/A' else 'N/A'
            print(
                f"{fid:<4} {filename:<30} {ftype:<10} "
                f"{date_str:<12} {ftel:<15} {finst:<15} {fexp:<10.2f}"
            )

        return results

    def get_fits_file(self, file_id: int):
        """获取 FITS 文件路径"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT file_path FROM fits_files WHERE id = ?",
            (file_id,)
        )
        result = cursor.fetchone()
        if result:
            print(f"✓ 找到 FITS 文件路径 (ID: {file_id}): {result[0]}")
            return result[0]
        else:
            print(f"✗ 未找到 FITS 文件 (ID: {file_id})")
            return None

    def __del__(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


def example_usage():
    """示例用法"""
    # 初始化数据库
    db = FITSMetadataDB()

    # 示例 1: 扫描目录添加 FITS 文件
    import glob

    print("=" * 100)
    print("示例 1: 添加 FITS 文件到数据库")
    print("=" * 100)

    fits_files = glob.glob("**/*.fits", recursive=True)

    if fits_files:
        for fits_file in fits_files[:5]:  # 仅添加前5个文件作为示例
            try:
                file_type = "image"
                if "cube" in fits_file.lower():
                    file_type = "cube"
                elif "catalog" in fits_file.lower():
                    file_type = "catalog"

                db.add_fits_file(
                    fits_file,
                    file_type=file_type,
                    comment="示例注释"
                )
            except Exception as e:
                print(f"✗ 添加失败 {fits_file}: {e}")
    else:
        print("当前目录下未找到 FITS 文件")

    # 示例 2: 查询 FITS 文件
    print("\n" + "=" * 100)
    print("示例 2: 查询 FITS 文件")
    print("=" * 100)

    db.query_fits(
        telescope="Hubble",
        date_obs="2025-06"
    )

    # 示例 3: 获取特定文件路径
    print("\n" + "=" * 100)
    print("示例 3: 获取 FITS 文件路径")
    print("=" * 100)

    results = db.query_fits()
    if results:
        fits_id = results[0][0]  # 获取第一个文件的ID
        db.get_fits_file(fits_id)


if __name__ == "__main__":
    example_usage()
