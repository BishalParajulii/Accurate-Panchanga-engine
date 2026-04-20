

import ephem
import math
from datetime import datetime, timedelta
from typing import Optional
import pytz
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from kundali_calculator import calculate_kundali
from kundali_chart import generate_kundali_chart, generate_kundali_text_report
import os

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

AUSPICIOUS_TITHIS_WITHIN_PAKSHA = [2, 3, 5, 7, 10, 11, 12, 13]
AUSPICIOUS_NAKSHATRAS = [
    "Rohini", "Mrigashira", "Hasta", "Chitra", "Swati",
    "Anuradha", "Uttara Ashadha", "Uttara Phalguni",
    "Uttara Bhadrapada", "Revati", "Pushya"
]
INAUSPICIOUS_YOGAS = [
    "Vishkambha", "Atiganda", "Shula", "Ganda", "Vyaghata",
    "Vajra", "Vyatipata", "Parigha", "Vaidhriti"
]
INAUSPICIOUS_KARANAS = ["Vishti"]

GREG_TO_NEP_MONTH = {
    1: "Magh", 2: "Falgun", 3: "Chaitra", 4: "Baisakh",
    5: "Jestha", 6: "Ashadha", 7: "Shrawan", 8: "Bhadra",
    9: "Ashwin", 10: "Kartik", 11: "Mangsir", 12: "Poush"
}

NEPALI_MONTHS = {
    "Poush": 1, "Magh": 2, "Falgun": 3, "Chaitra": 4,
    "Baisakh": 5, "Jestha": 6, "Ashadha": 7, "Shrawan": 8,
    "Bhadra": 9, "Ashwin": 10, "Kartik": 11, "Mangsir": 12
}

NEPALI_MONTH_NAMES = {
    1: "Poush", 2: "Magh", 3: "Falgun", 4: "Chaitra",
    5: "Baisakh", 6: "Jestha", 7: "Ashadha", 8: "Shrawan",
    9: "Bhadra", 10: "Ashwin", 11: "Kartik", 12: "Mangsir"
}

NEPALI_MONTH_NAMES_NE = {
    1: "पुष", 2: "माघ", 3: "फागुन", 4: "चैत",
    5: "वैशाख", 6: "जेठ", 7: "असार", 8: "साउन",
    9: "भदौ", 10: "असोज", 11: "कात्तिक", 12: "मंसिर"
}

GREG_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

NEPALI_MONTH_DAYS = {
    2082: [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 31],
    2083: [31, 31, 32, 32, 31, 31, 29, 30, 29, 30, 30, 31],
}

def gregorian_to_nepali(greg_date):
    """
    Accurate Nepali date conversion from Gregorian.
    Uses accurate month boundary dates for proper conversion.
    Nepali year increments on Chaitra 1 (around April 13-14)
    """
    g_year = greg_date.year
    g_month = greg_date.month
    g_day = greg_date.day
    
    # Determine Nepali year (changes on Baisakh 1, around April 13-14)
    # Corrected for 2083 transition: April 14, 2026
    if (g_month < 4) or (g_month == 4 and g_day < 14):
        n_year = g_year + 57 - 1
    else:
        n_year = g_year + 57
    
    # Month boundaries: (gregorian_month, start_day, nepali_month_number)
    # These are the exact start dates of each Nepali month in Gregorian calendar
    boundaries = [
        (4, 14, 5),   # Baisakh starts Apr 14
        (5, 15, 6),   # Jestha starts May 15
        (6, 16, 7),   # Ashadha starts Jun 16
        (7, 17, 8),   # Shrawan starts Jul 17
        (8, 17, 9),   # Bhadra starts Aug 17
        (9, 17, 10),  # Ashwin starts Sep 17
        (10, 18, 11), # Kartik starts Oct 18
        (11, 17, 12), # Mangsir starts Nov 17
        (12, 16, 1),  # Poush starts Dec 16
        (1, 15, 2),   # Magh starts Jan 15
        (2, 13, 3),   # Falgun starts Feb 13
        (3, 15, 4),   # Chaitra starts Mar 15
    ]
    
    # Find current Nepali month by finding the most recent boundary
    n_month = 4  # Default to Chaitra
    boundary_month, boundary_day = 3, 16
    
    for b_month, b_day, nep_month in boundaries:
        if g_month > b_month or (g_month == b_month and g_day >= b_day):
            n_month = nep_month
            boundary_month = b_month
            boundary_day = b_day
    
    # Calculate day within month using datetime subtraction
    if boundary_month > g_month:
        # Start date was in previous year
        start_year = g_year - 1
    else:
        start_year = g_year
    
    start_dt = datetime(start_year, boundary_month, boundary_day)
    current_dt = datetime(g_year, g_month, g_day)
    n_day = (current_dt - start_dt).days + 1
    
    return n_year, n_month, n_day


