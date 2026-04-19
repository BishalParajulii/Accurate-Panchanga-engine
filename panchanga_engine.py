import swisseph as swe
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import pytz
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from kundali_calculator import calculate_kundali, julian_day_from_datetime, normalize_longitude
from kundali_chart import generate_kundali_chart
import os

# Set ephemeris path
swe.set_ephe_path()
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
SWE_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima"
]
TITHI_NAMES_NEPALI = [
    "प्रतिपदा", "द्वितीया", "तृतीया", "चतुर्थी", "पञ्चमी",
    "षष्ठी", "सप्तमी", "अष्टमी", "नवमी", "दशमी",
    "एकादशी", "द्वादशी", "त्रयोदशी", "चतुर्दशी", "पूर्णिमा"
]
PAKSHA = ["Shukla", "Krishna"]
PAKSHA_NEPALI = ["शुक्ल", "कृष्ण"]

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

YOGA_NAMES = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarman", "Dhriti", "Shula", "Ganda",
    "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma",
    "Indra", "Vaidhriti"
]

KARANA_NAMES = [
    "Bava", "Balava", "Kaulava", "Taitila", "Garaja",
    "Vanija", "Vishti", "Shakuni", "Chatushpada", "Naga", "Kimstughna"
]
KARANA_NAMES_NEPALI = [
    "बव", "बालव", "कौलव", "तैतिल", "गरज",
    "वणिज", "विष्टि", "शकुनि", "चतुष्पाद", "नाग", "किंस्तुघ्न"
]

GREG_TO_NEP_MONTH = {
    1: "Magh", 2: "Falgun", 3: "Chaitra", 4: "Baisakh",
    5: "Jestha", 6: "Ashadha", 7: "Shrawan", 8: "Bhadra",
    9: "Ashwin", 10: "Kartik", 11: "Mangsir", 12: "Poush"
}

NEPALI_MONTH_NAMES_NE = {
    1: "पुष", 2: "माघ", 3: "फागुन", 4: "चैत",
    5: "वैशाख", 6: "जेठ", 7: "असार", 8: "साउन",
    9: "भदौ", 10: "असोज", 11: "कात्तिक", 12: "मंसिर"
}

NEPALI_MONTH_DAYS = {
    2082: [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 31],
    2083: [31, 31, 32, 32, 31, 31, 29, 30, 29, 30, 30, 31],
}

def gregorian_to_nepali(greg_date):
    g_year = greg_date.year
    g_month = greg_date.month
    g_day = greg_date.day
    
    if (g_month < 4) or (g_month == 4 and g_day < 14):
        n_year = g_year + 57 - 1
    else:
        n_year = g_year + 57
    
    boundaries = [
        (4, 14, 5), (5, 15, 6), (6, 16, 7), (7, 17, 8),
        (8, 17, 9), (9, 17, 10), (10, 18, 11), (11, 17, 12),
        (12, 16, 1), (1, 15, 2), (2, 13, 3), (3, 15, 4),
    ]
    
    n_month = 4
    boundary_month, boundary_day = 3, 15
    
    for b_month, b_day, nep_month in boundaries:
        if g_month > b_month or (g_month == b_month and g_day >= b_day):
            n_month = nep_month
            boundary_month = b_month
            boundary_day = b_day
    
    start_dt = datetime(g_year if boundary_month <= g_month else g_year - 1, boundary_month, boundary_day)
    n_day = (datetime(g_year, g_month, g_day) - start_dt).days + 1
    
    return n_year, n_month, n_day

def get_sidereal_longitudes(dt_utc):
    jd = julian_day_from_datetime(dt_utc)
    sun_pos, _ = swe.calc_ut(jd, swe.SUN, SWE_FLAGS)
    moon_pos, _ = swe.calc_ut(jd, swe.MOON, SWE_FLAGS)
    return normalize_longitude(sun_pos[0]), normalize_longitude(moon_pos[0])

