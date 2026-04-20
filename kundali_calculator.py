import swisseph as swe
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import pytz

# Set ephemeris path (you may need to download ephemeris files)
swe.set_ephe_path()
# Use sidereal zodiac with Lahiri ayanamsa for Vedic-style kundali output
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

# Swiss Ephemeris flags for accurate, topocentric calculations
SWE_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_TOPOCTR

# Planet constants
PLANETS = {
    'sun': swe.SUN,
    'moon': swe.MOON,
    'mars': swe.MARS,
    'mercury': swe.MERCURY,
    'jupiter': swe.JUPITER,
    'venus': swe.VENUS,
    'saturn': swe.SATURN,
    'rahu': swe.TRUE_NODE,
    'ketu': swe.TRUE_NODE,
}

PLANET_GEMS = {
    'sun': 'माणिक्य (Ruby)',
    'moon': 'मोती (Pearl)',
    'mars': 'मुगा (Coral)',
    'mercury': 'पन्ना (Emerald)',
    'jupiter': 'पुष्पराज (Yellow Sapphire)',
    'venus': 'हीरा (Diamond)',
    'saturn': 'नीलम (Blue Sapphire)',
    'rahu': 'गोमेद (Hessonite)',
    'ketu': 'लहसुनिया (Cat\'s Eye)'
}

PLANET_NAMES = {
    'sun': 'सूर्य', 'moon': 'चन्द्र', 'mars': 'मंगल', 'mercury': 'बुध',
    'jupiter': 'गुरु', 'venus': 'शुक्र', 'saturn': 'शनि',
    'rahu': 'राहु', 'ketu': 'केतु'
}

RAASHI_NAMES = [
    "मेष", "वृषभ", "मिथुन", "कर्कट", "सिंह", "कन्या",
    "तुला", "वृश्चिक", "धनु", "मकर", "कुम्भ", "मीन"
]

RAASHI_NAMES_EN = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

RAASHI_LORDS = [
    'Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury',
    'Venus', 'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter'
]

NAKSHATRA_NAMES_NE = [
    "अश्विनी", "भरणी", "कृत्तिका", "रोहिणी", "मृगशीर्षा",
    "आर्द्रा", "पुनर्वसु", "पुष्य", "आश्लेषा", "मघा",
    "पूर्व फाल्गुनी", "उत्तर फाल्गुनी", "हस्त", "चित्रा", "स्वाती",
    "विशाखा", "अनुराधा", "ज्येष्ठा", "मूला", "पूर्वाषाढा",
    "उत्तराषाढा", "श्रवण", "धनिष्ठा", "शतभिषा",
    "पूर्व भाद्रपदा", "उत्तर भाद्रपदा", "रेवती"
]

HOUSE_NAMES = [
    "प्रथम भाव", "द्वितीय भाव", "तृतीय भाव", "चतुर्थ भाव",
    "पञ्चम भाव", "षष्ठ भाव", "सप्तम भाव", "अष्टम भाव",
    "नवम भाव", "दशम भाव", "एकादश भाव", "द्वादश भाव"
]

# Nakshatra Syllables (Akshar) - 4 padas for each 27 nakshatras
NAKSHATRA_AKSHAR = [
    ["चु", "चे", "चो", "ला"], # Ashwini
    ["ली", "लू", "ले", "लो"], # Bharani
    ["अ", "इ", "उ", "ए"],    # Krittika
    ["ओ", "वा", "वी", "वू"], # Rohini
    ["वे", "वो", "का", "की"], # Mrigashira
    ["कु", "घ", "ङ", "छ"],    # Ardra
    ["के", "को", "हा", "ही"], # Punarvasu
    ["हू", "हे", "हो", "डा"], # Pushya
    ["डी", "डू", "डे", "डो"], # Ashlesha
    ["मा", "मी", "मू", "मे"], # Magha
    ["मो", "टा", "टी", "टू"], # Purva Phalguni
    ["टे", "टो", "पा", "पी"], # Uttara Phalguni
    ["पू", "ष", "ण", "ठ"],    # Hasta
    ["पे", "पो", "रा", "री"], # Chitra
    ["रू", "रे", "रो", "ता"], # Swati
    ["ती", "तू", "ते", "तो"], # Vishakha
    ["ना", "नी", "नू", "ने"], # Anuradha
    ["नो", "या", "यी", "यू"], # Jyeshtha
    ["ये", "यो", "भा", "भी"], # Mula
    ["भू", "धा", "फा", "ढा"], # Purva Ashadha
    ["भे", "भो", "जा", "जी"], # Uttara Ashadha
    ["खी", "खूँ", "खे", "खो"], # Shravana
    ["गा", "गी", "गू", "गे"], # Dhanishta
    ["गो", "सा", "सी", "सू"], # Shatabhisha
    ["से", "सो", "दा", "दी"], # Purva Bhadrapada
    ["दू", "थ", "झ", "ञ"],    # Uttara Bhadrapada
    ["दे", "दो", "चा", "ची"]  # Revati
]