def get_observer(lat, lon, elevation=0):
    obs = ephem.Observer()
    obs.lat = str(lat)
    obs.lon = str(lon)
    obs.elevation = elevation
    # Calculate atmospheric pressure based on elevation using barometric formula
    obs.pressure = 1013.25 * (1 - elevation / 44330) ** 5.255
    obs.horizon = 0  # Horizon at sea level for astronomical calculations
    return obs

def get_longitudes(observer, dt_utc):
    observer.date = dt_utc.strftime('%Y/%m/%d %H:%M:%S')
    sun = ephem.Sun(observer)
    moon = ephem.Moon(observer)
    sun_lon = math.degrees(float(ephem.Ecliptic(sun, epoch=ephem.J2000).lon)) % 360
    moon_lon = math.degrees(float(ephem.Ecliptic(moon, epoch=ephem.J2000).lon)) % 360
    return sun_lon, moon_lon


def tithi_raw(sun_lon, moon_lon):
    return ((moon_lon - sun_lon) % 360) / 12.0


def tithi_index(sun_lon, moon_lon):
    return int(tithi_raw(sun_lon, moon_lon))


def get_tithi_info(raw_idx):
    num = raw_idx + 1  # 1..30
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


def nakshatra_index(moon_lon):
    return int(moon_lon / (360 / 27)) + 1


def yoga_index(sun_lon, moon_lon):
    return int(((sun_lon + moon_lon) % 360) / (360 / 27)) + 1


def karana_index(t_raw):
    half = int(t_raw * 2) % 60
    if half == 0: return 10
    if half == 57: return 7
    if half == 58: return 8
    if half == 59: return 9
    return (half - 1) % 7


def binary_search_transition(observer, lo, hi, lo_val, value_fn, precision_s=10):
    while (hi - lo).total_seconds() > precision_s:
        mid = lo + (hi - lo) / 2
        if value_fn(observer, mid) == lo_val:
            lo = mid
        else:
            hi = mid
    return hi


def scan_day(observer, day_start_utc, day_end_utc, value_fn, info_fn, step_min=15, precision_s=10):
    transitions = []
    cur = day_start_utc
    prev_val = value_fn(observer, cur)
    segment_start = day_start_utc

    while cur < day_end_utc:
        nxt = min(cur + timedelta(minutes=step_min), day_end_utc)
        nxt_val = value_fn(observer, nxt)
        if nxt_val != prev_val:
            exact = binary_search_transition(observer, cur, nxt, prev_val, value_fn, precision_s)
            transitions.append({
                "val": prev_val,
                "info": info_fn(prev_val),
                "start_utc": segment_start,
                "end_utc": exact,
            })
            prev_val = nxt_val
            segment_start = exact
        cur = nxt

    transitions.append({
        "val": prev_val,
        "info": info_fn(prev_val),
        "start_utc": segment_start,
        "end_utc": None,
    })
    return transitions


def format_transitions(raw, tz, day_start_local, day_start_utc=None, prev_day_val=None):
    out = []
    for i, t in enumerate(raw):
        start_local = pytz.utc.localize(t["start_utc"]).astimezone(tz)
        end_local = pytz.utc.localize(t["end_utc"]).astimezone(tz) if t["end_utc"] else None
        continued = i == 0 and prev_day_val is not None and t["val"] == prev_day_val
        entry = {
            **t["info"],
            "start": start_local.strftime("%H:%M:%S"),
            "end": end_local.strftime("%H:%M:%S") if end_local else "→ next day",
            "end_dt": end_local,
            "continued": continued,
        }
        out.append(entry)
    return out


