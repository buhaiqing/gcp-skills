#!/bin/bash

# SQLite FITS Support Check

echo "=== SQLite 版本 ==="
sqlite3 --version

echo -e "\n=== FITS 支持检查 ==="
if sqlite3 -cmd '.quit' :memory: "
    SELECT CASE
        WHEN sqlite_compileoption_used('FITS') = 1 THEN '✓ FITS 已启用'
        ELSE '✗ FITS 未启用'
    END AS status;
" 2>/dev/null; then
    echo ""
else
    echo "✗ 检测失败 - SQLite 3.35.0+ 才支持 sqlite_compileoption_used()"
fi

echo -e "\n=== SQLite 编译选项 ==="
sqlite3<<-EOF
.mode list
.show
EOF

echo -e "\n=== 查询可用 pragma ==="
sqlite3<<-EOF
SELECT name FROM pragma_list_v2;
SQLITEVERSION
EOF
if sqlite3<<-EOF
SELECT compile_option FROM pragma_compile_options
WHERE compile_option LIKE '%FITS%' OR compile_option LIKE '%fits%';
SQLITEVERSION
EOF
2>/dev/null; then
    echo "找到 FITS 相关编译选项"
else
    echo "未找到 FITS 相关编译选项"
fi
