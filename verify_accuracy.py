from kundali_calculator import calculate_kundali
from datetime import datetime
import pytz

def verify():
    # Test for 2026-04-19 18:44 Kathmandu
    # Today, Sun is in Aries (Sign 0).
    # If Ascendant is Cancer (Sign 3), Aries should be in House 10.
    dt = datetime(2026, 4, 19, 18, 44)
    res = calculate_kundali(dt, 27.7172, 85.3240)
    
    sun_raashi = res['planets']['sun']['raashi']
    sun_house = res['planet_houses']['sun']
    asc_raashi = res['ascendant']['raashi']
    
    print(f"Results for {dt}:")
    print(f"Ascendant Sign: {asc_raashi}")
    print(f"Sun Sign: {sun_raashi}")
    print(f"Sun House: {sun_house}")
    
    # Expected: (0 - 3 + 12) % 12 + 1 = 10
    expected_house = (sun_raashi - asc_raashi + 12) % 12 + 1
    if sun_house == expected_house:
        print("SUCCESS: Sun is in the correct house according to Whole Sign logic.")
    else:
        print(f"FAILURE: Expected house {expected_house}, got {sun_house}")

if __name__ == "__main__":
    verify()
