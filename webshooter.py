#!/usr/bin/python3

import json
import time
import subprocess
import argparse
import re
import configparser
import os
import sys
import math
import unicodedata
import time

MODES = ["starttimes", "ical", "results", "signups", "medals", "starts", "list"]

CURL_URL_COMP = "https://webshooter.se/api/v4.1.9/competitions?page=1&per_page=1000&status=all&type=0"
CURL_URL_BASE = "https://webshooter.se/api/v4.1.9/competitions/{competition}"
CURL_URL_PAGE = "https://webshooter.se/api/v4.1.9/competitions/{competition}/{page}"
CURL_OPTIONS = ("-H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:97.0) Gecko/20100101 Firefox/97.0' " +
                "-H 'Accept: application/json, text/plain, */*' -H 'Accept-Language: en-US,en;q=0.5' " +
                "-H 'Accept-Encoding: gzip, deflate, br' " +
                "-H 'X-Requested-With: XMLHttpRequest' " +
                "-H 'DNT: 1' " +
                "-H 'Authorization: Bearer {token}' " +
                "-H 'Connection: keep-alive' " +
                "-H 'Sec-Fetch-Dest: empty' " +
                "-H 'Sec-Fetch-Mode: cors' " +
                "-H 'Sec-Fetch-Site: same-origin'")

parser = argparse.ArgumentParser(description = "Webshooter start times", formatter_class = argparse.RawTextHelpFormatter)
parser.add_argument('value', help = "Competition ID or year", nargs = '?')
parser.add_argument('--token', help = "Token, copy from Firefox: Web Developer Tools -> Storage -> Local Storage -> token")
parser.add_argument('--name', help = "Name")
parser.add_argument('--club', help = "Club, use 'None' to unset")
parser.add_argument('--card', help = "Card, use 'None' to unset")
help = "Mode\n  Available modes: "
for mode in MODES:
  help += f"\n    {mode}"
  match mode:
    case 'starttimes':
      help += "\n      List start times for a competition, requires webshooter id as <value>"
    case 'ical':
      help += "\n      List start times for a competition (in ical format), requires webshooter id as <value>"
    case 'results':
      help += "\n      List results from a competition, requires webshooter id as <value>"
    case 'signups':
      help += "\n      List sign up for a competition, requires webshooter id as <value>"
    case 'medals':
      help += "\n      List standard medals awarded for a card id, optional year as <value>"
    case 'starts':
      help += "\n      List total starts from a club, optional year as <value>"
    case 'list':
      help += "\n      List all competitions in webshooter, optinal year as <value>"
parser.add_argument('--mode', help = help, required = True)
parser.add_argument('-v', '--verbose', help = "Verbose", required = False, action = 'store_true', default = False)
parser.add_argument('-d', '--debug', help = "Debug", required = False, action = 'store_true', default = False)

args = parser.parse_args().__dict__

configfile = f"{os.path.expanduser('~')}/.webshooter.rc"
if os.path.exists(configfile):
  config = configparser.ConfigParser()
  config.read_file(open(configfile))

  if args['club'] == None:
    try:
      args['club'] = config.get('global', 'club')
    except configparser.NoOptionError:
      args['club'] = None

  if args['card'] == None:
    try:
      args['card'] = config.get('global', 'card')
    except configparser.NoOptionError:
      args['card'] = None

  if args['token'] == None:
    args['token'] = config.get('global', 'token')

elif args['token'] == None:
  parser.print_help(sys.stderr)
  print("", file=sys.stderr)
  print(f"Token not specified and config file {configfile} not found", file=sys.stderr)
  print("Use --token or create config file", file=sys.stderr)
  print("", file=sys.stderr)
  print("Example config file (all options are optional):", file=sys.stderr)
  print("", file=sys.stderr)
  print("[global]", file=sys.stderr)
  print("token = <token>", file=sys.stderr)
  print("club = xx-yyy", file=sys.stderr)
  print("unicode = [True|False]", file=sys.stderr)
  print("", file=sys.stderr)

  exit(1)

if args['club'] == "None":
  args['club'] = None

if args['card'] == "None":
  args['card'] = None

def printable(string):
  if config.has_option('global', 'unicode') and not config.getboolean('global', 'unicode'):
    string = unicodedata.normalize('NFKD', string)
    string = u"".join([c for c in string if not unicodedata.combining(c)])

  return string

