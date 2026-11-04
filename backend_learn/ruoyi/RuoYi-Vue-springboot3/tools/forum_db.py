"""本地开发辅助：从现有数据源配置读取凭据，只连接localhost，不打印密码。

用法：python tools/forum_db.py --query "SELECT ..."
      python tools/forum_db.py --file sql/forum_demo.sql
业务应用仍通过MyBatis访问数据库，本脚本仅用于初始化和验收。
"""
import argparse
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def run_sql(sql):
    config = (ROOT / 'ruoyi-admin/src/main/resources/application-druid.yml').read_text(encoding='utf-8')
    master = config.split('master:', 1)[1].split('slave:', 1)[0]
    def value(key):
        match = re.search(r'^\s*' + key + r':\s*(.*?)\s*$', master, re.M)
        if not match:
            raise RuntimeError('数据源配置缺少字段：' + key)
        return match.group(1).strip('"\'')
    jdbc = re.match(r'jdbc:mysql://(localhost|127\.0\.0\.1):(\d+)/([^?\s]+)', value('url'))
    if not jdbc:
        raise RuntimeError('仅允许现有配置中的本机MySQL，已停止')
    env = dict(os.environ, MYSQL_PWD=value('password'))
    result = subprocess.run([
        r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe',
        '--host=' + jdbc[1], '--port=' + jdbc[2], '--user=' + value('username'),
        '--database=' + jdbc[3], '--default-character-set=utf8mb4', '--batch', '--raw'
    ], input=sql.encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace'))
    return result.stdout.decode('utf-8', errors='replace')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--query')
    group.add_argument('--file')
    args = parser.parse_args()
    sql = args.query if args.query else Path(args.file).read_text(encoding='utf-8')
    print(run_sql(sql))
