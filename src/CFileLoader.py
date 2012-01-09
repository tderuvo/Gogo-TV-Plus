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
# CFileloader:
# This class is a generic file loader and handles downloading a file to disk.
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
import ftplib
from settings import *
from libs2 import *
from CServer import *

try: Emulating = xbmcgui.Emulating
except: Emulating = False

#todo: Add support for FTP files.

class CFileLoader2:
    ######################################################################
    # Description: Downloads a file in case of URL and returns absolute
    #              path to the local file.
#@todo: Fill parameters    
    # Parameters : URL=source, localfile=destination
    # Return     : -
    ######################################################################
    def load(self, URL, localfile='', timeout=0, proxy="CACHING", \
             content_type= '', retries=0):
              
        if (URL == ''):# or (localfile == ''):
            self.state = -1 #failed
            return
        
        destfile = localfile       
        self.data=''
        
        if (URL[:4] == 'http') or (URL[:3] == 'ftp'):
            sum_str = ''
            if proxy != "DISABLED":
                sum = 0
                #calculate hash of URL
                for i in range(len(URL)):
                    sum = sum + (ord(URL[i]) * i)
                sum_str = str(sum)
            
            if localfile != '':
                ext_pos = localfile.rfind('.') #find last '.' in the string
                if ext_pos != -1:
                    destfile = localfile[:ext_pos] + sum_str + localfile[ext_pos:]
                else:
                    destfile = localfile + sum_str
            else:
                destfile = tempCacheDir + sum_str  

            if proxy == "INCACHE":
                if os.path.exists(destfile) == True:
                    self.localfile = destfile
                    self.state = 0 #success
#todo: load file in memory if localfile = ''                    
                else:
                    self.state =  -1 #failed 
            elif (not((proxy == "ENABLED") and (os.path.exists(destfile) == True))):
                if URL[:3] == 'ftp':
                    self.loadFTP(URL, destfile, timeout, proxy, content_type, retries)
                else:
                    self.loadHTTP(URL, destfile, timeout, proxy, content_type, retries)                       
            else: #file is inside the cache
                self.localfile = destfile
                self.state = 0 #success
                
                if localfile == '':
                    try:
                        f = open(self.localfile, 'r')
                        self.data = f.read()
                        f.close()
                    except IOError:
                        self.state =  -1 #failed                                              
        else: #localfile    
            if (URL[1] == ':') or (URL[0] == '/'): #absolute (local) path
                self.localfile = URL
                self.state = 0 #success
            else: #assuming relative (local) path
                self.localfile = RootDir + SEPARATOR + URL
                self.state = 0 #success
            
#            Trace(self.localfile)
            
            if localfile == '':
                try:
                    f = open(self.localfile, 'r')
                    self.data = f.read()
                    f.close()
                except IOError:
                    self.state =  -1 #failed
            
    ######################################################################
    # Description: Downloads a file in case of URL and returns absolute
    #              path to the local file.
#@todo: Fill parameters    
    # Parameters : URL=source, localfile=destination
    # Return     : -
    ######################################################################           
    def loadHTTP(self, URL, localfile='', timeout=0, proxy="CACHING", \
                  content_type= '', retries=0):
        if timeout != 0:
            socket_setdefaulttimeout(timeout)
        self.state = -1 #failure
        counter = 0
                
        while (counter <= retries) and (self.state != 0):
            counter = counter + 1 
            try:

                
            
                cookies = ''
                if URL.find(nxserver_URL) != -1:
                    cookies = 'platform=' + platform + '; version=' + Version +'.'+ SubVersion
                    cookies = cookies + '; nxid=' + nxserver.user_id
                    values = { 'User-Agent' : 'Mozilla/4.0 (compatible;MSIE 7.0;Windows NT 6.0)',
                    'Cookie' : cookies}
                else:
                    values = { 'User-Agent' : 'Mozilla/4.0 (compatible;MSIE 7.0;Windows NT 6.0)'}
                        
                #print values
                                   
                req = urllib2.Request(URL, None, values)
                #req = urllib2.Request(URL)
                f = urllib2.urlopen(req)
                
                headers = f.info()
                                                
                type = headers['Content-Type']
                    
                if (content_type != '') and (type.find(content_type)  == -1):
                    #unexpected type
                    if timeout != 0:
                        socket_setdefaulttimeout(url_open_timeout)            
                    self.state = -1 #failed
                    break #do not try again                            
                        
                #open the destination file
                self.data = f.read()
                file = open(localfile, "wb")   
                file.write(self.data)
                file.close()
                f.close()                          
                       
                self.localfile = localfile
                self.state = 0 #success       
                  
            except IOError, e:
                if hasattr(e, 'reason'):
                    print 'We failed to reach a server.'
                    print 'Reason: ', e.reason
                elif hasattr(e, 'code'):
                    print 'The server could not fulfill the request.'
                    print 'Error code: ', e.code    
                self.state = -1 #failed