def fetch_data(competition = None, page = None):
  if args['debug']:
    if competition == None:
      filename = f"testdata/webshooter_competitions.json"
    elif page == None:
      filename = f"testdata/webshooter_{competition}.json"
    else:
      filename = f"testdata/webshooter_{competition}_{page.split('?')[0]}.json"
    with open(filename) as f:
      print(f"Reading file {filename}")
      output = f.read()
  else:
    if competition == None:
      print(f"Fetching competitions")
      curl = f"curl -s -w '%{{{{stderr}}}}%{{{{http_code}}}}' '{CURL_URL_COMP}' {CURL_OPTIONS}"
    elif page == None:
      print(f"Fetching {competition}")
      curl = f"curl -s -w '%{{{{stderr}}}}%{{{{http_code}}}}' '{CURL_URL_BASE}' {CURL_OPTIONS}"
    else:
      print(f"Fetching {page.split('?')[0]}")
      curl = f"curl -s -w '%{{{{stderr}}}}%{{{{http_code}}}}' '{CURL_URL_PAGE}' {CURL_OPTIONS}"
    output = subprocess.run(curl.format(competition = competition, page = page, token = args['token']), shell = True, capture_output = True)
    httpcode = int(output.stderr.decode())
    if httpcode != 200:
      print(f"Failed to get data, error: '{httpcode}'", file=sys.stderr)
      exit(1)
    output = output.stdout.decode()

  return json.loads(output)

def get_info(competition):
  info = {}

  data = fetch_data(competition = competition)

  info['id'] = competition
  info['name'] = data['competitions']['name']
  info['city'] = data['competitions']['contact_city']
  info['venue'] = data['competitions']['contact_venue']
  info['date'] = data['competitions']['date']
  info['signups_close'] = data['competitions']['signups_closing_date']
  info['type'] = data['competitions']['results_type']

  return info

def type_to_string(infotype):
  if infotype == 'field':
    return "Fält"
  elif infotype == 'precision':
    return 'Precision'
  elif infotype == 'military':
    return 'Militär snabbmatch'
  else:
    return 'Okänk'

def get_signups(competition):
  result = {}

  data = fetch_data(competition = competition, page = "signups?page=1&per_page=1000")

  weaponclasses = {}
  signup_count = 0

  for signup in data['signups']['data']:
    weaponclass = signup['weaponclass']['classname_general']
    if weaponclass in ['CD', 'CVY', 'CVÄ']:
      weaponclass = 'C'
    firstname = signup['user']['name']
    lastname = signup['user']['lastname']
    card = signup['user']['shooting_card_number']
    name = f"{firstname} {lastname}"
    club = str(signup['club']['districts_id']) + '-' + str(signup['club']['clubs_nr'])
    if weaponclass not in weaponclasses:
      weaponclasses[weaponclass] = 0
    weaponclasses[weaponclass] += 1
    if args['club'] == club and args['card'] == None or args['card'] == card:
      classname = signup['weaponclass']['classname']
      share_patrol = signup['share_patrol_with']
      same_patrol_as = None
      signup_count += 1
      if share_patrol != 0:
        same_patrol_as = share_patrol
        for user in data['signups']['data']:
          if user['user']['shooting_card_number'] == f"{share_patrol}":
            same_patrol_as = f"{user['user']['name']} {user['user']['lastname']}"
      if not card in result.keys():
        result[card] = {'name': name, 'lines': []}
      if same_patrol_as == None:
        result[card]['lines'].append(f"{classname:<4}")
      else:
        result[card]['lines'].append(f"{classname:<4} - {same_patrol_as}")

  result[0] = {'name': args['club'], 'lines': []}
  result[0]['lines'].append("")
  result[0]['lines'].append(f"Total from {args['club']}: {signup_count}")
  result[0]['lines'].append("")
  result[0]['lines'].append("Total signups in weapon classes:")
  for key in sorted(weaponclasses):
    result[0]['lines'].append(f"{key}: {weaponclasses[key]}")

  return result

