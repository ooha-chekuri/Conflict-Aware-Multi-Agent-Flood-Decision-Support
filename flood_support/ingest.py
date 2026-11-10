import hashlib,json,re
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd
import pymupdf
from .data_access import replace_pdf_pages

ROOT=Path(__file__).resolve().parents[1]
CSV_REQUIRED={"rainfall_statewise_daily_imd.csv":{"State","Date","Daily Actual","Daily Normal"},"rainfall_districtwise_daily_imd.csv":{"State","District","Date","Daily Actual"},"rainfall_tel_hr_cwc_ap_2021_2025.csv":{"Station","State","District","River","Data Acquisition Time","Telemetry Hourly Rainfall (mm)"}}
def prepare(root=ROOT, versioned_only=False):
    root=Path(root); raw=root/"data/raw"; proc=root/"data/processed"; proc.mkdir(parents=True,exist_ok=True)
    report={"created_at_utc":datetime.now(timezone.utc).isoformat(),"inputs":[],"issues":[],"pdf_pages":{},"csv":{}}
    pages=[]
    for f in sorted(raw.iterdir()):
        if not f.is_file(): continue
        ent={"name":f.name,"bytes":f.stat().st_size,"sha256":hashlib.sha256(f.read_bytes()).hexdigest()}
        if f.suffix.lower()==".pdf":
            try:
                with pymupdf.open(f) as doc:
                    report["pdf_pages"][f.name]=len(doc)
                    for ix,page in enumerate(doc,1):
                        text=" ".join(page.get_text().split())
                        pages.append({"source":f.name,"page":ix,"text":text})
                    if f.name.startswith("excluded_"): ent["excluded_reason"]="Unrelated résumé; retained as raw input, omitted from evidence."
            except Exception as e: report["issues"].append(f"PDF extraction failed for {f.name}: {e}")
        elif f.suffix.lower()==".csv":
            try:
                df=pd.read_csv(f,low_memory=False); required=CSV_REQUIRED.get(f.name,set()); missing=sorted(required-set(df.columns)); ent["rows"]=int(len(df)); ent["columns"]=list(df.columns)
                ent["missing_required_columns"]=missing
                if missing: report["issues"].append(f"{f.name}: missing required columns {missing}")
                if f.name in CSV_REQUIRED:
                    dc="Data Acquisition Time" if "Data Acquisition Time" in df.columns else "Date"
                    parsed=pd.to_datetime(df[dc],dayfirst=dc=="Data Acquisition Time",errors="coerce")
                    ent["date_column"]=dc; ent["date_min"]=str(parsed.min()); ent["date_max"]=str(parsed.max()); ent["invalid_date_rows"]=int(parsed.isna().sum())
                    if dc=="Data Acquisition Time": ent["rows_on_2022_07_16"]=int(parsed.dt.strftime("%Y-%m-%d").eq("2022-07-16").sum())
                    if f.name.startswith("rainfall_") and dc=="Date": ent["rows_on_2022_07_16"]=int(parsed.dt.strftime("%Y-%m-%d").eq("2022-07-16").sum())
                report["csv"][f.name]=ent
            except Exception as e: report["issues"].append(f"CSV validation failed for {f.name}: {e}")
        report["inputs"].append(ent)
    page_index=proc/("pdf_pages_v2.jsonl" if versioned_only else "pdf_pages.jsonl")
    page_index.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in pages),encoding="utf-8")
    # Guideline index is kept separate from other PDF-derived material.
    guide="ndma_guidelines_management_of_floods.pdf"; passages=[]; current_section=None
    guide_path=raw/guide
    if guide_path.exists():
        with pymupdf.open(guide_path) as doc:
            for page_no,page in enumerate(doc,1):
                # The supplied edition's first 32 physical pages are front matter,
                # contents, and executive action summaries rather than numbered chapters.
                if page_no < 33:
                    continue
                current_section=None
                buffer=[]
                def flush_paragraph():
                    para=" ".join(" ".join(buffer).split())
                    if len(para)>80 and current_section:
                        passages.append({"source":guide,"page":page_no,"section":current_section,"text":para})
                    buffer.clear()
                for line in page.get_text("text").splitlines():
                    heading=re.match(r"^\s*(\d+(?:\.\d+)+)\s+(.{3,120})$",line)
                    if heading:
                        flush_paragraph()
                        title=re.split(r"\s+\d+(?:\.\d+){0,3}\s+[A-Z]",heading.group(2).strip(),maxsplit=1)[0]
                        title=re.sub(r"\s+\d+(?:\s+\d+)*$", "", title).strip()
                        if title: current_section=f"{heading.group(1)} {title}"
                    elif not line.strip(): flush_paragraph()
                    else: buffer.append(line.strip())
                flush_paragraph()
    (root/"data/guidelines").mkdir(parents=True,exist_ok=True)
    passage_name="passages_v2.jsonl" if versioned_only else "passages.jsonl"
    (root/"data/guidelines"/passage_name).write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in passages),encoding="utf-8")
    # Build an explicitly sourced historical evidence subset only from matching dated telemetry and dated docs.
    hist=[]
    tel=raw/"rainfall_tel_hr_cwc_ap_2021_2025.csv"
    if tel.exists():
        df=pd.read_csv(tel,low_memory=False); ts=pd.to_datetime(df["Data Acquisition Time"],dayfirst=True,errors="coerce")
        selected=df[(ts.dt.strftime("%Y-%m-%d")=="2022-07-16") & df.State.astype(str).str.contains("Andhra Pradesh",case=False,na=False)]
        for i,row in selected.iterrows():
            obs=pd.to_datetime(row["Data Acquisition Time"],dayfirst=True,errors="coerce")
            hist.append({"evidence_id":f"HIST-TELEMETRY-{int(i)}","source_label":"historical","source_class":"official_telemetry","source_name":tel.name,"claim_type":"rainfall","claim_text":f"Telemetry rainfall {row['Telemetry Hourly Rainfall (mm)']} mm recorded at station {row['Station']}","location":str(row.get("District") or ""),"observed_at":obs.isoformat() if not pd.isna(obs) else None,"available_at":obs.isoformat() if not pd.isna(obs) else None,"value":float(row["Telemetry Hourly Rainfall (mm)"]) if pd.notna(row["Telemetry Hourly Rainfall (mm)"]) else None,"unit":"mm","measurement_type":"observation","verified":False,"source_page":None,"metadata":{"station":row["Station"],"river":row["River"],"agency":row["Agency"],"latitude":row["Latitude"],"longitude":row["Longitude"],"curation":"row-preserving CSV extraction; no independent verification"}})
    # Legacy output below preserves the earlier assumptions for comparison only.
    # The versioned output clears these availability values and records the 18:00
    # MHA report-as-of time separately; CWC issue time is unknown.
    docdates={"mha_flood_situation_2022-07-15.pdf":"2022-07-15T18:00:00+05:30","cwc_daily_flood_situation_report_2022-07-16.pdf":"2022-07-16T23:59:59+05:30","cwc_daily_flood_bulletin_2022-07-16.pdf":"2022-07-16T23:59:59+05:30","mha_flood_situation_2022-07-16.pdf":"2022-07-16T18:00:00+05:30"}
    for row in pages:
        if row["source"] in docdates and row["text"]:
            hist.append({"evidence_id":f"HIST-PDF-{row['source']}-P{row['page']}","source_label":"historical","source_class":"government_official","source_name":row["source"],"claim_type":"historical_context","claim_text":row["text"][:2500],"location":None,"available_at":docdates[row["source"]],"measurement_type":"unknown","source_page":row["page"],"verified":False,"metadata":{"curation":"page text extraction, not a structured claim; human review required"}})
    # Manually curated rows transcribed from the CWC bulletin's printed station table.
    # Explicit values and provenance are retained; availability is end-of-day because issue time is unknown.
    bulletin="cwc_daily_flood_bulletin_2022-07-16.pdf"
    stations=[
      ("Chinturu (Tallagudem/Kummuru)","Sabri","Andhra Pradesh",41.5,43.0,50.42,49.24,49.40,"Rising",20.0,12,3),
      ("Dowlaiswaram (State Govt Site)","Godavari","Andhra Pradesh",14.25,16.08,18.36,17.1,17.31,"Rising",30.0,14,3),
      ("Kunavaram","Godavari","Andhra Pradesh",37.74,39.24,51.3,48.77,49.05,"Rising",40.0,13,3),
      ("Godavari Rly Bridge (Rajahmundry)","Godavari","Andhra Pradesh",17.68,19.51,20.48,19.08,19.18,"Rising",30.0,14,5),
      ("Bhadrachalam","Godavari","Telangana",45.72,48.77,55.66,53.916,53.18,"Falling",-60.0,14,3),
      ("Dummugudem","Godavari","Telangana",53.0,55.0,60.25,58.38,57.8,"Falling",-100.0,14,3),
    ]
    for station,river,state,warning,danger,hfl,actual,forecast,trend,rate,hour,pdfpage in stations:
        base_id=f"HIST-CWC-{station.upper().replace(' ','-')}-20220716"
        common={"source_label":"historical","source_class":"government_official","source_name":bulletin,"location":station,"available_at":"2022-07-16T23:59:59+05:30","unit":"m","source_page":pdfpage,"verified":False,"metadata":{"river":river,"state":state,"warning_level_m":warning,"danger_level_m":danger,"highest_flood_level_m":hfl,"trend_mm_per_hour":rate,"curation":"manual structured transcription from printed CWC table; independently review against source page","availability_assumption":"publication time unknown; end-of-day cutoff used to prevent intraday leakage"}}
        hist.append(common|{"evidence_id":base_id,"claim_type":"river_level","claim_text":f"CWC bulletin observed level at {station}, {river}, {state}: {actual} m at 16-07-2022 {hour:02d}:00; trend {trend} ({rate:g} mm/hour). Warning {warning} m, danger {danger} m, previous HFL {hfl} m.","observed_at":f"2022-07-16T{hour:02d}:00:00+05:30","value":actual,"status":trend,"measurement_type":"observation"})
        hist.append(common|{"evidence_id":base_id+"-FORECAST","claim_type":"river_level","claim_text":f"CWC bulletin forecast level at {station}: {forecast} m, forecast valid at 16-07-2022 21:00 local. This is forecast evidence, not an observed level.","reported_at":"2022-07-16T23:59:59+05:30","value":forecast,"measurement_type":"forecast","metadata":common["metadata"]|{"forecast_valid_at":"2022-07-16T21:00:00+05:30","forecast_vintage_time":"not stated in source; conservative availability cutoff is end of report date"}})
    mha="mha_flood_situation_2022-07-16.pdf"; mha_time="2022-07-16T18:00:00+05:30"
    # MHA page 1: official CWC above-danger offsets for Andhra Pradesh stations.
    for station,river,district,above,trend in [("Dowlaiswaram","Godavari","East Godavari",0.96,"Rising"),("Chinturu","Sabri","Alluri Sitharama Raju",6.24,"Rising"),("Kunavaram","Godavari","Alluri Sitharama Raju",9.49,"Rising")]:
        hist.append({"evidence_id":f"HIST-MHA-ABOVE-DANGER-{station.upper()}-20220716","source_label":"historical","source_class":"government_official","source_name":mha,"claim_type":"river_level_above_danger","claim_text":f"MHA report reproduces CWC station status: {river} at {station}, {district}; level {above:g} m above danger level, trend {trend}.","location":station,"reported_at":mha_time,"available_at":mha_time,"value":above,"unit":"m above danger level","status":trend,"measurement_type":"observation","source_page":1,"verified":False,"metadata":{"river":river,"district":district,"state":"Andhra Pradesh","curation":"transcribed from MHA table; this is an offset above danger level, not absolute river stage"}})
    # MHA page 2 is a 24-hour state-reported impact table. Dashes stay unavailable, not zero.
    impact_rows=[("affected_districts",6,"districts","06 districts affected"),("affected_locations",1,"villages","01 village affected"),("affected_population",1991,"persons","population affected"),("damage",18,"fully_damaged_houses","18 houses fully damaged"),("evacuation",7409,"persons","persons evacuated"),("relief_shelter",7374,"persons_in_relief_camps","inmates in relief camps")]
    for kind,value,unit,description in impact_rows:
        hist.append({"evidence_id":f"HIST-MHA-AP-{kind.upper()}-20220716","source_label":"historical","source_class":"government_official","source_name":mha,"claim_type":kind,"claim_text":f"MHA 16 July 2022 1800 Hrs state-reported table (last 24 hours), Andhra Pradesh: {description} = {value}.","location":"Andhra Pradesh (statewide)","reported_at":mha_time,"available_at":mha_time,"value":value,"unit":unit,"status":"reported","measurement_type":"report","source_page":2,"verified":False,"metadata":{"reporting_period":"last 24 hours as of 2022-07-16 1800 Hrs","curation":"manual transcription from MHA table; '-' table cells are preserved as unavailable and not converted to zero"}})
    for date_label,detail in [("2022-07-16","Heavy rainfall at isolated places over Coastal Andhra Pradesh and Yanam"),("2022-07-17","Thunderstorms with lightning at isolated places over Coastal Andhra Pradesh and Yanam")]:
        hist.append({"evidence_id":f"HIST-MHA-WEATHER-{date_label}","source_label":"historical","source_class":"government_official","source_name":mha,"claim_type":"weather_forecast","claim_text":f"MHA report reproduces IMD forecast for {date_label}: {detail}.","location":"Coastal Andhra Pradesh and Yanam","reported_at":mha_time,"available_at":mha_time,"measurement_type":"forecast","source_page":1,"verified":False,"metadata":{"forecast_for":date_label,"forecast_issuer":"IMD, as reproduced by MHA"}})
    hist.append({"evidence_id":"HIST-CWC-AP-GODAVARI-REGIONAL-OUTLOOK-20220716","source_label":"historical","source_class":"government_official","source_name":"cwc_daily_flood_situation_report_2022-07-16.pdf","claim_type":"flood_forecast","claim_text":"CWC advisory states the Godavari flood wave was travelling downstream and water levels in East Godavari and Alluri Sitharama Raju were rising; it said the flood situation would continue for the next 2 to 3 days.","location":"East Godavari and Alluri Sitharama Raju districts","reported_at":"2022-07-16T23:59:59+05:30","available_at":"2022-07-16T23:59:59+05:30","measurement_type":"forecast","source_page":3,"verified":False,"metadata":{"curation":"manual extraction of CWC advisory; qualitative forecast, not a numeric prediction","availability_assumption":"publication time unknown; end-of-day cutoff used to prevent intraday leakage"}})
    for name,location in [("nrsc_godavari_inundation_2022-07-16.pdf","Godavari River, Andhra Pradesh"),("nrsc_sabari_godavari_inundation_2022-07-16.pdf","Sabari and Godavari Rivers, Andhra Pradesh")]:
        hist.append({"evidence_id":f"HIST-MAP-{name}","source_label":"historical","source_class":"government_official","source_name":name,"claim_type":"inundation_map_context","claim_text":"NRSC map document for flood inundation; source text identifies Sentinel-1A during-flood SAR acquisition on 16 July 2022 at 1800 Hrs. Mapped polygons require visual/geospatial interpretation and are not converted to village-level records here.","location":location,"measurement_type":"unknown","source_page":1,"verified":False,"metadata":{"acquisition":"Sentinel-1A SAR, 2022-07-16 1800 Hrs","curation":"map page context only; no georeferenced polygon extraction","availability":"map acquisition time is not publication time"}})
    if not versioned_only:
        (proc/"historical_evidence.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in hist),encoding="utf-8")
    # Corrected temporal representation is written separately so archived outputs remain untouched.
    v2=[]
    ingested=report["created_at_utc"]
    for original in hist:
        row=dict(original); row["ingested_at"]=ingested
        row["published_at"]=None; row["available_at"]=None
        meta=dict(row.get("metadata",{}))
        if row.get("source_name")=="rainfall_tel_hr_cwc_ap_2021_2025.csv":
            meta["availability_limitation"]="source capture/receipt timestamp not supplied; observation timestamp is not treated as availability"
        elif row.get("source_name", "").startswith("cwc_"):
            meta["availability_limitation"]="PDF issue/publication time not established; prior 23:59:59 cutoff was an assumption and is not used as fact"
        elif row.get("source_name", "").startswith("mha_"):
            meta["availability_limitation"]="18:00 is the report-as-of time printed in the report, not verified publication or system availability time"
            row["report_as_of_time"]="2022-07-16T18:00:00+05:30" if "2022-07-16" in row.get("source_name", "") else None
        if row.get("measurement_type")=="forecast":
            valid=meta.get("forecast_valid_at") or meta.get("forecast_for")
            if valid and "T" in valid: row["forecast_valid_at"]=valid
            elif valid: row["forecast_valid_date"]=valid
            row["reported_at"]=None
        if row.get("source_name", "").startswith("nrsc_"):
            meta["availability_limitation"]="satellite acquisition time is not map publication or availability time"
        row["metadata"]=meta
        row["availability_assumption"]={"value":None,"reason":meta.get("availability_limitation","publication/availability timestamp not supplied; left unknown")}
        v2.append(row)
    (proc/"historical_evidence_v2.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in v2),encoding="utf-8")
    report["historical_evidence_records"]=len(hist); report["guideline_passages"]=len(passages)
    report_name="inspection_report_v2.json" if versioned_only else "inspection_report.json"
    (proc/report_name).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    if not versioned_only:
        replace_pdf_pages(proc/"flood_support.sqlite",pages)
    return report
