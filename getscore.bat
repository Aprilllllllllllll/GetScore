@echo off
chcp 65001 >nul
cd /d "E:\GetScore"

echo ============================================
echo  正在执行成绩查询脚本...
echo ============================================
REM 用 Git Bash 运行 run.sh（请确保已安装 Git）
bash -c "cd 'E:/GetScore' && bash scripts/run.sh"

if %errorlevel% neq 0 (
    echo.
    echo ❌ 查询脚本执行失败！
    pause
    exit /b
)

echo.
echo ============================================
echo  查询完成，最新成绩如下：
echo ============================================
python -c "import sqlite3; conn=sqlite3.connect('data/scores.db'); conn.row_factory=sqlite3.Row; cur=conn.cursor(); cur.execute('SELECT id, course_name, score, semester, is_fail FROM scores ORDER BY id'); rows=cur.fetchall(); print(f'共 {len(rows)} 条记录\n'); [print(f'{r[\"id\"]:<4} {r[\"course_name\"]:<35} {str(r[\"score\"]):>6}  {r[\"semester\"]:<12} {\"⚠挂科\" if r[\"is_fail\"] else \" 正常\"}') for r in rows]; conn.close()"

echo.
pause