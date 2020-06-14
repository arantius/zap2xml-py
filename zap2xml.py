#!/usr/bin/env python
"""zap2xml.py -- The simplest zap2it scraper I could write.

Around June 2020 the `zap2xml.pl` I had stopped working.  It generated HTTP
requests that gave only 400 responses.  I tried to patch it, to the point that
it got OK responses, but parsed no data from them.  The zap2it site must have
changed.  I thought they had an API, but apparently this tool has always
scraped the internal JSON feed, built just for the web site?

So re-write from scratch.  Simplest possible form I can, so the fewest things
need to change if the site ever does again.  The goal is to feed guide data
into Tvheadend.
"""

import argparse
import pathlib
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET


def get_args():
  parser = argparse.ArgumentParser(
      description='Fetch TV data from zap2it.',
      epilog='This tool is noisy to stdout; with cron use ')
  parser.add_argument(
      '--aid', dest='zap_aid', type=str, default='gapzap',
      help='Raw zap2it input parameter.  (Affiliate ID?)')
  parser.add_argument(
      '-c', '--country', dest='zap_country', type=str, default='USA',
      help='Country identifying the listings to fetch.')
  parser.add_argument(
      '-d', '--delay', dest='delay', type=int, default=5,
      help='Delay, in seconds, between server fetches.')
  parser.add_argument(
      '--device', dest='zap_device', type=str, default='-',
      help='Raw zap2it input parameter.  (?)')
  parser.add_argument(
      '--headend-id', dest='zap_headendId', type=str, default='lineupId',
      help='Raw zap2it input parameter.  (?)')
  parser.add_argument(
      '--is-override', dest='zap_isOverride', type=bool, default=True,
      help='Raw zap2it input parameter.  (?)')
  parser.add_argument(
      '--language', dest='zap_languagecode', type=str, default='en',
      help='Raw zap2it input parameter.  (Language.)')
  parser.add_argument(
      '--pref', dest='zap_pref', type=str, default='',
      help='Raw zap2it input parameter.  (Preferences?)')
  parser.add_argument(
      '--timespan', dest='zap_timespan', type=int, default=3,
      help='Raw zap2it input parameter.  (Hours of data per fetch?)')
  parser.add_argument(
      '--timezone', dest='zap_timezone', type=str, default='',
      help='Raw zap2it input parameter.  (Time zone?)')
  parser.add_argument(
      '--user-id', dest='zap_userId', type=str, default='-',
      help='Raw zap2it input parameter.  (?)')
  parser.add_argument(
      '-z', '--zip', '--postal', dest='zap_postalCode', type=str, required=True,
      help='The zip/postal code identifying the listings to fetch.')
  return parser.parse_args()


def get_cached(cache_dir, cache_key, url):
  pass


def remove_stale_cache(cache_dir, zap_time):
  for p in cache_dir.glob('*.js.gz'):
    try:
      t = int(''.join(filter(str.isdigit, p.name)))
      if t >= zap_time: continue
    except:
      pass
    print('Removing stale cache file:', p.name)
    p.unlink()


def main():
  cache_dir = pathlib.Path(__file__).parent.joinpath('cache')
  if not cache_dir.is_dir():
    cache_dir.mkdir()

  args = get_args()
  base_qs = {k[4:]: v for (k, v) in vars(args).items() if k.startswith('zap_')}
  done_channels = False
  err = 0
  # Start time parameter is now rounded up to nearest `zap_timespan`, in s.
  zap_time = time.time()
  zap_time_window = args.zap_timespan * 3600
  zap_time = int(zap_time - (zap_time % zap_time_window)) + zap_time_window

  remove_stale_cache(cache_dir, zap_time)

  out = ET.Element('tv')
  out.set('source-info-url', 'http://tvlistings.zap2it.com/')
  out.set('source-info-name', 'zap2it.com')
  out.set('generator-info-name', 'zap2xml.py')
  out.set('generator-info-url', 'github.com/arantius/zap2xml-py')

  # Fetch three days' data, in `zap_timespan` chunks.
  for i in range(int(48 / args.zap_timespan)):
    i_time = zap_time + (i * zap_time_window)
    qs = base_qs.copy()
    qs['lineupId'] = '%s-%s-DEFAULT' % (args.zap_country, args.zap_headendId)
    qs['time'] = i_time
    url = 'https://tvlistings.zap2it.com/api/grid?'
    url += urllib.parse.urlencode(qs)

    print(url)
    txt_json = get_cached(cache_dir, i_time, url)

  out_path = pathlib.Path(__file__).parent.joinpath('xmltv.xml')
  #out_file = open(out_path.absolute)

  sys.exit(err)


if __name__ == '__main__':
  main()