DASHA_LORDS = ['ketu', 'venus', 'sun', 'moon', 'mars', 'rahu', 'jupiter', 'saturn', 'mercury']
DASHA_LORDS_NEPALI = ['केतु', 'शुक्र', 'सूर्य', 'चन्द्र', 'मंगल', 'राहु', 'गुरु', 'शनि', 'बुध']
DASHA_YEARS = [7, 20, 6, 10, 7, 18, 16, 19, 17]

def decimal_to_dms(decimal_deg):
    """Convert decimal degrees to Degrees:Minutes:Seconds format"""
    d = int(decimal_deg)
    m = int((decimal_deg - d) * 60)
    s = int((decimal_deg - d - m/60) * 3600)
    return f"{d:02d}° {m:02d}' {s:02d}\""

def normalize_longitude(longitude: float) -> float:
    return longitude % 360.0


def julian_day_from_datetime(dt: datetime) -> float:
    fraction = dt.hour + dt.minute / 60.0 + dt.second / 3600.0 + dt.microsecond / 3_600_000_000.0
    return swe.julday(dt.year, dt.month, dt.day, fraction)


def get_planet_position(jd: float, planet: int) -> Tuple[float, float, float]:
    pos, ret = swe.calc_ut(jd, planet, SWE_FLAGS)
    return normalize_longitude(pos[0]), pos[1], pos[3]  # longitude, latitude, speed


def get_true_node_position(jd: float) -> Tuple[float, float, float]:
    pos, ret = swe.calc_ut(jd, swe.TRUE_NODE, SWE_FLAGS)
    return normalize_longitude(pos[0]), pos[1], pos[3]


def get_house_cusps(jd: float, lat: float, lon: float, hsys: str = 'W') -> List[float]:
    """Use whole-sign houses for Vedic kundali calculation."""
    cusps, ascmc = swe.houses(jd, lat, lon, hsys.encode())
    return [normalize_longitude(c) for c in cusps]


def get_ascendant(jd: float, lat: float, lon: float) -> float:
    cusps, ascmc = swe.houses(jd, lat, lon, b'W')
    return normalize_longitude(ascmc[0])

def longitude_to_raashi(longitude: float) -> Tuple[int, float]:
    raashi = int(longitude / 30) % 12
    degrees_in_raashi = longitude % 30
    return raashi, degrees_in_raashi

def longitude_to_nakshatra(longitude: float) -> Tuple[int, float]:
    nakshatra_span = 360 / 27
    nakshatra = int(longitude / nakshatra_span) % 27
    degrees_in_nakshatra = longitude % nakshatra_span
    pada = int(degrees_in_nakshatra / (nakshatra_span / 4)) + 1
    return nakshatra, pada

def longitude_to_navamsha(longitude: float) -> int:
    raashi_idx = int(longitude / 30) % 12
    degrees_in_raashi = longitude % 30
    navamsha_idx_in_raashi = int(degrees_in_raashi / (30/9))
    start_raashi = [0, 9, 6, 3][raashi_idx % 4]
    return (start_raashi + navamsha_idx_in_raashi) % 12

TITHI_NAMES = [
    "Shukla Pratipada", "Shukla Dwitiya", "Shukla Tritiya", "Shukla Chaturthi", "Shukla Panchami",
    "Shukla Shashthi", "Shukla Saptami", "Shukla Ashtami", "Shukla Navami", "Shukla Dashami",
    "Shukla Ekadashi", "Shukla Dwadashi", "Shukla Trayodashi", "Shukla Chaturdashi", "Purnima",
    "Krishna Pratipada", "Krishna Dwitiya", "Krishna Tritiya", "Krishna Chaturthi", "Krishna Panchami",
    "Krishna Shashthi", "Krishna Saptami", "Krishna Ashtami", "Krishna Navami", "Krishna Dashami",
    "Krishna Ekadashi", "Krishna Dwadashi", "Krishna Trayodashi", "Krishna Chaturdashi", "Amavasya"
]

