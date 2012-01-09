#############################################################################
#
#   Copyright (C) 2011 Navi-X
#
#   This file is part of Navi-X.
#
#   Navi-X is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   Navi-X is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with Navi-X.  If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

#############################################################################
#
# CPlayer:
# Video and audio player class which extends the funcionality of the default
# xbmc player class.
#############################################################################

from string import *
import sys, os.path
import urllib
import urllib2
import re, random, string
import xbmc, xbmcgui
import re, os, time, datetime, traceback
import shutil
import zipfile
from libs2 import *
from settings import *
from CURLLoader import *
from CFileLoader import *

try: Emulating = xbmcgui.Emulating
except: Emulating = False

#####################################################################
# Description: My player class, overrides the XBMC Player
######################################################################
class CPlayer(xbmc.Player):
    def  __init__(self, core, function):
        self.function=function
        self.core=core
        self.stopped=False
        self.pls = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
#        self.pls.clear()

        xbmc.Player.__init__(self)

    def onPlayBackStarted(self):
        self.function(1)
    
    def onPlayBackEnded(self):
        self.stopped=True
        self.function(2)
        
    def onPlayBackStopped(self):
        self.stopped=True
        self.function(3)

    ######################################################################
    # Description: Play the video, audio in the playlist
    # Parameters : playlist = the input playlist containing all items
    #              first = index of first item
    #              lasts = index of last item
    # Return     : 0 if succesful, -1 if no audio, video files in list
    ######################################################################    
    def play(self, playlist, first, last):
        self.pls.clear()

        if first == last:
            URL = playlist.list[first].URL
            xbmc.Player.play(self, URL)
        else:
        
            index = first
            urlopener = CURLLoader()
            self.stopped=False
            while (index <= last) and (self.stopped == False) and (self.pls.size() < 10):               
                type = playlist.list[index].type
                if type == 'video' or type == 'audio':
                    URL = playlist.list[index].URL

                    result = urlopener.urlopen(URL, playlist.list[index])
                    if result == 0:
                        loc_url = urlopener.loc_url

                        name = playlist.list[index].name
                        
                        #if (xbmc.getInfoLabel("System.BuildVersion")[:1] == '9') or \
                        #   (xbmc.getInfoLabel("System.BuildVersion")[:2] == '10'):                        
                        listitem = xbmcgui.ListItem(name)
                        listitem.setInfo('video', {'Title': name})
                        self.pls.add(url=loc_url, listitem=listitem)                      
                        #else:
                        #    self.pls.add(loc_url, name)
                        
                        if self.pls.size() == 1:
                            #start playing, continue loading                      
                            xbmc.Player.play(self, self.pls)
                index = index + 1
            
            if self.pls.size() == 0:
                #no valid items found
                return -1
                
        return 0

    ######################################################################
    ######################################################################            
    def play_URL(self, URL, mediaitem=0):
        #URL=mediaitem.URL
        #check if the URL is empty or not
        if URL == '':
            return -1
                                              
        urlopener = CURLLoader()
        result = urlopener.urlopen(URL, mediaitem)
        if result != 0:
            return -1    
        URL = urlopener.loc_url
        
        SetInfoText("Loading...... ", setlock=True)

        self.pls.clear() #clear the playlist
                
        ext = getFileExtension(URL)
#todo ashx  
        if ext == 'ashx':
            ext = 'm3u'
               
        if ext == 'pls' or ext == 'm3u':
            loader = CFileLoader2() #file loader
            loader.load(URL, tempCacheDir + "playlist." + ext, retries=2)
            if loader.state == 0: #success
                result = self.pls.load(loader.localfile)
                if result == False:
                    return -1
                    
                #xbmc.Player.play(self, self.pls) #play the playlist
                self.play_media(loader.localfile)
        else:
            #self.pls.add(urlopener.loc_url)
            if mediaitem.playpath != '':
                self.play_RTMP(mediaitem.URL, mediaitem.playpath, mediaitem.swfplayer, mediaitem.pageurl);
            else: 
                self.play_media(URL)
            
        return 0

    ######################################################################
    ######################################################################  
    def play_media(self, URL):
        if xbmc.getInfoLabel("System.BuildVersion")[:2] == '10':
            #XBMC Dharma
            cmd = 'xbmc.PlayMedia(%s)' % URL
            xbmc.executebuiltin(cmd)
        else:
            xbmc.Player.play(self, URL)
            
    ######################################################################
    ###################################################################### 
    def play_RTMP(self, URL, playpath, swfplayer, pageurl):
        #check if the URL is empty or not
        if URL == '':
            return -1
    
        self.pls.clear() #clear the playlist
    
        item=xbmcgui.ListItem('', iconImage='', thumbnailImage='')
        if swfplayer != '':
            item.setProperty("SWFPlayer", swfplayer)
        if playpath != '':
            item.setProperty("PlayPath", playpath)
        if pageurl != '':
            item.setProperty("PageURL", pageurl)

        xbmc.Player(xbmc.PLAYER_CORE_DVDPLAYER).play(URL, item)
        
        return 0
        