def get_starttimes(competition, ical = False):
  result = {}

  data = fetch_data(competition = competition, page = "patrols")

  filename = f"webshooter_{info['id']}.ical"
  file = None
  if ical == True:
    file = open(filename, "w")
    file.write("BEGIN:VCALENDAR\n")
    file.write("VERSION:2.0\n")
    file.write("PRODID:-//Webshooter//Pistol//SV\n")
    file.write("CALSCALE:GREGORIAN\n")

    # Set time zone
    file.write("BEGIN:VTIMEZONE\n")
    file.write("TZID:Europe/Stockholm\n")
    file.write(f"LAST-MODIFIED:{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}\n")
    file.write("TZURL:https://www.tzurl.org/zoneinfo-outlook/Europe/Stockholm\n")
    file.write("X-LIC-LOCATION:Europe/Stockholm\n")
    file.write("BEGIN:DAYLIGHT\n")
    file.write("TZOFFSETFROM:+0100\n")
    file.write("TZOFFSETTO:+0200\n")
    file.write("TZNAME:CEST\n")
    file.write("DTSTART:19700329T020000\n")
    file.write("RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=3\n")
    file.write("END:DAYLIGHT\n")
    file.write("BEGIN:STANDARD\n")
    file.write("TZOFFSETFROM:+0200\n")
    file.write("TZOFFSETTO:+0100\n")
    file.write("TZNAME:CET\n")
    file.write("DTSTART:19701025T030000\n")
    file.write("RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10\n")
    file.write("END:STANDARD\n")
    file.write("END:VTIMEZONE\n")

  for patrol in data['patrols']:
    start_time = patrol['start_time_human']
    end_time = patrol['end_time_human']
    patrolnr = patrol['sortorder']
    for signup in patrol['signups']:
      club = str(signup['club']['districts_id']) + '-' + str(signup['club']['clubs_nr'])
      card = signup['user']['shooting_card_number']
      if args['club'] == club and args['card'] == None or args['card'] == card:
        firstname = signup['user']['name']
        lastname = signup['user']['lastname']
        name = f"{firstname} {lastname}"
        classname = signup['weaponclass']['classname']
        weapongroup = signup['weaponclass']['classname_general']
        lane = signup['lane']
        if not card in result.keys():
          result[card] = {'name': name, 'lines': []}
        result[card]['lines'].append(f"{classname:<4} : Patrol {patrolnr:<2} ({start_time} - {end_time}) : Lane {lane}")
        if file != None:
          file.write("BEGIN:VEVENT\n")
          file.write(f"UID:webshooter_{info['id']}-{len(result[card]['lines'])}\n")
          file.write(f"DTSTAMP:{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}\n")
          file.write(f"DTSTART;TZID=Europe/Stockholm:{info['date'].replace('-','')}T{start_time.replace(':','')}00Z\n")
          file.write(f"DTEND;TZID=Europe/Stockholm:{info['date'].replace('-','')}T{end_time.replace(':','')}00Z\n")
          file.write(f"SUMMARY:{info['name']}\n")
          file.write(f"LOCATION:{info['city']}\n")
          file.write("DESCRIPTION:")
          file.write(f"{info['name']}\\n")
          file.write(f"{info['date']}\\n")
          file.write(f"{info['city']}\\n")
          file.write(f"{info['venue']}\\n")
          file.write(f"{type_to_string(info['type'])}\\n")
          file.write("\\n")
          file.write(f"Vapengrupp: {weapongroup}\\n")
          if info['type'] == 'field':
            file.write(f"Patrull: {patrolnr}\\n")
          else:
            file.write(f"Skjutlag: {patrolnr}\\n")
          file.write(f"Plats: {lane}\\n")
          file.write("\\n")
          file.write(f"<a href='https://webshooter.se/app/competitions/{info['id']}/information'>Webshooter Info</a>\n")
          file.write("END:VEVENT\n")

  if file != None:
    file.write("END:VCALENDAR\n")
    file.close();
    if not 0 in result.keys():
      result[0] = {'info': []}
    result[0]['info'].append("");
    result[0]['info'].append(f"Start times written to {filename}")

  return result