def get_nepali_calendar_month(nep_year, nep_month, lat=27.7172, lon=85.3240, elevation=1400, tz_name="Asia/Kathmandu"):
    """Get calendar data for a specific Nepali month"""
    if nep_year not in NEPALI_MONTH_DAYS:
        # Fallback to a default number of days or raise error
        month_days = 30
    else:
        month_days = NEPALI_MONTH_DAYS[nep_year][nep_month - 1]
    
    # Calculate starting Gregorian date
    boundaries = [
        (4, 14, 5), (5, 15, 6), (6, 16, 7), (7, 17, 8),
        (8, 17, 9), (9, 17, 10), (10, 18, 11), (11, 17, 12),
        (12, 16, 1), (1, 15, 2), (2, 13, 3), (3, 15, 4)
    ]
    
    b_month, b_day = 4, 14
    for bm, bd, nm in boundaries:
        if nm == nep_month:
            b_month, b_day = bm, bd
            break
            
    if nep_month < 5 and nep_month != 1:
        g_year = nep_year - 57 + 1
    else:
        g_year = nep_year - 57
        
    start_date = datetime(g_year, b_month, b_day)
    
    # First day weekday (0=Monday, 6=Sunday)
    first_day_weekday = start_date.weekday()
    # Adjust to 0=Sunday for calendar grid
    first_day_grid = (first_day_weekday + 1) % 7
    
    weeks = []
    current_week = [None] * first_day_grid
    
    spanning_greg_months = set()
    
    for day in range(1, month_days + 1):
        greg_date = start_date + timedelta(days=day - 1)
        date_str = greg_date.strftime("%Y-%m-%d")
        spanning_greg_months.add(greg_date.month)
        
        try:
            panchanga = calculate_panchanga(date_str, lat, lon, elevation, tz_name)
            primary_tithi = panchanga["tithis"][0] if panchanga["tithis"] else {}
            
            day_data = {
                "greg_date": date_str,
                "greg_day": greg_date.day,
                "greg_month_name": GREG_MONTH_NAMES[greg_date.month],
                "nep_date": f"{nep_year}-{nep_month}-{day}",
                "nep_day": day,
                "tithi": primary_tithi.get("name", ""),
                "tithi_ne": primary_tithi.get("name_ne", ""),
                "paksha": primary_tithi.get("paksha", ""),
                "paksha_ne": primary_tithi.get("paksha_ne", ""),
                "panchanga": panchanga
            }
        except Exception as e:
            day_data = {"nep_day": day, "error": str(e)}
            
        current_week.append(day_data)
        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []
            
    if current_week:
        current_week.extend([None] * (7 - len(current_week)))
        weeks.append(current_week)
        
    # Sort spanning months and format names
    sorted_months = sorted(list(spanning_greg_months))
    greg_month_str = " / ".join([GREG_MONTH_NAMES[m] for m in sorted_months])
    
    return {
        "nep_year": nep_year,
        "nep_month": nep_month,
        "nep_month_name": NEPALI_MONTH_NAMES[nep_month],
        "nep_month_name_ne": NEPALI_MONTH_NAMES_NE[nep_month],
        "greg_months_spanning": greg_month_str,
        "weeks": weeks
    }


def get_calendar_month(year, month, lat=27.7172, lon=85.3240, elevation=1400, tz_name="Asia/Kathmandu"):
    """Get calendar data for the entire month with tithi and panchanga info for each day"""
    import calendar
    
    cal_matrix = calendar.monthcalendar(year, month)
    calendar_data = {
        "year": year,
        "month": month,
        "month_name": GREG_TO_NEP_MONTH.get(month, "Unknown"),
        "weeks": []
    }
    
    for week in cal_matrix:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                try:
                    panchanga = calculate_panchanga(date_str, lat, lon, elevation, tz_name)
                    nep_year, nep_month, nep_day = gregorian_to_nepali(datetime(year, month, day))
                    
                    primary_tithi = panchanga["tithis"][0] if panchanga["tithis"] else {}
                    
                    day_data = {
                        "greg_date": date_str,
                        "greg_day": day,
                        "nep_date": f"{nep_year}-{nep_month}-{nep_day}",
                        "nep_day": nep_day,
                        "tithi": primary_tithi.get("name", ""),
                        "tithi_ne": primary_tithi.get("name_ne", ""),
                        "paksha": primary_tithi.get("paksha", ""),
                        "paksha_ne": primary_tithi.get("paksha_ne", ""),
                        "panchanga": panchanga
                    }
                    week_data.append(day_data)
                except Exception as e:
                    week_data.append({"greg_day": day, "error": str(e)})
        
        calendar_data["weeks"].append(week_data)
    
    return calendar_data


