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
python main.py view

echo.
pause