YOGA_NAMES = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda", "Sukarma", "Dhriti",
    "Shula", "Ganda", "Vajra", "Siddhi", "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyaghata",
    "Harshana", "Vajra", "Siddhi", "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyaghata",
    "Harshana", "Vajra"
]

KARANA_NAMES = [
    "Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti",
    "Shakuni", "Chatushpada", "Naga", "Kimstughna"
]

# 0: Deva, 1: Manushya, 2: Rakshasa
NAKSHATRA_GANA = [
    'Deva', 'Manushya', 'Rakshasa', 'Manushya', 'Deva', 'Manushya', 
    'Deva', 'Deva', 'Rakshasa', 'Rakshasa', 'Manushya', 'Manushya', 
    'Deva', 'Rakshasa', 'Deva', 'Rakshasa', 'Deva', 'Rakshasa', 
    'Rakshasa', 'Manushya', 'Manushya', 'Deva', 'Rakshasa', 'Rakshasa', 
    'Manushya', 'Manushya', 'Deva'
]

# Nadi: 0: Adi, 1: Madhya, 2: Antya (Zig-zag pattern: 1-2-3-3-2-1)
NAKSHATRA_NADI = [
    'Adi', 'Madhya', 'Antya', 'Antya', 'Madhya', 'Adi',
    'Adi', 'Madhya', 'Antya', 'Antya', 'Madhya', 'Adi',
    'Adi', 'Madhya', 'Antya', 'Antya', 'Madhya', 'Adi',
    'Adi', 'Madhya', 'Antya', 'Antya', 'Madhya', 'Adi',
    'Adi', 'Madhya', 'Antya'
]

NAKSHATRA_YONI = [
    'Horse', 'Elephant', 'Sheep', 'Serpent', 'Serpent', 'Dog',
    'Cat', 'Sheep', 'Cat', 'Rat', 'Rat', 'Cow',
    'Buffalo', 'Tiger', 'Buffalo', 'Tiger', 'Deer', 'Deer',
    'Dog', 'Monkey', 'Mongoose', 'Monkey', 'Lion', 'Horse',
    'Lion', 'Cow', 'Elephant'
]

# Vashya by Rashi: 0: Chaturpada, 1: Manav, 2: Jalachara, 3: Vanachara, 4: Keeta
RAASHI_VASHYA = [
    'Chatuspada', 'Chatuspada', 'Manav', 'Jalachara', 'Vanachara', 'Manav',
    'Manav', 'Keeta', 'Manav', 'Chatuspada', 'Manav', 'Jalachara'
]

# Varna by Nakshatra: 0: Brahmin, 1: Kshatriya, 2: Vaishya, 3: Shudra
NAKSHATRA_VARNA = [
    'Shudra', 'Shudra', 'Brahmin', 'Vaishya', 'Vaishya', 'Shudra',
    'Vaishya', 'Brahmin', 'Shudra', 'Shudra', 'Vaishya', 'Vaishya',
    'Brahmin', 'Shudra', 'Vaishya', 'Shudra', 'Vaishya', 'Shudra',
    'Shudra', 'Vaishya', 'Vaishya', 'Brahmin', 'Shudra', 'Shudra',
    'Vaishya', 'Vaishya', 'Brahmin'
]

def get_tithi(moon_long: float, sun_long: float) -> Tuple[int, str]:
    diff = normalize_longitude(moon_long - sun_long)
    tithi = int(diff / 12) + 1
    if tithi > 30:
        tithi = 30
    return tithi, TITHI_NAMES[tithi - 1]


def get_yoga(moon_long: float, sun_long: float) -> Tuple[int, str]:
    sum_long = normalize_longitude(moon_long + sun_long)
    index = int(sum_long / (360 / 27))
    return index + 1, YOGA_NAMES[index % len(YOGA_NAMES)]


