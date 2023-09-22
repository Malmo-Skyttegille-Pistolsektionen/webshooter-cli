#!/usr/bin/python3

import json
import time
import subprocess
import argparse
import re
import configparser
import os

MODES = "starttimes, results, signups"

CURL_URL = "'https://webshooter.se/api/v4.1.9/competitions/{competition}/{page}'"
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
parser.add_argument('-d', '--debug', help = "Debug", required = False, action='store_true', default=False)

args = parser.parse_args().__dict__

config = configparser.ConfigParser()
config.read_file(open(f"{os.path.expanduser('~')}/.webshooter.rc"))

if args['club'] is None:
  args['club'] = config.get('global', 'club')

if args['token'] is None:
  args['token'] = config.get('global', 'token')

def fetch_data(page):
  if args['debug']:
    filename = f"testdata/webshooter_{page.split('?')[0]}.json"
    with open(filename) as f:
      print(f"Reading file {filename}")
      output = f.read()
  else:
    print(f"Fetching {page.split('?')[0]}")
    curl = f"curl {CURL_URL} {CURL_OPTIONS}"
    output = subprocess.run(curl.format(**args, page=page), shell = True, capture_output = True)
    output = output.stdout.decode()

  return json.loads(output)

def get_signups():
  result = {}

  data = fetch_data(page="signups?page=1&per_page=1000")

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
        result[card]['lines'].append(f"{name:<20} - {classname:<4}")
      else:
        result[card]['lines'].append(f"{name:<20} - {classname:<4} - {same_patrol_as}")

  result[0] = {'name': args['club'], 'lines': []}
  result[0]['lines'].append("")
  result[0]['lines'].append(f"Total from {args['club']}: {signup_count}")
  result[0]['lines'].append("")
  result[0]['lines'].append("Total signups in weapon classes:")
  for key in sorted(weaponclasses):
    result[0]['lines'].append(f"{key}: {weaponclasses[key]}")

  return result

def get_starttimes():
  result = {}

  data = fetch_data(page="patrols")

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
        result[card]['lines'].append(f"{name:<20} - {classname:<4} : Patrol {patrolnr:<2} ({start_time} - {end_time}) : Lane {lane}")

  return result

def get_results():
  result = {}

  data = fetch_data(page="results")

  for results in data['results']:
    firstname = results['signup']['user']['name']
    lastname = results['signup']['user']['lastname']
    card = results['signup']['user']['shooting_card_number']
    name = f"{firstname} {lastname}"
    club = str(results['signup']['club']['districts_id']) + '-' + str(results['signup']['club']['clubs_nr'])
    if args['club'] == club:
      classname = results['weaponclass']['classname']
      placement = results['placement']
      if results['figure_hits'] == 0 and results['points'] != 0:
        precision = True
      else:
        precision = False
      if precision:
        points = results['points']
      else:
        points = f"{results['hits']}/{results['figure_hits']}"
      line = f"{firstname:<10} {lastname:<20} - {classname:<4} : {placement:>2} - {points:<5}"
      if results['std_medal'] is not None:
        line += f"({results['std_medal']})"
      else:
        line += "   "
      line += " -"
      first = True
      for point in results['results']:
        if not first:
          line += ","
          first = False
        if precision:
          line += f" {point['points']}"
        else:
          line += f" {point['hits']}/{point['figure_hits']}"
      if not card in result.keys():
        result[card] = {'name': name, 'lines': []}
      result[card]['lines'].append(line)

  return result

if args['mode'] == "signups":
  result = get_signups()
elif args['mode'] == "starttimes":
  result = get_starttimes()
elif args['mode'] == "results":
  result = get_results()
else:
  print("Invalid mode")
  print(f"Available modes: {MODES}")
  exit(1)

print("")
print(f"Club: {args['club']}")
print("")

for card in result.keys():
  if card != 0:
    if args['card'] is None or args['card'] == card:
      if args['name'] is None or args['name'] == result[card]['name']:
        for line in result[card]['lines']:
          print(f"{line}")

if 0 in result.keys():
  for line in result[card]['lines']:
    print(f"{line}")

