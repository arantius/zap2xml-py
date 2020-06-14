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

The zap2it site, at least for my area/OTA, only gives 12 hours of data.
(Without logging in -- and I don't want to write that code!)  So this is
designed to be run every 3/6 hours or so.  Every URL is cached, so you can go
more often with little extra cost.

Written to have only standard library dependencies.  I.e. to be a single file.
"""

import argparse
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request
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


def get_cached(cache_dir, cache_key, delay, url):
  cache_path = cache_dir.joinpath(cache_key)
  if cache_path.is_file():
    with open(cache_path, 'rb') as f:
      return f.read()
  else:
    print('Fetching:', url)
    resp = urllib.request.urlopen(url)
    result = resp.read()
    with open(cache_path, 'wb') as f:
      f.write(result)
    time.sleep(delay)
    return result


def remove_stale_cache(cache_dir, zap_time):
  for p in cache_dir.glob('*'):
    try:
      t = int(p.name)
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
  # Start time parameter is now rounded down to nearest `zap_timespan`, in s.
  zap_time = time.time()
  zap_time_window = args.zap_timespan * 3600
  zap_time = int(zap_time - (zap_time % zap_time_window)) + zap_time_window

  remove_stale_cache(cache_dir, zap_time)

  out = ET.Element('tv')
  out.set('source-info-url', 'http://tvlistings.zap2it.com/')
  out.set('source-info-name', 'zap2it.com')
  out.set('generator-info-name', 'zap2xml.py')
  out.set('generator-info-url', 'github.com/arantius/zap2xml-py')

  # Fetch 12 hours of data, in `zap_timespan` chunks.
  for i in range(int(12 / args.zap_timespan)):
    i_time = zap_time + (i * zap_time_window)
    qs = base_qs.copy()
    qs['lineupId'] = '%s-%s-DEFAULT' % (args.zap_country, args.zap_headendId)
    qs['time'] = i_time
    url = 'https://tvlistings.zap2it.com/api/grid?'
    url += urllib.parse.urlencode(qs)

    result = get_cached(cache_dir, str(i_time), args.delay, url)
    d = json.loads(result)

    if not done_channels:
      done_channels = True
      for c_in in d['channels']:
        c_out = ET.SubElement(out, 'channel')
        c_out.set(
            'id', 'I%s.%s.zap2it.com' % (c_in['channelNo'], c_in['channelId']))
        ET.SubElement(c_out, 'display-name').text \
            = '%s %s' % (c_in['channelNo'], c_in['callSign'])
        ET.SubElement(c_out, 'display-name').text = c_in['channelNo']
        ET.SubElement(c_out, 'display-name').text = c_in['callSign']

  out_path = pathlib.Path(__file__).parent.joinpath('xmltv.xml')
  with open(out_path.absolute(), 'wb') as f:
    f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write(ET.tostring(out, encoding='UTF-8'))

  sys.exit(err)


if __name__ == '__main__':
  main()