def get_karana(moon_long: float, sun_long: float) -> str:
    diff = normalize_longitude(moon_long - sun_long)
    half_tithi = int(diff / 6) + 1
    if half_tithi <= 7:
        return KARANA_NAMES[half_tithi - 1]
    return KARANA_NAMES[7 + ((half_tithi - 8) % 4)]


def get_avakahada_chakra(planets, ascendant, birth_datetime):
    sun = planets['sun']
    moon = planets['moon']
    moon_nakshatra_idx, moon_pada = longitude_to_nakshatra(moon['longitude'])
    tithi_num, tithi_name = get_tithi(moon['longitude'], sun['longitude'])
    yoga_num, yoga_name = get_yoga(moon['longitude'], sun['longitude'])
    karana_name = get_karana(moon['longitude'], sun['longitude'])

    return {
        'varna': NAKSHATRA_VARNA[moon_nakshatra_idx],
        'vashya': RAASHI_VASHYA[moon['raashi']],
        'tithi': tithi_name,
        'nakshatra': NAKSHATRA_NAMES_NE[moon_nakshatra_idx],
        'pada': moon_pada,
        'yoga': yoga_name,
        'karana': karana_name,
        'gan': NAKSHATRA_GANA[moon_nakshatra_idx],
        'yoni': NAKSHATRA_YONI[moon_nakshatra_idx],
        'nadi': NAKSHATRA_NADI[moon_nakshatra_idx],
        'sign': moon['raashi_name'],
        'sign_lord': RAASHI_LORDS[moon['raashi']]
    }

def get_gem_recommendations(lagna_raashi: int, planets: Dict) -> Dict:
    raashi_lords = [6, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4] # Simplified
    planet_keys = ['sun', 'moon', 'mars', 'mercury', 'jupiter', 'venus', 'saturn']
    lagna_lord = planet_keys[raashi_lords[lagna_raashi] % 7]
    return {
        'lucky_gems': [PLANET_GEMS[lagna_lord]],
        'unlucky_gems': []
    }

def calculate_antardashas(mahadasha_lord_idx, start_time, mahadasha_years):
    antardashas = []
    current_start = start_time
    for i in range(9):
        idx = (mahadasha_lord_idx + i) % 9
        duration_days = (mahadasha_years * DASHA_YEARS[idx] / 120.0) * 365.25
        end_time = current_start + timedelta(days=duration_days)
        antardashas.append({
            "lord": DASHA_LORDS[idx],
            "lord_name": DASHA_LORDS_NEPALI[idx],
            "start_date": current_start.isoformat(),
            "end_date": end_time.isoformat()
        })
        current_start = end_time
    return antardashas

def calculate_vimshottari_dasha(moon_nakshatra_idx, moon_pada, birth_dt, moon_deg_in_nakshatra):
    dasha_start_idx = moon_nakshatra_idx % 9
    nakshatra_span = 360 / 27
    elapsed_in_nakshatra = moon_deg_in_nakshatra / nakshatra_span
    remaining_years = DASHA_YEARS[dasha_start_idx] * (1 - elapsed_in_nakshatra)
    
    all_dashas = []
    current_time = datetime.now(birth_dt.tzinfo)
    
    # First Mahadasha
    first_end = birth_dt + timedelta(days=remaining_years * 365.25)
    all_dashas.append({
        "lord": DASHA_LORDS[dasha_start_idx],
        "lord_name": DASHA_LORDS_NEPALI[dasha_start_idx],
        "start_date": birth_dt.isoformat(),
        "end_date": first_end.isoformat(),
        "antardashas": calculate_antardashas(dasha_start_idx, birth_dt, DASHA_YEARS[dasha_start_idx])
    })
    
    running_date = first_end
    current_idx = dasha_start_idx
    for _ in range(9):
        current_idx = (current_idx + 1) % 9
        lord = DASHA_LORDS[current_idx]
        years = DASHA_YEARS[current_idx]
        end_date = running_date + timedelta(days=years * 365.25)
        all_dashas.append({
            "lord": lord,
            "lord_name": DASHA_LORDS_NEPALI[current_idx],
            "start_date": running_date.isoformat(),
            "end_date": end_date.isoformat(),
            "antardashas": calculate_antardashas(current_idx, running_date, years)
        })
        running_date = end_date
        
    current_mahadasha = None
    for d in all_dashas:
        if datetime.fromisoformat(d['start_date']) <= current_time <= datetime.fromisoformat(d['end_date']):
            current_mahadasha = d
            break
            
    return {
        "all_mahadashas": all_dashas,
        "current_mahadasha": current_mahadasha or all_dashas[0]
    }