def get_results(competition, infotype):
  result = {}

  data = fetch_data(competition = competition, page = "results")

  total_points = {}
  std_medals = {}
  total_series = 0

  for first_pass in [ True, False ]:
    if not first_pass:
      if args['verbose']:
        print("Poängmetoden Precision:")
      if infotype == 'precision' or infotype == 'military':
        for key in total_points:
          if infotype == 'precision':
            if key == 'A':
              s = 46.1 * total_series
              b = 44.5 * total_series
            elif key == 'B':
              s = 47.0 * total_series
              b = 45.5 * total_series
            elif key == 'C':
              s = 47.1 * total_series
              b = 46.0 * total_series
            elif key in ('M1', 'M2', 'M3', 'M4'):
              s = 282
              b = 274
            elif key == 'M5':
              s = 294
              b = 288
            elif key in ('M6', 'M7'):
              s = 270
              b = 253
            elif key == 'M8':
              s = 999999
              b = 999998
            elif key == 'M9':
              s = 999999
              b = 999998
            else:
              print(f"Unknown weapon group: {key}")
              sys.exit(1)
          if infotype == 'military':
            if key == 'A':
              s = 540
              b = 516
            elif key == 'R':
              s = 552
              b = 528
            elif key == 'B':
              s = 561
              b = 537
            elif key == 'C':
              s = 564
              b = 540
            else:
              print(f"Unknown weapon group: {key}")
              sys.exit(1)
          s = math.ceil(s)
          b = math.ceil(b)
          if args['verbose']:
            print(f"{key} S: {s} B: {b}")

          std_medals[key] = {}
          std_medals[key]['s'] = s
          std_medals[key]['b'] = b

        if args['verbose']:
          print("Beräkningsmetoden:")
        for key in total_points:
          total_points[key].sort(reverse=True)
          count = len(total_points[key])
          s = 999999
          b = 999998
          if count >= 9:
            s = math.floor(count/9)
            s = total_points[key][s-1]
          if count >= 3:
            b = math.floor(count/3)
            b = total_points[key][b-1]
          if args['verbose']:
            print(f"{key}({count}) S: {s} B: {b}")

          std_medals[key]['s'] = min(std_medals[key]['s'], s)
          std_medals[key]['b'] = min(std_medals[key]['b'], b)

        if args['verbose']:
          print("Använda gränser:")
          for key in std_medals:
            print(f"{key} S: {std_medals[key]['s']} B: {std_medals[key]['b']}")

    for results in data['results']:
      series = 0
      firstname = results['signup']['user']['name']
      lastname = results['signup']['user']['lastname']
      card = results['signup']['user']['shooting_card_number']
      name = f"{firstname} {lastname}"
      club = str(results['signup']['club']['districts_id']) + '-' + str(results['signup']['club']['clubs_nr'])
      classname = results['weaponclass']['classname']
      placement = results['placement']
      if results['placement'] > 0:
        group = results['weaponclass']['classname_general'][0]
        if group != 'C':
          group = results['weaponclass']['classname_general']
        if total_points.get(group) == None:
          total_points[group] = []
        total_points[group].append(results['points'])
      if args['club'] == club and args['card'] == None or args['card'] == card:
        if results['figure_hits'] == 0 and results['points'] != 0:
          precision = True
        else:
          precision = False
        if precision:
          points = results['points']
        else:
          points = f"{results['hits']}/{results['figure_hits']}"
        if not first_pass:
          line = f"{classname:<4} : {placement:>2} - {points:<6}"
          if args['verbose'] or not precision:
            if results['std_medal'] != None:
              result[card]['medals'][results['std_medal']] += 1
              line += f"({results['std_medal']}) "
            else:
              line += "    "
          if precision:
            if points >= std_medals[group]['b']:
              if points >= std_medals[group]['s']:
                result[card]['medals']['S'] += 1
                line += "(S)"
              else:
                result[card]['medals']['B'] += 1
                line += "(B)"
            else:
              line += "   "
          line += " -"
          first = True
        for point in results['results']:
          series += 1
          if not first_pass:
            if not first:
              line += ","
              first = False
            if precision:
              line += f" {point['points']:>2}"
            else:
              line += f" {point['hits']}/{point['figure_hits']}"
          if not card in result.keys():
            result[card] = {'name': name, 'lines': [], 'medals': {'B': 0, 'S': 0}}
        if not first_pass:
          result[card]['lines'].append(line)
      if series > total_series:
        total_series = series

  return result

def get_competitions_list(year = None):
  result = {}

  data = fetch_data()

  for competition in data['competitions']['data']:
    if re.match(f"^{year}-", competition['date']) or year == None:
      result[competition['id']] = {}
      result[competition['id']]['date'] = competition['date']
      result[competition['id']]['type'] = competition['results_type']
      result[competition['id']]['type_readable'] = printable(competition['results_type_human'])

  return result

