#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Charles Li <chuck@mixed-metaphors.net>
# Copyright (c) 2011 Tristan Matthews <le.businessman@gmail.com>

# This file is part of CloudSound.

# CloudSound is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# CloudSound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with CloudSound.  If not, see <http://www.gnu.org/licenses/>.

import urllib2,re,datetime,calendar,sys,getopt
from urllib2 import URLError
from pyo import *

SND_PATH = 'snds/'
URL_TIMEOUT = 100

def main(argv=None):

    citycode = "CAXX0301"
    sounds = []
    ambient_sounds = []

    if argv == None:
        argv = sys.argv
    try:
        opts, args = getopt.getopt(argv[1:], "hc:")
    except getopt.error, msg:
        print "Invalid options"

    for o, a in opts:
        if o in ("-h", "--help"):
            print "-c <citycode>"
            sys.exit(2)
        if o == "-c": citycode = a

    while True:
        current, forecast = WeatherScrape(citycode)
        reset_sounds(sounds, ambient_sounds)
        update_rain(current["rain"], current["temp"], current["conditions"], ambient_sounds)
        update_snow(current["rain"], current["temp"], current["conditions"], ambient_sounds)
        update_thunder(current["conditions"], ambient_sounds)
        update_wind(current["wind"], ambient_sounds)
        update_cricket(current["temp"], ambient_sounds)
        update_melody(current["humidity"], forecast["highs"], forecast["lows"],
                    forecast["pop"], sounds)
        update_mixdown(sounds, ambient_sounds)
        time.sleep(120)


def weather_to_int(nn):
    nn_num = 1
    if re.search(r'sun',nn,re.I): nn_num -= 1
    if re.search(r'cloud',nn,re.I): nn_num += 1
    if re.search(r'showers',nn,re.I): nn_num += 2
    if re.search(r'rain',nn,re.I): nn_num += 3
    if re.search(r'snow|flurries|ice|hail',nn,re.I): nn_num += 50
    if re.search(r'thunder',nn,re.I): nn_num += 100
    return nn_num

# scrape current weather

regex = re.compile("twc-col-2 twc-forecast-icon.*?alt=\"([\w\s]+)\".*?"
"twc-col-1 twc-forecast-temperature\"><strong>([\d\.]+).*?"
"Chance of Rain:.*?(\d+).*?"
"Wind:<br><strong>.*?(Calm|[\w\s]+ at[\s\n]+(\d+)).*?"
"Humidity:<\/span>\s*([\d]+|N\/A).*?", re.DOTALL)

# scrape 10 day forecast

regex2 = re.compile(
"twc-(wx-hi\d+|wx-low\d+|line-precip)\">.*?(--|\d+)",re.DOTALL)

def WeatherScrape(citycode):

    current = {}
    forecast = {"conditions":[],"highs":[],"lows":[],"pop":[]}

    try:
        url = urllib2.urlopen("http://www.weather.com/weather/today/"+citycode, timeout=URL_TIMEOUT).read()
    except URLError:
        url = open('CAXX0301').read()

    print "got data"
    cur = regex.search(url)

    current["conditions"] = weather_to_int(cur.group(1))
    print current["conditions"]
    current["temp"] = (float(cur.group(2))-32)*5/9.0
    print current["temp"]
    current["rain"] = int(cur.group(3))
    print current["rain"]
    if cur.group(4) == "Calm": current["wind"] = 0
    else: current["wind"] = float(cur.group(5))*1.609344
    print current["wind"]
    if cur.group(6) == "N/A": current["humidity"] = 0
    else: current["humidity"] = float(cur.group(6))
    print current["humidity"]

    try:
        url2 = urllib2.urlopen("http://www.weather.com/weather/tenday/"+citycode, timeout=URL_TIMEOUT).read()
    except URLError:
        url2 = open('CAXX0301.1').read()

    fore = regex2.findall(url2)

    for n in range(1,10):
        forecast["highs"].append((int(fore[n][1])-32)*5/9.0*14)
    print forecast["highs"]
    for n in range(11,20):
        forecast["lows"].append((int(fore[n][1])-32)*5/9.0*7)
    print forecast["lows"]
    for n in range(21,30):
        forecast["pop"].append(int(fore[n][1])/12.0)
    print forecast["pop"]
    return current,forecast

# --------------- Sound Stuff -----------------------------------

# start pyo server

s = Server(nchnls=2, buffersize=512, duplex=0).boot()
s.start()

def reset_sounds(sounds, ambient_sounds):
    for s in sounds:
        s.stop()
        del s
    for a in ambient_sounds:
        a.stop()
        del a

    sounds = []
    ambient_sounds = []

