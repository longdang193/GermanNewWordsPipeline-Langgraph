import sqlite3, os, pathlib
home = pathlib.Path(os.environ['USERPROFILE']) / '.codex'
db = home / 'state_5.sqlite'
con = sqlite3.connect(db)
cur = con.cursor()
for table in ['threads','thread_dynamic_tools','thread_spawn_edges','agent_jobs','jobs']:
    print('\nTABLE', table)
    cols = [r[1] for r in cur.execute(f'PRAGMA table_info({table})')]
    print('COLUMNS', cols)
    try:
        sample = cur.execute(f'SELECT * FROM {table} LIMIT 3').fetchall()
        print('SAMPLE', sample)
    except Exception as exc:
        print('ERR', exc)
con.close()