def get_medals(year = None):
  medals = {}

  competitions = get_competitions_list(year)
  for competition in competitions.keys():
    info = get_info(competition)
    results = get_results(competition, infotype=info['type'])
    for card in results.keys():
      if card != 0:
        if results[card]['medals']['S'] != 0 or results[card]['medals']['B'] != 0:
          if not info['type'] in medals:
            medals[info['type']] = {'S': 0, 'B': 0, 'type_readable': competitions[competition]['type_readable']}

          print(printable(f"{info['name']} - {info['city']} - {info['venue']}"))
          print(f"Medals: B: {results[card]['medals']['B']} S: {results[card]['medals']['S']}");
          if args['verbose']:
            for line in results[card]['lines']:
              name = printable(results[card]['name'])
              print(f"{name:<20} - {line}")

          medals[info['type']]['S'] += results[card]['medals']['S']
          medals[info['type']]['B'] += results[card]['medals']['B']
    time.sleep(1)

  print("")
  print("")
  print(f"Card: {args['card']}")
  print("")
  for type in medals.keys():
    print(f"{medals[type]['type_readable']:<20} S: {medals[type]['S']} B: {medals[type]['B']}")
  print("---")
  s = sum(m['S'] for m in medals.values() if m)
  b = sum(m['B'] for m in medals.values() if m)
  print(f"{'Total':<20} S: {s} B: {b}")

  return None

def get_starts_total(year = None):
  result = {}
  total = 0

  competitions = get_competitions_list(year)

  for competition in competitions.keys():
    info = get_info(competition)
    results = get_results(competition, infotype=info['type'])

    if info['type'] not in result:
      result[info['type']] = {}
      result[info['type']]['results'] = 0

    print(f"Datum: {competitions[competition]['date']} ID: {competition} Typ: {info['type']}")

    for card in results.keys():
      if card != 0:
        for line in results[card]['lines']:
          result[info['type']]['results'] += 1
          total += 1

  print(f"Club: {args['club']}")
  print(f"Year: {year}")
  print("")
  print(f"Total starts during {year}: {total}")
  print("")

  for type in result.keys():
    print(f"{type}: {result[type]['results']}")

  return None

def get_competitions(year = None):
  competitions = get_competitions_list(year)

  print(f"Total: {len(competitions)}")
  for competition in competitions.keys():
    print(f"Datum: {competitions[competition]['date']} ID: {competition:5} Typ: {competitions[competition]['type_readable']}")

  return None

info = None
competition = None
result = None

if args['mode'] == "signups" or args['mode'] == "starttimes" or args['mode'] == "ical" or args['mode'] == "results":
  competition = args['value']
  info = get_info(competition)

if args['mode'] == "signups":
  result = get_signups(competition)
elif args['mode'] == "starttimes":
  result = get_starttimes(competition)
elif args['mode'] == "ical":
  result = get_starttimes(competition, ical = True)
elif args['mode'] == "results":
  result = get_results(competition, infotype=info['type'])
elif args['mode'] == "medals":
  result = get_medals(year = args['value'])
elif args['mode'] == "starts":
  result = get_starts_total(year = args['value'])
elif args['mode'] == "list":
  result = get_competitions(year = args['value'])
else:
  print(f"Invalid mode, {args['mode']}")
  exit(1)

print("")

if info != None:
  print(printable(f"{info['name']} - {info['city']} - {info['venue']}"))
  print(f"Date {info['date']}")
  print(f"Type {info['type']}")
  print("")
  print(f"Webshooter id {info['id']}")
  print(f"Signup closing date {info['signups_close']}")

  print("")
  print(f"Club: {args['club']}")
  print("")

if result != None:
  for card in result.keys():
    if card != 0:
      if 'lines' in result[card]:
        for line in result[card]['lines']:
          name = printable(result[card]['name'])
          print(f"{name:<20} - {line}")

  if 0 in result.keys():
    if 'lines' in result[0]:
      for line in result[0]['lines']:
        print(f"{line}")

  if 0 in result.keys():
    if 'info' in result[0]:
      for line in result[0]['info']:
        print(f"{line}")