# raindrop
def update_rain(rain, temp, cond, ambient_sounds):
    if rain and temp > 0 or cond == 54:
        drops = [SND_PATH + 'water_drops1.aif' for i in range(1,32)]
        num_drops = len(drops)
        olaps = 4
        tabs = []
        trtabs = []
        trrnds = []
        cl = Cloud(density=(rain/10)**2 + rain/5 - 2, poly=num_drops*olaps).play()
        for i in range(num_drops):
            tabs.append(SndTable(drops[i]))

        for j in range(olaps):
           offset = j * num_drops
           for i in range(num_drops):
               index = i + offset
               trrnds.append(TrigChoice(cl[index],[0.75,1,1.25,1.5,2]))
               ambient_sounds.append(TrigEnv(cl[index],table=tabs[i],dur=1./tabs[i].getRate()*trrnds[index]))

# snow
def update_snow(rain, temp, cond, ambient_sounds):
    if rain and temp <= 0 or cond == 54:
        snow = SndTable(SND_PATH + 'walking-in-snow-1.aif')
        env = Osc(snow, freq=1.0/snow.getDur()).out()
        ambient_sounds.append(env)

# thunder
def update_thunder(cond, ambient_sounds):
    if cond > 100:
        thunder = SndTable(SND_PATH + 'thunder.aif')
        ambient_sounds.append(Osc(table=thunder, freq=thunder.getRate(), mul=.5).out())

# the wind

def update_wind(wind, ambient_sounds):
    if wind:
        metro = Metro(time=.250).play()
        wind1_ctrl = TrigRand(metro, min=wind*15, max=wind*16, port=2)
        wind2_ctrl = TrigRand(metro, min=wind*18, max=wind*19, port=2)
        wind1 = Noise(mul=0.5)
        wind2 = Noise(mul=0.5)
        ambient_sounds.append(Biquad(wind1, freq=wind1_ctrl, q=5, type=0))
        ambient_sounds.append(Biquad(wind2, freq=wind2_ctrl, q=5, type=0))

# crickets - current temperature via Dolbear's Law
def update_cricket(temp, ambient_sounds):
    if temp < 0: temp = 0.7 + 1.0/temp*-1
    cricket = SndTable(SND_PATH + 'cricket.aif')
    temperature = temp # change this to change temperature
    temperature_in_file = 25.0
    chirps_in_file = 20
    temperature_ratio = temperature / temperature_in_file
    ambient_sounds.append(Pan(Osc(table=cricket, freq=cricket.getRate() *
        temperature_ratio,mul=1),outs=2,pan=0.8).out())


def update_melody(humidity, forecast_highs, forecast_lows, forecast_pop, sounds):
    # humidity - controls speed of forecast melody
    humid = .5 + humidity/100.0*.5

    # temperature forecast - highs and lows

    now = datetime.datetime.now()
    week_day = calendar.weekday(now.year,now.month,now.day)
    day_seq = [1,1,1,1,1,3,3]
    day_seq = day_seq[week_day:] + day_seq[:week_day]
    day_seq.pop(0)
    day_seq[-1] += 1

    env = CosTable([(0,0),(300,1),(1000,.3),(8191,0)])
    env2 = HarmTable([1,0,.33,0,.2,0,.143,0,.111])
    seq = Seq(time=humid, seq=day_seq, poly=6).play()
    amp = TrigEnv(seq, table=env, dur=1, mul=.5)
    amp2 = TrigEnv(seq, table=env2, dur=1, mul=.5)
    sounds.append(Pan(SineLoop(freq=forecast_highs,
        feedback=0.05,mul=amp),outs=2,pan=0.2).out())
    sounds.append(Pan(SineLoop(freq=forecast_lows,
        feedback=0.05,mul=amp2),outs=2,pan=0.9).out())

    # rain forecast
    ramp = TrigEnv(seq, table=env, dur=1, mul=forecast_pop)
    rt = SndTable(SND_PATH + 'water_drops1.aif')
    sounds.append(Freeverb(Pan(Osc(table=rt, freq=100, mul=ramp),outs=2,pan=0.5)).out())

def update_mixdown(sounds, ambient_sounds):
    # mixdown!
    sounds += ambient_sounds
    #mix = Biquad(Mix(sounds, 2, mul=1), freq=1/humidity*17400+600)
    mix = Mix(sounds,2,mul=1)
    sounds.append(Freeverb(mix, size=0.9, damp=0.95).out())

if __name__ == "__main__":
    sys.exit(main())