def calculate_panchanga(date_str, lat=27.7172, lon=85.3240, elevation=1400, tz_name="Asia/Kathmandu"):
    tz = pytz.timezone(tz_name)
    y, m, d = map(int, date_str.split("-"))
    day_start = tz.localize(datetime(y, m, d, 0, 0, 0))
    day_end = tz.localize(datetime(y, m, d, 23, 59, 59))
    ds_utc = day_start.astimezone(pytz.utc).replace(tzinfo=None)
    de_utc = day_end.astimezone(pytz.utc).replace(tzinfo=None)

    obs = get_observer(lat, lon, elevation)

    def vfn_tithi(o, dt):
        s, m = get_longitudes(o, dt); return tithi_index(s, m)
    def vfn_nak(o, dt):
        _, m = get_longitudes(o, dt); return nakshatra_index(m)
    def vfn_yoga(o, dt):
        s, m = get_longitudes(o, dt); return yoga_index(s, m)
    def vfn_karana(o, dt):
        s, m = get_longitudes(o, dt); return karana_index(tithi_raw(s, m))

    def ifn_tithi(v): return get_tithi_info(v)
    def ifn_nak(v): return {"number": v, "name": NAKSHATRA_NAMES[(v-1) % 27]}
    def ifn_yoga(v): return {"number": v, "name": YOGA_NAMES[(v-1) % 27]}
    def ifn_karana(v): return {"number": v, "name": KARANA_NAMES[v % len(KARANA_NAMES)], "name_ne": KARANA_NAMES_NEPALI[v % len(KARANA_NAMES_NEPALI)]}

    prev_tithi_val = vfn_tithi(obs, ds_utc - timedelta(seconds=1))
    tithis = format_transitions(
        scan_day(obs, ds_utc, de_utc, vfn_tithi, ifn_tithi),
        tz,
        day_start,
        ds_utc,
        prev_day_val=prev_tithi_val,
    )
    naks = format_transitions(scan_day(obs, ds_utc, de_utc, vfn_nak, ifn_nak), tz, day_start)
    yogas = format_transitions(scan_day(obs, ds_utc, de_utc, vfn_yoga, ifn_yoga), tz, day_start)
    karanas = format_transitions(scan_day(obs, ds_utc, de_utc, vfn_karana, ifn_karana), tz, day_start)

    obs.date = ds_utc.strftime('%Y/%m/%d %H:%M:%S')
    sunrise = pytz.utc.localize(obs.next_rising(ephem.Sun()).datetime()).astimezone(tz)
    sunset = pytz.utc.localize(obs.next_setting(ephem.Sun()).datetime()).astimezone(tz)

    return {
        "date": date_str,
        "nepali_month": GREG_TO_NEP_MONTH[m],
        "location": {"lat": lat, "lon": lon, "elevation": elevation, "timezone": tz_name},
        "sunrise": sunrise.strftime("%H:%M:%S"),
        "sunset": sunset.strftime("%H:%M:%S"),
        "tithis": tithis,
        "nakshatras": naks,
        "yogas": yogas,
        "karanas": karanas,
    }


def print_panchanga(p):
    W = 58
    sep = "─" * W
    print(f"\n{'═'*W}")
    print(f"  🕉  PANCHANGA  |  {p['date']}  |  {p['location']['timezone']}")
    print(f"{'═'*W}")
    print(f"  📍 {p['location']['lat']}°N  {p['location']['lon']}°E  |  elev {p['location']['elevation']}m")
    print(f"  🌅 Sunrise : {p['sunrise']}     🌇 Sunset : {p['sunset']}")
    print(sep)

    def show(label, items, name_key="name", extra_key=None):
        print(f"  {label}")
        for t in items:
            line = f"     {t[name_key]}"
            if extra_key and extra_key in t:
                line += f"  ({t[extra_key]})"
            if "paksha" in t:
                line = f"     {p['nepali_month']} {t['paksha']} {t[name_key]}  ({t.get('name_ne','')})"
            if t.get('continued'):
                line += "  (continues from previous day)"
            print(line)
            print(f"       {t['start']}  →  {t['end']}")
        print(sep)

    show("📅 TITHI", p["tithis"])
    show("🌙 NAKSHATRA", p["nakshatras"])
    show("☀  YOGA", p["yogas"])
    show("🔮 KARANA", p["karanas"], extra_key="name_ne")

    if len(p["tithis"]) > 1:
        print(f"  ⚠️  KSHAYA TITHI: {len(p['tithis'])} tithis transition today!")
    print(f"{'═'*W}\n")


