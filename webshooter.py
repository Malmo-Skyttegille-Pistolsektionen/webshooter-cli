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

MODES = "starttimes, results, signups"

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

parser = argparse.ArgumentParser(description = "Webshooter start times")
parser.add_argument('competition', help = "Competition ID, check the link in webshooter")
parser.add_argument('--token', help = "Token, copy from Firefox: Web Developer Tools -> Storage -> Local Storage -> token")
parser.add_argument('--name', help = "Name")
parser.add_argument('--club', help = "Club")
parser.add_argument('--card', help = "Card")
parser.add_argument('--mode', help = f"Mode, available modes: {MODES}", required = True)
parser.add_argument('-v', '--verbose', help = "Verbose", required = False, action='store_true', default=False)
parser.add_argument('-d', '--debug', help = "Debug", required = False, action='store_true', default=False)

args = parser.parse_args().__dict__

configfile = f"{os.path.expanduser('~')}/.webshooter.rc"
if os.path.exists(configfile):
  config = configparser.ConfigParser()
  config.read_file(open(configfile))

  if args['club'] is None:
    args['club'] = config.get('global', 'club')

  if args['token'] is None:
    args['token'] = config.get('global', 'token')

elif args['token'] is None:
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

def fetch_data(competition, page):
  if args['debug']:
    if page is None:
      filename = f"testdata/webshooter_{competition}.json"
    else:
      filename = f"testdata/webshooter_{competition}_{page.split('?')[0]}.json"
    with open(filename) as f:
      print(f"Reading file {filename}")
      output = f.read()
  else:
    if page is None:
      print(f"Fetching {args['competition']}")
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

  data = fetch_data(competition = competition, page = None)

  info['id'] = competition
  info['name'] = data['competitions']['name']
  info['city'] = data['competitions']['contact_city']
  info['venue'] = data['competitions']['contact_venue']
  info['date'] = data['competitions']['date']
  info['signups_close'] = data['competitions']['signups_closing_date']
  info['type'] = data['competitions']['results_type']

  return info

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
    if args['club'] == club:
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
      if same_patrol_as is None:
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

def get_starttimes(competition):
  result = {}

  data = fetch_data(competition = competition, page = "patrols")

  for patrol in data['patrols']:
    start_time = patrol['start_time_human']
    end_time = patrol['end_time_human']
    patrolnr = patrol['sortorder']
    for signup in patrol['signups']:
      club = str(signup['club']['districts_id']) + '-' + str(signup['club']['clubs_nr'])
      if args['club'] == club:
        firstname = signup['user']['name']
        lastname = signup['user']['lastname']
        card = signup['user']['shooting_card_number']
        name = f"{firstname} {lastname}"
        classname = signup['weaponclass']['classname']
        lane = signup['lane']
        if not card in result.keys():
          result[card] = {'name': name, 'lines': []}
        result[card]['lines'].append(f"{classname:<4} : Patrol {patrolnr:<2} ({start_time} - {end_time}) : Lane {lane}")

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
          s = math.floor(count/9)
          s = total_points[key][s-1]
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
        if total_points.get(group) is None:
          total_points[group] = []
        total_points[group].append(results['points'])
      if args['club'] == club:
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
            if results['std_medal'] is not None:
              line += f"({results['std_medal']}) "
            else:
              line += "    "
          if precision:
            if points >= std_medals[group]['b']:
              if points >= std_medals[group]['s']:
                line += "(S)"
              else:
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
            result[card] = {'name': name, 'lines': []}
        if not first_pass:
          result[card]['lines'].append(line)
      if series > total_series:
        total_series = series

  return result

info = get_info(competition = args['competition'])

if args['mode'] == "signups":
  result = get_signups(competition = args['competition'])
elif args['mode'] == "starttimes":
  result = get_starttimes(competition = args['competition'])
elif args['mode'] == "results":
  result = get_results(competition = args['competition'], infotype=info['type'])
else:
  print("Invalid mode")
  print(f"Available modes: {MODES}")
  exit(1)

print("")

i = f"{info['name']} - {info['city']} - {info['venue']}"
if config.has_option('global', 'unicode') and not config.getboolean('global', 'unicode'):
  i = unicodedata.normalize('NFKD', i)
  i = u"".join([c for c in i if not unicodedata.combining(c)])
print(f"{i}")
print(f"Date {info['date']}")
print(f"Type {info['type']}")
print("")
print(f"Webshooter id {info['id']}")
print(f"Signup closing date {info['signups_close']}")

print("")
print(f"Club: {args['club']}")
print("")

for card in result.keys():
  if card != 0:
    if args['card'] is None or args['card'] == card:
      if args['name'] is None or args['name'] == result[card]['name']:
        for line in result[card]['lines']:
          name = result[card]['name']
          if config.has_option('global', 'unicode') and not config.getboolean('global', 'unicode'):
            name = unicodedata.normalize('NFKD', name)
            name = u"".join([c for c in name if not unicodedata.combining(c)])
          print(f"{name:<20} - {line}")

if 0 in result.keys():
  for line in result[card]['lines']:
    print(f"{line}")