def calculate_kundali(birth_datetime: datetime, lat: float, lon: float, tz_str: str = "Asia/Kathmandu") -> Dict:
    tz = pytz.timezone(tz_str)
    if birth_datetime.tzinfo is None:
        birth_datetime = tz.localize(birth_datetime)
    birth_utc = birth_datetime.astimezone(pytz.utc)
    jd = julian_day_from_datetime(birth_utc)
    swe.set_topo(lon, lat, 0)
    ayanamsa = swe.get_ayanamsa_ut(jd)

    asc_deg = get_ascendant(jd, lat, lon)
    asc_raashi, asc_deg_in_raashi = longitude_to_raashi(asc_deg)
    house_cusps = get_house_cusps(jd, lat, lon)
    
    planets = {}
    for name, p_id in PLANETS.items():
        if name == 'ketu':
            node_lon, node_lat, node_speed = get_true_node_position(jd)
            lon_p = normalize_longitude(node_lon + 180.0)
            lat_p = -node_lat
            speed = node_speed
        elif name == 'rahu':
            lon_p, lat_p, speed = get_true_node_position(jd)
        else:
            lon_p, lat_p, speed = get_planet_position(jd, p_id)

        r_idx, deg_in_r = longitude_to_raashi(lon_p)
        n_idx, pada = longitude_to_nakshatra(lon_p)
        
        planets[name] = {
            'longitude': lon_p,
            'raashi': r_idx,
            'raashi_name': RAASHI_NAMES[r_idx],
            'raashi_name_en': RAASHI_NAMES_EN[r_idx],
            'degrees_in_raashi': deg_in_r,
            'dms': decimal_to_dms(deg_in_r),
            'nakshatra_name': NAKSHATRA_NAMES_NE[n_idx],
            'pada': pada,
            'is_vakri': speed < 0
        }

    planet_houses = {}
    for p_name, p_data in planets.items():
        p_lon = p_data['longitude']
        house = 1
        for i in range(12):
            c_start = house_cusps[i]
            c_end = house_cusps[(i+1)%12]
            if i == 11:
                if p_lon >= c_start or p_lon < c_end: break
            elif c_start <= p_lon < c_end: break
            house += 1
        planet_houses[p_name] = house

    nav_planets = {}
    for p_name, p_data in planets.items():
        nav_r = longitude_to_navamsha(p_data['longitude'])
        nav_planets[p_name] = {'raashi': nav_r, 'raashi_name': RAASHI_NAMES[nav_r]}
    
    nav_asc_r = longitude_to_navamsha(asc_deg)
    navamsha_data = {
        'planets': nav_planets,
        'ascendant': {'raashi': nav_asc_r, 'raashi_name': RAASHI_NAMES[nav_asc_r]}
    }
    
    gems = get_gem_recommendations(asc_raashi, planets)
    moon_nakshatra_idx, moon_pada = longitude_to_nakshatra(planets['moon']['longitude'])
    dasha_data = calculate_vimshottari_dasha(
        moon_nakshatra_idx,
        moon_pada,
        birth_datetime,
        planets['moon']['longitude'] % (360 / 27)
    )
    avakahada = get_avakahada_chakra(planets, asc_deg, birth_datetime)

    return {
        'birth_details': {
            'datetime': birth_datetime.isoformat(),
            'latitude': lat,
            'longitude': lon,
            'timezone': tz_str,
            'ayanamsa_degrees': ayanamsa,
            'sidereal_mode': 'Lahiri'
        },
        'ascendant': {
            'raashi': asc_raashi,
            'raashi_name': RAASHI_NAMES[asc_raashi], 
            'degrees_in_raashi': asc_deg_in_raashi,
            'dms': decimal_to_dms(asc_deg_in_raashi)
        },
        'planets': planets,
        'planet_houses': planet_houses,
        'navamsha': navamsha_data,
        'gems': gems,
        'current_dasha': dasha_data,
        'avakahada': avakahada,
        'houses': [{'number': i+1, 'cusp_longitude': house_cusps[i], 'raashi': longitude_to_raashi(house_cusps[i])[0]} for i in range(12)]
    }