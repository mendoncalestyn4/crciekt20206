"""Cricket Captain 2026's team and competition names.

The game lets you rename every competition and team, in two text files in its
folder (editcompnames.txt and editteamnames.txt)::

    England : 20 Over Trophy,T20 Blast,Blast          country : the game's name, new name, short name
    Mumbai,Mumbai Indians,MI                          the game's name, new name, short name

The scorecards print the new name.  The lists below are the names from those
files: every competition with the country it belongs to, and every team with
its country, under both names, so a scorecard is understood whichever name it
uses.  The same reader is used for the files themselves when the site finds
them next to the Scorecards folder, so a later rename is understood too.
"""

from __future__ import annotations

import re
from pathlib import Path

COMP_FILE, TEAM_FILE = "editcompnames.txt", "editteamnames.txt"


def parse_comp_file(text: str) -> list[tuple[str, str, str]]:
    """(country, the game's name, the name scorecards print) for each line of editcompnames.txt."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        country, rest = line.split(":", 1)
        bits = [b.strip() for b in rest.split(",")]
        if not bits[0]:
            continue
        out.append((country.strip(), bits[0], bits[1] if len(bits) > 1 and bits[1] else bits[0]))
    return out


def parse_team_file(text: str) -> list[tuple[str, str, str]]:
    """(country, the game's name, the name scorecards print) for each team in editteamnames.txt; national sides
    have the country "International"."""
    out, country = [], ""
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            m = re.match(r"\s*#\s*===\s*(.+?)\s*===", line)
            if m:
                country = m.group(1)
            continue
        if not line.strip() or line.strip().startswith("["):
            continue
        bits = [b.strip() for b in line.split(",")]
        if bits[0]:
            out.append((country, bits[0], bits[1] if len(bits) > 1 and bits[1] else bits[0]))
    return out


def find_edit_files(scorecards: Path | str | None, also: tuple = ()) -> dict[str, Path]:
    """The game's two name files, looked for in the game's folder (the Scorecards folder's parent), the
    Scorecards folder itself, then the folders in `also` (where the game is installed).  {"comp": path,
    "team": path} for those found."""
    found: dict[str, Path] = {}
    dirs = [Path(scorecards).parent, Path(scorecards)] if scorecards else []
    for d in dirs + [Path(a) for a in also]:
        for key, name in (("comp", COMP_FILE), ("team", TEAM_FILE)):
            p = d / name
            try:
                if key not in found and p.is_file():
                    found[key] = p
            except OSError:  # a folder that can't be looked in (no permission, a drive that's gone)
                pass
    return found


# --------------------------------------------------------------------------- #
# The names in the game's files (Cricket Captain 2026 with real names)
# --------------------------------------------------------------------------- #
# (country, the game's name, the name scorecards print)
COMPETITIONS: list[tuple[str, str, str]] = [
    ('England', 'English FC League', 'County Championship'),
    ('England', 'Challenge Trophy', 'Metro Bank One Day Cup'),
    ('England', '20 Over Trophy', 'T20 Blast'),
    ('England', '100 Ball Trophy', 'The Hundred'),
    ('Australia', 'Australian League', 'Sheffield Shield'),
    ('Australia', 'One Day Cup', 'Marsh One-Day Cup'),
    ('Australia', '20 Over Trophy', 'Big Bash League'),
    ('India', 'FC League', 'Ranji Trophy'),
    ('India', 'One Day Cup', 'Vijay Hazare Trophy'),
    ('India', 'Domestic 20 Over', 'Syed Mushtaq Ali Trophy'),
    ('India', '20 Over League', 'Indian Premier League'),
    ('New Zealand', 'FC League', 'Plunket Shield'),
    ('New Zealand', 'One Day Cup', 'Ford Trophy'),
    ('New Zealand', '20 Over Trophy', 'Super Smash'),
    ('South Africa', 'FC League', 'CSA 4-Day Series'),
    ('South Africa', 'One Day Cup', 'CSA One-Day Cup'),
    ('South Africa', 'Domestic 20 Over', 'CSA T20 Challenge'),
    ('South Africa', 'Provincial 20 Over', 'CSA T20 Knock-Out'),
    ('South Africa', '20 Over Trophy', 'SA20'),
    ('West Indies', '4 Day Competition', 'West Indies Championship'),
    ('West Indies', '50 Over', 'Super50 Cup'),
    ('West Indies', '20 Over Trophy', 'Caribbean Premier League'),
    ('Pakistan', 'FC League', 'Quaid-e-Azam Trophy'),
    ('Pakistan', 'Dept Cup', "President's Trophy"),
    ('Pakistan', 'One Day Cup', 'Pakistan Cup'),
    ('Pakistan', '20 Over Trophy', 'National T20 Cup'),
    ('Pakistan', 'Super Cup', 'Pakistan Super League'),
    ('Bangladesh', 'FC League', 'National Cricket League'),
    ('Bangladesh', 'One Day Cup', 'Dhaka Premier Division Cricket League'),
    ('Bangladesh', 'Domestic 20 Over', 'NCL T20'),
    ('Bangladesh', '20 Over Trophy', 'Bangladesh Premier League'),
    ('Afghanistan', 'FC League', 'Ahmad Shah Abdali First Class Tournament'),
    ('Afghanistan', 'One Day Cup', 'Ghazi Amanullah Khan Regional One Day To'),
    ('Afghanistan', 'Domestic 20 Over', 'National T20 Cup'),
    ('Afghanistan', '20 Over Trophy', 'Shpageeza Cricket League'),
    ('Ireland', 'FC League', 'Inter-Provincial Championship'),
    ('Ireland', 'One Day Cup', 'Inter-Provincial Cup'),
    ('Ireland', 'Domestic 20 Over', 'Inter-Provincial Trophy'),
    ('Sri Lanka', 'FC League', 'Major League Tournament'),
    ('Sri Lanka', 'One Day Cup', 'Major Clubs Limited Over Tournament'),
    ('Sri Lanka', 'Domestic 20 Over', 'Major Clubs T20 Tournament'),
    ('Sri Lanka', '20 Over Trophy', 'Lanka Premier League'),
    ('Zimbabwe', 'FC League', 'Logan Cup'),
    ('Zimbabwe', 'One Day Cup', 'Pro50 Championship'),
    ('Zimbabwe', 'Domestic 20 Over', 'Domestic T20 Competition'),
]

# (country, the game's name, the name scorecards print); national sides are "International"
TEAMS: list[tuple[str, str, str]] = [
    ('International', 'Afghanistan', 'Afghanistan'),
    ('International', 'Australia', 'Australia'),
    ('International', 'Bangladesh', 'Bangladesh'),
    ('International', 'Canada', 'Canada'),
    ('International', 'Denmark', 'Denmark'),
    ('International', 'England', 'England'),
    ('International', 'Hong Kong', 'Hong Kong'),
    ('International', 'India', 'India'),
    ('International', 'Ireland', 'Ireland'),
    ('International', 'Italy', 'Italy'),
    ('International', 'Kenya', 'Kenya'),
    ('International', 'Nepal', 'Nepal'),
    ('International', 'Netherlands', 'Netherlands'),
    ('International', 'New Zealand', 'New Zealand'),
    ('International', 'Oman', 'Oman'),
    ('International', 'Pakistan', 'Pakistan'),
    ('International', 'Scotland', 'Scotland'),
    ('International', 'South Africa', 'South Africa'),
    ('International', 'Sri Lanka', 'Sri Lanka'),
    ('International', 'UAE', 'UAE'),
    ('International', 'USA', 'USA'),
    ('International', 'Uganda', 'Uganda'),
    ('International', 'West Indies', 'West Indies'),
    ('International', 'Zimbabwe', 'Zimbabwe'),
    ('International', 'Bermuda', 'Bermuda'),
    ('International', 'Malaysia', 'Malaysia'),
    ('International', 'Namibia', 'Namibia'),
    ('International', 'Nigeria', 'Nigeria'),
    ('International', 'Papua New Guinea', 'Papua New Guinea'),
    ('International', 'Saudi Arabia', 'Saudi Arabia'),
    ('International', 'Singapore', 'Singapore'),
    ('International', 'World XI A', 'World XI A'),
    ('International', 'World XI B', 'World XI B'),
    ('Australia', 'Adelaide', 'Adelaide Strikers'),
    ('Australia', 'Brisbane', 'Brisbane Heat'),
    ('Australia', 'Hobart', 'Hobart Hurricanes'),
    ('Australia', 'Melbourne Green', 'Melbourne Stars'),
    ('Australia', 'Melbourne Red', 'Melbourne Renegades'),
    ('Australia', 'Perth', 'Perth Scorchers'),
    ('Australia', 'Sydney Green', 'Sydney Thunder'),
    ('Australia', 'Sydney Pink', 'Sydney Sixers'),
    ('Australia', 'Cricket Australia XI', 'Cricket Australia XI'),
    ('Australia', "Australian Chairman's XI", "Australian Chairman's XI"),
    ('Australia', "Prime Minister's XI", "Prime Minister's XI"),
    ('Australia', 'New South Wales', 'New South Wales'),
    ('Australia', 'Queensland', 'Queensland'),
    ('Australia', 'South Australia', 'South Australia'),
    ('Australia', 'Tasmania', 'Tasmania'),
    ('Australia', 'Victoria', 'Victoria'),
    ('Australia', 'Western Australia', 'Western Australia'),
    ('South Africa', 'Boland', 'Boland'),
    ('South Africa', 'Border', 'Border'),
    ('South Africa', 'Eastern Province', 'Eastern Cape Iinyathi'),
    ('South Africa', 'Easterns', 'Eastern Storm'),
    ('South Africa', 'Free State', 'Knights'),
    ('South Africa', 'Gauteng', 'Lions'),
    ('South Africa', 'KZulu-Natal Coastal', 'Dolphins'),
    ('South Africa', 'KZulu-Natal Inland', 'Tuskers'),
    ('South Africa', 'Limpopo', 'Limpopo Impalas'),
    ('South Africa', 'Mpumalanga', 'Mpumalanga Rhinos'),
    ('South Africa', 'North West', 'North West Dragons'),
    ('South Africa', 'Northern Cape', 'Northern Cape Heat'),
    ('South Africa', 'Northerns', 'Titans'),
    ('South Africa', 'SW Districts', 'Garden Route Badgers'),
    ('South Africa', 'Western Province', 'Western Province'),
    ('South Africa', 'SA Under-19s', 'SA Under-19s'),
    ('South Africa', 'Cape Town', 'MI Cape Town'),
    ('South Africa', 'Durban', "Durban's Super Giants"),
    ('South Africa', 'Eastern Cape', 'Sunrisers Eastern Cape'),
    ('South Africa', 'Johannesburg', 'Joburg Super Kings'),
    ('South Africa', 'Paarl', 'Paarl Royals'),
    ('South Africa', 'Pretoria', 'Pretoria Capitals'),
    ('India', 'Bangalore', 'Royal Challengers Bengaluru'),
    ('India', 'Chennai', 'Chennai Super Kings'),
    ('India', 'Delhi', 'Delhi Capitals'),
    ('India', 'Gujarat', 'Gujarat Titans'),
    ('India', 'Hyderabad', 'Sunrisers Hyderabad'),
    ('India', 'Kolkata', 'Kolkata Knight Riders'),
    ('India', 'Lucknow', 'Lucknow Super Giants'),
    ('India', 'Mumbai', 'Mumbai Indians'),
    ('India', 'Punjab', 'Punjab Kings'),
    ('India', 'Rajasthan', 'Rajasthan Royals'),
    ('India', 'Andhra', 'Andhra'),
    ('India', 'Arunachal Pradesh', 'Arunachal Pradesh'),
    ('India', 'Assam', 'Assam'),
    ('India', 'Baroda', 'Baroda'),
    ('India', 'Bengal', 'Bengal'),
    ('India', 'Bihar', 'Bihar'),
    ('India', 'Chandigarh', 'Chandigarh'),
    ('India', 'Chhattisgarh', 'Chhattisgarh'),
    ('India', 'Delhi CC', 'Delhi'),
    ('India', 'Goa', 'Goa'),
    ('India', 'Gujarat CC', 'Gujarat'),
    ('India', 'Haryana', 'Haryana'),
    ('India', 'Himachal Pradesh', 'Himachal Pradesh'),
    ('India', 'Hyderabad CC', 'Hyderabad'),
    ('India', 'Jammu and Kashmir', 'Jammu and Kashmir'),
    ('India', 'Jharkhand', 'Jharkhand'),
    ('India', 'Karnataka', 'Karnataka'),
    ('India', 'Kerala CC', 'Kerala'),
    ('India', 'Madhya Pradesh', 'Madhya Pradesh'),
    ('India', 'Maharashtra', 'Maharashtra'),
    ('India', 'Manipur', 'Manipur'),
    ('India', 'Meghalaya', 'Meghalaya'),
    ('India', 'Mizoram', 'Mizoram'),
    ('India', 'Mumbai CC', 'Mumbai'),
    ('India', 'Nagaland', 'Nagaland'),
    ('India', 'Odisha', 'Odisha'),
    ('India', 'Puducherry', 'Puducherry'),
    ('India', 'Punjab CC', 'Punjab'),
    ('India', 'Railways', 'Railways'),
    ('India', 'Rajasthan CC', 'Rajasthan'),
    ('India', 'Saurashtra', 'Saurashtra'),
    ('India', 'Services', 'Services'),
    ('India', 'Sikkim', 'Sikkim'),
    ('India', 'Tamil Nadu', 'Tamil Nadu'),
    ('India', 'Tripura', 'Tripura'),
    ('India', 'Uttar Pradesh', 'Uttar Pradesh'),
    ('India', 'Uttarakhand', 'Uttarakhand'),
    ('India', 'Vidarbha', 'Vidarbha'),
    ('Zimbabwe', 'Manicaland', 'Mountaineers'),
    ('Zimbabwe', 'Mashonaland', 'Mashonaland Eagles'),
    ('Zimbabwe', 'Masvingo', 'Southern Rocks'),
    ('Zimbabwe', 'Matabeleland', 'Matabeleland Tuskers'),
    ('Zimbabwe', 'Midlands', 'Mid West Rhinos'),
    ('New Zealand', 'Auckland', 'Auckland Aces'),
    ('New Zealand', 'Canterbury', 'Canterbury Kings'),
    ('New Zealand', 'Central Districts', 'Central Stags'),
    ('New Zealand', 'Northern Districts', 'Northern Brave'),
    ('New Zealand', 'Otago', 'Otago Volts'),
    ('New Zealand', 'Wellington', 'Wellington Firebirds'),
    ('Pakistan', 'Hyderabad PL', 'Hyderabad Kingsmen'),
    ('Pakistan', 'Islamabad', 'Islamabad United'),
    ('Pakistan', 'Karachi', 'Karachi Kings'),
    ('Pakistan', 'Lahore', 'Lahore Qalandars'),
    ('Pakistan', 'Multan', 'Multan Sultans'),
    ('Pakistan', 'Peshawar', 'Peshawar Zalmi'),
    ('Pakistan', 'Quetta', 'Quetta Gladiators'),
    ('Pakistan', 'Rawalpindi', 'Rawalpindiz'),
    ('Pakistan', 'Abbottabad', 'Abbottabad Region'),
    ('Pakistan', 'Bahawalpur', 'Bahawalpur Region'),
    ('Pakistan', 'Faisalabad', 'Faisalabad Region'),
    ('Pakistan', 'Islamabad CC', 'Islamabad Region'),
    ('Pakistan', 'Karachi Blues', 'Karachi Region Blues'),
    ('Pakistan', 'Lahore Whites', 'Lahore Region Whites'),
    ('Pakistan', 'Multan CC', 'Multan Region'),
    ('Pakistan', 'Peshawar CC', 'Peshawar Region'),
    ('Pakistan', 'Sialkot CC', 'Sialkot Region'),
    ('Pakistan', 'Tribal Areas', 'FATA Region'),
    ('Sri Lanka', 'Colombo', 'Colombo Strikers'),
    ('Sri Lanka', 'Dambulla', 'Dambulla Sixers'),
    ('Sri Lanka', 'Galle', 'Galle Marvels'),
    ('Sri Lanka', 'Jaffna', 'Jaffna Kings'),
    ('Sri Lanka', 'Kandy', 'Kandy Falcons'),
    ('Sri Lanka', 'Ace Capital CC', 'Ace Capital'),
    ('Sri Lanka', 'Badureliya', 'Badureliya Sports Club'),
    ('Sri Lanka', 'Bloomfield', 'Bloomfield Cricket and Athletic Club'),
    ('Sri Lanka', 'Burgher', 'Burgher Recreation Club'),
    ('Sri Lanka', 'Chilaw Marians', 'Chilaw Marians'),
    ('Sri Lanka', 'Colombo CC', 'Colombo'),
    ('Sri Lanka', 'Colts', 'Colts'),
    ('Sri Lanka', 'Kurunegala Youth', 'Kurunegala Youth'),
    ('Sri Lanka', 'Moors', 'Moors Sports Club'),
    ('Sri Lanka', 'Nondescripts', 'Nondescripts'),
    ('Sri Lanka', 'Nugegoda SWC', 'Nugegoda Sports Welfare Club'),
    ('Sri Lanka', 'Panadura', 'Panadura Sports Club'),
    ('Sri Lanka', 'Police', 'Police Sports Club'),
    ('Sri Lanka', 'Tamil Union', 'Tamil Union Cricket and Athletic Club'),
    ('Sri Lanka', 'Sinhalese', 'Sinhalese Sports Club'),
    ('West Indies', 'Antigua and Barbuda', 'Antigua and Barbuda Falcons'),
    ('West Indies', 'Barbados', 'Barbados Royals'),
    ('West Indies', 'Guyana', 'Guyana Amazon Warriors'),
    ('West Indies', 'Jamaica', 'Jamaica Kingsmen'),
    ('West Indies', 'Leeward Islands', 'St Kitts and Nevis Patriots'),
    ('West Indies', 'Trinidad and Tobago', 'Trinbago Knight Riders'),
    ('West Indies', 'Windward Islands', 'Saint Lucia Kings'),
    ('West Indies', 'Barbados CC', 'Barbados Pride'),
    ('West Indies', 'Campuses & Colleges', 'Combined Campuses and Colleges'),
    ('West Indies', 'Guyana CC', 'Guyana Harpy Eagles'),
    ('West Indies', 'Jamaica CC', 'Jamaica Scorpions'),
    ('West Indies', 'Leeward Islands CC', 'Leeward Islands Hurricanes'),
    ('West Indies', 'Trinidad & Tobago CC', 'Trinidad and Tobago Red Force'),
    ('West Indies', 'Windward Islands CC', 'Windward Islands Volcanoes'),
    ('West Indies', 'West Indies Academy', 'West Indies Academy'),
    ('England', 'Derbyshire', 'Derbyshire'),
    ('England', 'Durham', 'Durham'),
    ('England', 'Essex', 'Essex'),
    ('England', 'Glamorgan', 'Glamorgan'),
    ('England', 'Gloucestershire', 'Gloucestershire'),
    ('England', 'Hampshire', 'Hampshire'),
    ('England', 'Kent', 'Kent'),
    ('England', 'Lancashire', 'Lancashire'),
    ('England', 'Leicestershire', 'Leicestershire'),
    ('England', 'Middlesex', 'Middlesex'),
    ('England', 'Northamptonshire', 'Northamptonshire'),
    ('England', 'Nottinghamshire', 'Nottinghamshire'),
    ('England', 'Somerset', 'Somerset'),
    ('England', 'Surrey', 'Surrey'),
    ('England', 'Sussex', 'Sussex'),
    ('England', 'Warwickshire', 'Warwickshire'),
    ('England', 'Worcestershire', 'Worcestershire'),
    ('England', 'Yorkshire', 'Yorkshire'),
    ('England', 'Birmingham', 'Birmingham Phoenix'),
    ('England', 'Cardiff', 'Welsh Fire'),
    ('England', 'Leeds', 'SunRisers Leeds'),
    ('England', 'London Blue', 'London Spirit'),
    ('England', 'London Green', 'MI London'),
    ('England', 'Manchester', 'Manchester Super Giants'),
    ('England', 'Nottingham', 'Trent Rockets'),
    ('England', 'Southampton', 'Southern Brave'),
    ('Bangladesh', 'Chittagong', 'Chattogram Royals'),
    ('Bangladesh', 'Dhaka', 'Dhaka Capitals'),
    ('Bangladesh', 'Noakhali', 'Noakhali Express'),
    ('Bangladesh', 'Rajshahi', 'Rajshahi Warriors'),
    ('Bangladesh', 'Rangpur', 'Rangpur Riders'),
    ('Bangladesh', 'Sylhet', 'Sylhet Titans'),
    ('Bangladesh', 'Barisal CC', 'Barishal Division'),
    ('Bangladesh', 'Chattogram CC', 'Chittagong Division'),
    ('Bangladesh', 'Dhaka CC', 'Dhaka Division'),
    ('Bangladesh', 'Khulna CC', 'Khulna Division'),
    ('Bangladesh', 'Mymensingh CC', 'Mymensingh Division'),
    ('Bangladesh', 'Rajshahi CC', 'Rajshahi Division'),
    ('Bangladesh', 'Rangpur CC', 'Rangpur Division'),
    ('Bangladesh', 'Sylhet CC', 'Sylhet Division'),
    ('Ireland', 'Leinster', 'Leinster Lightning'),
    ('Ireland', 'Munster', 'Munster Reds'),
    ('Ireland', 'North West (IRE)', 'North West Warriors'),
    ('Ireland', 'Northern CU', 'Northern Knights'),
    ('Afghanistan', 'Herat', 'Herat'),
    ('Afghanistan', 'Jalalabad', 'Nangarhar Leopards'),
    ('Afghanistan', 'Kabul', 'Kabul Zwanan'),
    ('Afghanistan', 'Kandahar', 'Kandahar Knights'),
    ('Afghanistan', 'Mazar-i-Sharif', 'Balkh Legends'),
    ('Afghanistan', 'Hindukush', 'Hindukush Strikers'),
    ('Afghanistan', 'Mah-e-Par', 'Mahipar Stars'),
    ('Afghanistan', 'Maiwand', 'Maiwand Champions'),
    ('Afghanistan', 'Pamir', 'Pamir Legends'),
]
