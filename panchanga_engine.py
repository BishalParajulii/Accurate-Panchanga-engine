

import ephem
import math
from datetime import datetime, timedelta
from typing import Optional
import pytz
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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
