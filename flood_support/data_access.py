"""Small SQLite data-access layer; later backends can implement the same calls."""
import sqlite3
from pathlib import Path

def replace_pdf_pages(database:Path, pages:list[dict]):
    database=Path(database); database.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS pdf_pages(source TEXT,page INTEGER,text TEXT,PRIMARY KEY(source,page))")
        conn.execute("DELETE FROM pdf_pages")
        conn.executemany("INSERT INTO pdf_pages(source,page,text) VALUES(?,?,?)",[(p["source"],p["page"],p["text"]) for p in pages])

def search_pdf_pages(database:Path,query:str=""):
    database=Path(database)
    if not database.exists(): return []
    with sqlite3.connect(database) as conn:
        if query:
            rows=conn.execute("SELECT source,page,text FROM pdf_pages WHERE text LIKE ? ORDER BY source,page",(f"%{query}%",)).fetchall()
        else: rows=conn.execute("SELECT source,page,text FROM pdf_pages ORDER BY source,page").fetchall()
    return [{"source":s,"page":p,"text":t} for s,p,t in rows]
