import svgwrite
import os
from typing import Dict, List, Tuple

# Nepali abbreviations for planets
PLANET_ABBR_NEPALI = {
    'sun': 'सू', 'moon': 'च', 'mars': 'मं', 'mercury': 'बु',
    'jupiter': 'गु', 'venus': 'शु', 'saturn': 'श',
    'rahu': 'रा', 'ketu': 'के'
}

# Hamro Patro style colors
COLORS = {
    'bg': '#000000',
    'line': '#e67e22', # Bold Orange
    'text_planet': '#ffffff',
    'text_sign': '#ffffff',
    'text_vakri': '#f1c40f' # Yellow for retrograde
}

def generate_kundali_chart(data: Dict, output_path: str, is_navamsha: bool = False):
    """Generate North Indian Diamond Chart (Hamro Patro style)"""
    dwg = svgwrite.Drawing(output_path, size=(500, 500), profile='full')
    
    # Background
    dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), fill=COLORS['bg']))
    
    # Outer frame
    dwg.add(dwg.rect(insert=(10, 10), size=(480, 480), fill='none', stroke=COLORS['line'], stroke_width=4))
    
    # Diamond lines
    dwg.add(dwg.line(start=(10, 10), end=(490, 490), stroke=COLORS['line'], stroke_width=2))
    dwg.add(dwg.line(start=(10, 490), end=(490, 10), stroke=COLORS['line'], stroke_width=2))
    dwg.add(dwg.line(start=(10, 250), end=(250, 10), stroke=COLORS['line'], stroke_width=2))
    dwg.add(dwg.line(start=(250, 10), end=(490, 250), stroke=COLORS['line'], stroke_width=2))
    dwg.add(dwg.line(start=(490, 250), end=(250, 490), stroke=COLORS['line'], stroke_width=2))
    dwg.add(dwg.line(start=(250, 490), end=(10, 250), stroke=COLORS['line'], stroke_width=2))

    # Center coordinates for each house (North Indian style)
    # 1st house is top-middle diamond
    house_centers = [
        (250, 125), (140, 60),  (60, 140), (125, 250),
        (60, 360),  (140, 440), (250, 375), (360, 440),
        (440, 360), (375, 250), (440, 140), (360, 60)
    ]
    
    # Sign positions (small numbers in each house)
    sign_positions = [
        (250, 230), (350, 130), (230, 25), (130, 130),
        (25, 230),  (130, 350), (250, 470), (370, 350),
        (475, 230), (370, 120), (250, 25), (130, 120) 
    ]
    # Actually, North Indian sign mapping is:
    # 1st house (center top diamond) gets the lagna raashi number
    
    if is_navamsha:
        planets_data = data['navamsha']['planets']
        start_raashi = data['navamsha']['ascendant']['raashi'] + 1
    else:
        planets_data = data['planets']
        start_raashi = data['ascendant']['raashi'] + 1
    
    # House planet mapping
    house_planets = {i+1: [] for i in range(12)}
    for p_name, p_info in planets_data.items():
        if is_navamsha:
            # Navamsha house is different from Janma house
            # We need to calculate it: (Nav_Planet_Raashi - Nav_Asc_Raashi + 1) % 12
            nav_p_r = p_info['raashi']
            nav_a_r = data['navamsha']['ascendant']['raashi']
            h = (nav_p_r - nav_a_r + 12) % 12 + 1
        else:
            h = data['planet_houses'][p_name]
        
        # Add labels with Nepali abbreviations
        label = PLANET_ABBR_NEPALI[p_name]
        if not is_navamsha and p_info.get('is_vakri'):
            label += '(व)'
        house_planets[h].append(label)

    # Render Sign Numbers
    for i in range(12):
        sign_num = (start_raashi + i - 1) % 12 + 1
        # Positions for sign numbers
        sx, sy = 250, 250
        if i == 0: sx, sy = 250, 230 # 1
        elif i == 1: sx, sy = 180, 170 # 2
        elif i == 2: sx, sy = 170, 110 # 3
        elif i == 3: sx, sy = 120, 230 # 4
        elif i == 4: sx, sy = 110, 330 # 5
        elif i == 5: sx, sy = 170, 390 # 6
        elif i == 6: sx, sy = 250, 270 # 7
        elif i == 7: sx, sy = 330, 390 # 8
        elif i == 8: sx, sy = 390, 330 # 9
        elif i == 9: sx, sy = 380, 230 # 10
        elif i == 10: sx, sy = 390, 110 # 11
        elif i == 11: sx, sy = 330, 170 # 12
        
        dwg.add(dwg.text(str(sign_num), insert=(sx, sy), fill=COLORS['text_sign'], 
                         font_size="20px", font_weight="bold", text_anchor="middle"))

    # Render Planets in each house
    for h, p_list in house_planets.items():
        cx, cy = 0, 0
        if h == 1: cx, cy = 250, 120 # 1
        elif h == 2: cx, cy = 180, 60 # 2
        elif h == 3: cx, cy = 80, 60 # 3
        elif h == 4: cx, cy = 120, 180 # 4
        elif h == 5: cx, cy = 80, 280 # 5
        elif h == 6: cx, cy = 180, 440 # 6
        elif h == 7: cx, cy = 250, 380 # 7
        elif h == 8: cx, cy = 340, 440 # 8
        elif h == 9: cx, cy = 420, 350 # 9
        elif h == 10: cx, cy = 350, 250 # 10
        elif h == 11: cx, cy = 420, 150 # 11
        elif h == 12: cx, cy = 340, 60 # 12

        # Group planets in the house
        for idx, p_label in enumerate(p_list):
            offset_y = idx * 22
            dwg.add(dwg.text(p_label, insert=(cx, cy + offset_y), fill=COLORS['text_planet'], 
                             font_size="22px", font_weight="600", text_anchor="middle"))

    dwg.save()

def generate_kundali_text_report(data: Dict) -> str:
    """Fallback text report"""
    return "Refined Hamro Patro style report"