def find_muhurta(date_str, lat=27.7172, lon=85.3240):
    p = calculate_panchanga(date_str, lat, lon)
    windows = []
    for t in p["tithis"]:
        if t.get("within_paksha") not in AUSPICIOUS_TITHIS_WITHIN_PAKSHA:
            continue
        for n in p["nakshatras"]:
            if n["name"] not in AUSPICIOUS_NAKSHATRAS:
                continue
            for y in p["yogas"]:
                if y["name"] in INAUSPICIOUS_YOGAS:
                    continue
                for k in p["karanas"]:
                    if k["name"] in INAUSPICIOUS_KARANAS:
                        continue
                    windows.append({
                        "tithi": f"{t['paksha']} {t['name']}",
                        "nakshatra": n["name"],
                        "yoga": y["name"],
                        "karana": k["name"],
                        "window": f"{t['start']}–{t['end']}",
                    })
    return windows


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

@app.get("/panchanga/{date_str}")
async def get_panchanga(date_str: str):
    try:
        p = calculate_panchanga(date_str)
        return p
    except Exception as e:
        return {"error": str(e)}


@app.get("/calendar/{year}/{month}")
async def get_calendar(year: int, month: int):
    try:
        cal_data = get_calendar_month(year, month)
        return cal_data
    except Exception as e:
        return {"error": str(e)}


@app.get("/nepali-calendar/{year}/{month}")
async def get_nepali_calendar(year: int, month: int):
    try:
        cal_data = get_nepali_calendar_month(year, month)
        return cal_data
    except Exception as e:
        return {"error": str(e)}


class KundaliRequest(BaseModel):
    birth_date: str
    birth_time: str
    latitude: float = 27.7172
    longitude: float = 85.3240
    timezone: str = "Asia/Kathmandu"


@app.post("/kundali")
async def generate_kundali(request: KundaliRequest):
    """Generate Janma Kundali"""
    try:
        # Parse birth datetime
        birth_datetime = datetime.fromisoformat(f"{request.birth_date}T{request.birth_time}")

        # Calculate kundali
        kundali_data = calculate_kundali(
            birth_datetime,
            request.latitude,
            request.longitude,
            request.timezone,
        )

        # Generate charts
        timestamp = request.birth_time.replace(':', '-')
        janma_filename = f"kundali_janma_{request.birth_date}_{timestamp}.svg"
        nav_filename = f"kundali_navamsha_{request.birth_date}_{timestamp}.svg"
        
        janma_path = os.path.join("static", janma_filename)
        nav_path = os.path.join("static", nav_filename)
        
        generate_kundali_chart(kundali_data, janma_path, is_navamsha=False)
        generate_kundali_chart(kundali_data, nav_path, is_navamsha=True)

        return {
            "kundali_data": kundali_data,
            "janma_chart_url": f"/static/{janma_filename}",
            "navamsha_chart_url": f"/static/{nav_filename}",
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/kundali-chart/{filename}")
async def get_kundali_chart(filename: str):
    """Serve kundali chart SVG"""
    file_path = os.path.join("static", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/svg+xml")
    return {"error": "Chart not found"}


if __name__ == "__main__":
    print("Calculating... (takes ~30s for precision scan)\n")

    p = calculate_panchanga("2026-04-15", 27.7172, 85.3240, 1400, "Asia/Kathmandu")
    print_panchanga(p)

    print("📍 Same date — New York:")
    p2 = calculate_panchanga("2026-04-15", 40.7128, -74.0060, 10, "America/New_York")
    print_panchanga(p2)

    print("🔮 Muhurta windows (Kathmandu):")
    mw = find_muhurta("2026-04-15")
    if mw:
        for m in mw[:3]:
            print(f"  ✅ {m['tithi']} | {m['nakshatra']} | Yoga: {m['yoga']} | {m['window']}")
    else:
        print("  No fully auspicious windows today")
    print("Calculating... (takes ~30s for precision scan)\n")

    p = calculate_panchanga("2026-04-15", 27.7172, 85.3240, 1400, "Asia/Kathmandu")
    print_panchanga(p)

    print("📍 Same date — New York:")
    p2 = calculate_panchanga("2026-04-15", 40.7128, -74.0060, 10, "America/New_York")
    print_panchanga(p2)

    print("🔮 Muhurta windows (Kathmandu):")
    mw = find_muhurta("2026-04-15")
    if mw:
        for m in mw[:3]:
            print(f"  ✅ {m['tithi']} | {m['nakshatra']} | Yoga: {m['yoga']} | {m['window']}")
    else:
        print("  No fully auspicious windows today")
