from flood_support.data_access import replace_pdf_pages,search_pdf_pages

def test_sqlite_page_replace_and_search(tmp_path):
    db=tmp_path/"test.sqlite"
    replace_pdf_pages(db,[{"source":"guide.pdf","page":2,"text":"Emergency evacuation guidance"}])
    assert search_pdf_pages(db,"evacuation")[0]["page"]==2
    replace_pdf_pages(db,[{"source":"guide.pdf","page":3,"text":"Updated source page"}])
    assert len(search_pdf_pages(db))==1 and search_pdf_pages(db)[0]["page"]==3
import csv,json
import pymupdf

def test_prepare_v2_leaves_unverified_publication_times_unknown(tmp_path):
    from flood_support.ingest import prepare
    raw=tmp_path/"data"/"raw"; raw.mkdir(parents=True)
    fields=["Station","State","District","River","Data Acquisition Time","Telemetry Hourly Rainfall (mm)","Agency","Latitude","Longitude"]
    with (raw/"rainfall_tel_hr_cwc_ap_2021_2025.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerow({"Station":"Gauge A","State":"Andhra Pradesh","District":"Example","River":"Example River","Data Acquisition Time":"16-07-2022 10:00","Telemetry Hourly Rainfall (mm)":"12","Agency":"CWC","Latitude":"1","Longitude":"2"})
    for name,text in [("cwc_daily_flood_bulletin_2022-07-16.pdf","CWC bulletin"),("mha_flood_situation_2022-07-16.pdf","MHA 16-07-2022 1800 Hrs")]:
        doc=pymupdf.open(); page=doc.new_page(); page.insert_text((72,72),text); doc.save(raw/name); doc.close()
    proc=tmp_path/"data"/"processed"; proc.mkdir(parents=True)
    old_file=proc/"historical_evidence.jsonl"; old_file.write_text("preserve-existing\n",encoding="utf-8")
    prepare(tmp_path,versioned_only=True)
    assert old_file.read_text(encoding="utf-8")=="preserve-existing\n"
    rows=[json.loads(line) for line in (tmp_path/"data"/"processed"/"historical_evidence_v2.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows and all(r["available_at"] is None and r["published_at"] is None for r in rows)
    assert all(r["ingested_at"] for r in rows)
    mha=next(r for r in rows if r["evidence_id"].startswith("HIST-MHA-ABOVE"))
    assert mha["report_as_of_time"]=="2022-07-16T18:00:00+05:30"
    assert mha["availability_assumption"]["value"] is None
