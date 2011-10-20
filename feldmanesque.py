#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Charles Li <chuck@mixed-metaphors.com>
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

import urllib2,re,datetime,calendar,sys,getopt,json
from urllib2 import URLError
from pyo import *

SND_PATH = 'snds/'
URL_TIMEOUT = 100


def main(argv=None):

#   citycode = "CAXX0301"
    citycode = "CYUL"
    f_len = 50
    update_interval = 1800
    sounds = []

    if argv == None:
        argv = sys.argv
    try:
        opts, args = getopt.getopt(argv[1:], "hc:n:u:",["help"])
    except getopt.error, msg:
        print "Invalid options"

    for o, a in opts:
        if o in ("-h", "--help"):
            print """
            -c <weather.com citycode, default CAXX0301 (Montreal)>
            -n <length of forecast in hours, from 1 to 180, default 50>
            -u <data update interval in seconds, default 1800>
            """
            sys.exit(2)
        if o == "-c": citycode = a
        if o == "-n": f_len = int(a)
        if o == "-u": update_interval = int(a)

# start pyo server

    s = Server(nchnls=2, buffersize=1024, duplex=0).boot()
    s.start()

# initiate sounds

    forecast = ScrapeHourly(citycode,f_len)
    temp_melody = TempMelody(temp=forecast["temp"],clouds=forecast["clouds"],feelslike=forecast["feelslike"])
#    wind_melody = WindMelody(wspd=forecast["wspd"],wdir=forecast["wdir"],pop=forecast["pop"])
    sounds.append(temp_melody._exc)
    sounds.append(temp_melody._exc2)
#    sounds.append(wind_melody._exc)
    mix = Mix(sounds,2).out()
    mixverb = Freeverb(mix,size=0.9,damp=0.95).out()
#    reset_sounds(sounds, ambient_sounds)

#    update_mixdown(sounds, ambient_sounds)

# update sound data every once in a while

    while True:
        time.sleep(update_interval)
#        forecast = WeatherScrape(citycode)

# ----------- Start of weather scraping functions ---------------

# scrape current weather

hourly_regex = re.compile("hbhTDConditionIcon.*?(\d+)\.gif.*?"
    "hbhTDCondition.*?(\d+).*?"
    "hbhTDFeels.*?(\d+).*?"
    "hbhTDPrecip.*?(\d+).*?"
    "hbhTDHumidity.*?(\d+).*?"
    "hbhTDWind.*?(Calm|([NSEW]+).*?(\d+))",re.DOTALL)

def ScrapeHourly_old(citycode,hourly_length):
    
    hourly = {"length":hourly_length,"conditions":[],"temp":[],"feels":[],"pop":[],"humidity":[],"wind":[],"wind_dir":[]}
    try:
        url = urllib2.urlopen("http://www.weather.com/weather/hourbyhour/"+
            citycode, timeout=URL_TIMEOUT).read()
    except URLError:
        print "Weather server timed out"

    hourly_all = hourly_regex.findall(url)
    print hourly_all

def ScrapeHourly(citycode,f_len):
    try:
        url = urllib2.urlopen('http://api.wunderground.com/api/59660bdc41616057/hourly7day/q/'+citycode+'.json')
    except URLError:
        print "Weather server timed out"
    temp = []
    dewpoint = []
    clouds = []
    humidity = []
    wspd = []
    wdir = []
    pop = []
    feelslike = []

    forecast = json.loads(url.read())['hourly_forecast']
    for i in range(0,len(forecast)):
        temp.append(int(forecast[i]["temp"]["english"]) * 6)
        temp.append(int(forecast[i]["dewpoint"]["english"]) * 6)
#        dewpoint.append(int(forecast[i]["dewpoint"]["english"]) * 7)
        clouds.append(int(forecast[i]["sky"])/10.0)
        humidity.append(int(forecast[i]["humidity"])/10.0)
        wspd.append(int(forecast[i]["wspd"]["metric"]))
        wdir.append(int(forecast[i]["wdir"]["degrees"]))
        pop.append(int(forecast[i]["pop"])/10.0)
        feelslike.append(int(forecast[i]["feelslike"]["english"]) * 6)
        feelslike.append(int(forecast[i]["humidity"]) * 6)
    return {"temp":temp[:f_len],"clouds":clouds[:f_len],"humidity":humidity[:f_len],"wspd":wspd,"wdir":wdir,"pop":pop,"feelslike":feelslike[:f_len]}

class TempMelody(object):
    def __init__(self,temp,clouds,feelslike,time=0.3,dur=3,mul=.2):
        self._temp = temp
        self._clouds = clouds
        self._feelslike = feelslike
        self._time = time
        self._dur = dur
        self._mul = mul
        self._env = CosTable([(0,0),(140,1),(1370,0.45),(3600,0,23),(8191,0)])
        self._env2 = ChebyTable([0.8,0.5,0.9,0.2,0.3,0.2,0,0.1])
        self._seq = Seq(time=self._time,seq=self._clouds,poly=len(clouds)).play()
        self._amp = TrigEnv(self._seq,table=self._env,dur=self._dur,mul=self._mul)
        self._amp2 = TrigEnv(self._seq,table=self._env2,dur=self._dur,mul=self._mul)
        self._exc = SineLoop(freq=self._temp,feedback=0.05,mul=self._amp)
        self._exc2 = SineLoop(freq=self._feelslike,feedback=0.05,mul=self._amp2)

        @property
        def temp(self): return self._temp
        @temp.setter
        def temp(self,x): self._temp = x
        @property
        def clouds(self): return self._clouds
        @clouds.setter
        def clouds(self,x):self._clouds = x
        @property
        def time(self): return self._time
        @time.setter
        def time(self,x):self._time = x
        @property
        def dur(self): return self._dur
        @dur.setter
        def dur(self,x):self._dur = x
        @property
        def mul(self): return self._mul
        @mul.setter
        def mul(self,x):self._mul = x
        @property
        def env(self): return self._env
        @env.setter
        def env(self,x):self._env = x

class WindMelody(object):
    def __init__(self,wspd,wdir,pop,time=.3,dur=2,mul=.2):
        self._wspd = wspd
        self._wdir = wdir
        self._pop = pop
        self._time = time
        self._dur = dur
        self._mul = mul
        self._env = ChebyTable([0.8,0.5,0.9,0.9])
        self._seq = Seq(time=self._time,seq=self._pop,poly=len(pop)).play()
        self._amp = TrigEnv(self._seq,table=self._env,dur=self._dur,mul=self._mul)
        self._exc = SineLoop(freq=self._wdir,feedback=0.05,mul=self._amp)

if __name__ == "__main__":
    sys.exit(main())