def get_tithi_info(moon_lon, sun_lon):
    diff = normalize_longitude(moon_lon - sun_lon)
    raw_idx = int(diff / 12)
    num = raw_idx + 1
    if num <= 15:
        paksha_idx, within = 0, num
    else:
        paksha_idx, within = 1, num - 15
    
    if within == 15:
        name = "Purnima" if paksha_idx == 0 else "Amavasya"
        name_ne = "पूर्णिमा" if paksha_idx == 0 else "औंसी"
    else:
        name = TITHI_NAMES[within - 1]
        name_ne = TITHI_NAMES_NEPALI[within - 1]
        
    return {
        "number": num,
        "name": name,
        "name_ne": name_ne,
        "paksha": PAKSHA[paksha_idx],
        "paksha_ne": PAKSHA_NEPALI[paksha_idx],
        "within_paksha": within,
    }

def binary_search_transition(dt_start, dt_end, value_fn, target_val, precision_s=10):
    lo, hi = dt_start, dt_end
    while (hi - lo).total_seconds() > precision_s:
        mid = lo + (hi - lo) / 2
        if value_fn(mid) == target_val:
            lo = mid
        else:
            hi = mid
    return hi

def scan_day(ds_utc, de_utc, value_fn, info_fn, step_min=30):
    transitions = []
    cur = ds_utc
    prev_val = value_fn(cur)
    segment_start = ds_utc
    
    while cur < de_utc:
        nxt = min(cur + timedelta(minutes=step_min), de_utc)
        nxt_val = value_fn(nxt)
        if nxt_val != prev_val:
            exact = binary_search_transition(cur, nxt, value_fn, prev_val)
            transitions.append({
                "info": info_fn(prev_val),
                "start_utc": segment_start,
                "end_utc": exact
            })
            prev_val = nxt_val
            segment_start = exact
        cur = nxt
        
    transitions.append({
        "info": info_fn(prev_val),
        "start_utc": segment_start,
        "end_utc": None
    })
    return transitions

def calculate_panchanga(date_str, lat=27.7172, lon=85.3240, elevation=1400, tz_name="Asia/Kathmandu"):
    tz = pytz.timezone(tz_name)
    y, m, d = map(int, date_str.split("-"))
    day_start = tz.localize(datetime(y, m, d, 0, 0, 0))
    day_end = tz.localize(datetime(y, m, d, 23, 59, 59))
    ds_utc = day_start.astimezone(pytz.utc).replace(tzinfo=None)
    de_utc = day_end.astimezone(pytz.utc).replace(tzinfo=None)

    def vfn_tithi(dt):
        s, m = get_sidereal_longitudes(dt); return int(normalize_longitude(m - s) / 12)
    def vfn_nak(dt):
        _, m = get_sidereal_longitudes(dt); return int(m / (360 / 27))
    def vfn_yoga(dt):
        s, m = get_sidereal_longitudes(dt); return int(normalize_longitude(s + m) / (360 / 27))
    def vfn_karana(dt):
        s, m = get_sidereal_longitudes(dt); return int(normalize_longitude(m - s) / 6)

    def ifn_tithi(v): return get_tithi_info(v * 12 + 1, 0) # Dummy s_lon for info
    def ifn_nak(v): return {"number": v+1, "name": NAKSHATRA_NAMES[v % 27]}
    def ifn_yoga(v): return {"number": v+1, "name": YOGA_NAMES[v % 27]}
    def ifn_karana(v):
        if v == 0: k_idx = 10 # Kimstughna
        elif v >= 57: k_idx = v - 50 # Shakuni, Chatushpada, Naga
        else: k_idx = (v - 1) % 7
        return {"number": v, "name": KARANA_NAMES[k_idx], "name_ne": KARANA_NAMES_NEPALI[k_idx]}

    def format_t(raw, tz):
        out = []
        for t in raw:
            s_loc = pytz.utc.localize(t["start_utc"]).astimezone(tz)
            e_loc = pytz.utc.localize(t["end_utc"]).astimezone(tz) if t["end_utc"] else None
            out.append({**t["info"], "start": s_loc.strftime("%H:%M:%S"), "end": e_loc.strftime("%H:%M:%S") if e_loc else "→ next day"})
        return out

    tithis = format_t(scan_day(ds_utc, de_utc, vfn_tithi, ifn_tithi), tz)
    naks = format_t(scan_day(ds_utc, de_utc, vfn_nak, ifn_nak), tz)
    yogas = format_t(scan_day(ds_utc, de_utc, vfn_yoga, ifn_yoga), tz)
    karanas = format_t(scan_day(ds_utc, de_utc, vfn_karana, ifn_karana), tz)

    import ephem
    obs = ephem.Observer(); obs.lat, obs.lon, obs.elevation = str(lat), str(lon), elevation
    obs.date = ds_utc.strftime('%Y/%m/%d %H:%M:%S')
    sunrise = pytz.utc.localize(obs.next_rising(ephem.Sun()).datetime()).astimezone(tz)
    sunset = pytz.utc.localize(obs.next_setting(ephem.Sun()).datetime()).astimezone(tz)

    n_year, n_month, n_day = gregorian_to_nepali(datetime(y, m, d))

    return {
        "date": date_str,
        "nepali_date": f"{n_year}-{n_month}-{n_day}",
        "nepali_month": GREG_TO_NEP_MONTH[m],
        "location": {"lat": lat, "lon": lon, "elevation": elevation, "timezone": tz_name},
        "sunrise": sunrise.strftime("%H:%M:%S"),
        "sunset": sunset.strftime("%H:%M:%S"),
        "tithis": tithis,
        "nakshatras": naks,
        "yogas": yogas,
        "karanas": karanas,
    }

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root(): return FileResponse("static/index.html")