#           except urllib2.HTTPError:
#               socket_setdefaulttimeout(oldtimeout)
#
#               Trace("There was an http error: ")
#               self.state = -1 #failed

#           except urllib2.URLError, e:
#               socket_setdefaulttimeout(oldtimeout)
#
#               Trace("There is a problem with the URL: " + str(e.reason))
#               self.state = -1 #failed
                
        if timeout != 0:
            socket_setdefaulttimeout(url_open_timeout)                     
    
        #end function
              
    ######################################################################
    # Description: Downloads a file in case of URL and returns absolute
    #              path to the local file.
#@todo: Fill parameters    
    # Parameters : URL=source, localfile=destination
    # Return     : -
    ######################################################################        
    def loadFTP(self, URL, localfile='', timeout=0, proxy="CACHING", \
                  content_type= '', retries=0):
        self.state = 0 #success      
        
        #Parse URL according RFC 1738: ftp://user:password@host:port/path 
        #There is no standard Python funcion to split these URL's.
        username=''
        password=''        
        port=21
        
        #check for username, password
        index = URL.find('@')
        if index != -1:
            index2 = URL.find(':',6,index)
            if index2 != -1:
                username = URL[6:index2]
                print 'user: ' + username
                password = URL[index2+1:index]
                print 'password: ' + password            
            URL = URL[index+1:]
        else:
            URL = URL[6:]
        
        #check for host
        index = URL.find('/')
        if index != -1:
            host = URL[:index]
            path = URL[index:]
        else:
            host = URL
            path = ''
            
        #retrieve the port
        index = host.find(':')
        if index != -1:
            port = int(host[index+1:])
            host = host[:index]
            
        print 'host: ' + host    
        print 'port: ' + str(port)
            
        #split path and file
        index = path.rfind('/')
        if index != -1:
            file = path[index+1:]
            path = path[:index]
        else:
            file = ''        
        
        print 'path: ' + path
        print 'file: ' + file
       
        try:
            self.f = ftplib.FTP()
            self.f.connect(host,port)
        except (socket.error, socket.gaierror), e:
            print 'ERROR: cannot reach "%s"' % host
            self.state = -1 #failed to download the file
            return

        print '*** Connected to host "%s"' % host

        try:
            if username != '':
                self.f.login(username, password)
            else:
                self.f.login()
        except ftplib.error_perm:
            print 'ERROR: cannot login anonymously'
            self.f.quit()
            self.state = -1 #failed to download the file
            return

        print '*** Logged in as "anonymous"'

        try:
            self.f.cwd(path)
        except ftplib.error_perm:
            print 'ERROR: cannot CD to "%s"' % path
            self.f.quit()
            self.state = -1 #failed to download the file
            return

        print '*** Changed to "%s" folder' % path

        #retrieve the file
        self.bytes = 0
        #self.file = open(localfile, 'wb')

        try:
            self.f.retrbinary('RETR %s' % file, open(localfile, 'wb').write)
            self.localfile = localfile
            #self.size = self.f.size(file)
            #self.size_MB = float(self.size) / (1024 * 1024)
            #self.percent2 = 0
            #self.f.retrbinary('RETR %s' % file, self.download_fileFTP_callback)
        except ftplib.error_perm:
            print 'ERROR: cannot read file "%s"' % file
            os.unlink(self.file)
            self.state = -1 #failed
        else:
            print '*** Downloaded "%s" to CWD' % file
        
        self.f.quit()
        
        #end function
        