@app.get("/panchanga/{date_str}")
async def get_panchanga(date_str: str, lat: float = 27.7172, lon: float = 85.3240):
    try: return calculate_panchanga(date_str, lat, lon)
    except Exception as e: return {"error": str(e)}

@app.get("/nepali-calendar/{year}/{month}")
async def get_nepali_calendar(year: int, month: int, lat: float = 27.7172, lon: float = 85.3240):
    try:
        month_days = NEPALI_MONTH_DAYS.get(year, [30]*12)[month-1]
        g_year = year - 57
        start_month_map = {5:(4,14), 6:(5,15), 7:(6,16), 8:(7,17), 9:(8,17), 10:(9,17), 11:(10,18), 12:(11,17), 1:(12,16), 2:(1,15), 3:(2,13), 4:(3,15)}
        gm, gd = start_month_map[month]
        if month < 5 and month != 1: g_year += 1
        
        start_date = datetime(g_year, gm, gd)
        weeks = []
        current_week = [None] * ((start_date.weekday() + 1) % 7)
        
        for day in range(1, month_days + 1):
            g_date = start_date + timedelta(days=day - 1)
            p = calculate_panchanga(g_date.strftime("%Y-%m-%d"), lat, lon)
            current_week.append({
                "greg_date": g_date.strftime("%Y-%m-%d"),
                "greg_day": g_date.day,
                "nep_day": day,
                "tithi_ne": p["tithis"][0]["name_ne"],
                "paksha_ne": p["tithis"][0]["paksha_ne"],
                "panchanga": p
            })
            if len(current_week) == 7:
                weeks.append(current_week); current_week = []
        if current_week: current_week.extend([None] * (7 - len(current_week))); weeks.append(current_week)
        
        return {
            "nep_year": year, "nep_month": month, "nep_month_name_ne": NEPALI_MONTH_NAMES_NE[month],
            "greg_months_spanning": f"{start_date.strftime('%B')} / {(start_date + timedelta(days=month_days)).strftime('%B')}",
            "weeks": weeks
        }
    except Exception as e: return {"error": str(e)}

class KundaliRequest(BaseModel):
    birth_date: str; birth_time: str; latitude: float; longitude: float; timezone: str = "Asia/Kathmandu"

@app.post("/kundali")
async def generate_kundali(request: KundaliRequest):
    try:
        dt = datetime.fromisoformat(f"{request.birth_date}T{request.birth_time}")
        data = calculate_kundali(dt, request.latitude, request.longitude, request.timezone)
        ts = request.birth_time.replace(':', '-')
        j_file, n_file = f"kj_{request.birth_date}_{ts}.svg", f"kn_{request.birth_date}_{ts}.svg"
        generate_kundali_chart(data, os.path.join("static", j_file), False)
        generate_kundali_chart(data, os.path.join("static", n_file), True)
        return {"kundali_data": data, "janma_chart_url": f"/static/{j_file}", "navamsha_chart_url": f"/static/{n_file}"}
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
