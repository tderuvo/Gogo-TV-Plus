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
# CURLLoader:
# This class Retrieves the URL to a media item which the XBMC player 
# understands.
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
from CFileLoader import *

try: Emulating = xbmcgui.Emulating
except: Emulating = False

class CURLLoader:
    def __init__(self, parent=0):
        self.parent=parent

    ######################################################################
    # Description: This class is used to retrieve the direct URL of given
    #              URL which the XBMC player understands.
    #              
    # Parameters : URL=source URL, mediaitem = mediaitem to open
    # Return     : 0=successful, -1=fail
    ######################################################################
    def urlopen(self, URL, mediaitem=0):
        result = 0 #successful

        if mediaitem.processor != '':
            result = self.geturl_processor(mediaitem) 
        elif URL.find('http://www.youtube.com') != -1:
            mediaitem.processor = "http://navix.turner3d.net/proc/youtube"
            result = self.geturl_processor(mediaitem) 
        elif URL[:4] == 'http':
            result = self.geturl_redirect(URL) 
        else:
            self.loc_url = URL
        
        return result

    ######################################################################
    # Description: This class is used to retrieve the real URL of 
    #              a media item. The XBMC player sometimes fails to handle
    #              HTTP redirection. Therefore we do it here.           
    # Parameters : URL=source URL
    # Return     : 0=successful, -1=fail
    ######################################################################
    def geturl_redirect(self, URL):        
        try:
            values = { 'User-Agent' : 'Mozilla/4.0 (compatible;MSIE 7.0;Windows NT 6.0)'}
            req = urllib2.Request(URL, None, values)
            f = urllib2.urlopen(req)
            self.loc_url=f.geturl()
            f.close()            
        except IOError:
            return -1 # failed
        
        #always return true    
        return 0

    ######################################################################
    # Description: This class is used to retrieve media playback
    #              parameters using a processor server
    #              
    # Parameters : mediaitem = mediaitem to open
    # Return     : 0=successful, -1=fail
    ######################################################################
    def geturl_processor(self, mediaitem):
        cache_filename=procCacheDir + ProcessorLocalFilename(mediaitem.processor)
        is_cached=False
        proc_ori=""
        htmRaw=""
        if cache_filename>"" and os.path.exists(cache_filename):
            # use cached processor if no older than 24 hours
            if os.path.getmtime(cache_filename) + 60*60*24 > time.mktime(time.gmtime()):
                try:
                    htmRaw=open(cache_filename, 'r').read()
                    is_cached=True
                    print "Processor: phase 1 - query\n URL: "+mediaitem.URL+"\n Processor (cached): "+mediaitem.processor
                except IOError:
                    pass

        if htmRaw=="":
            print "Processor: phase 1 - query\n URL: "+mediaitem.URL+"\n Processor: "+mediaitem.processor
            SetInfoText("Processor: getting filter...")
            htmRaw=getRemote(mediaitem.processor+'?url='+urllib.quote_plus(mediaitem.URL),{'cookie':'version='+Version+'.'+SubVersion+'; platform='+platform})['content']
            proc_ori=htmRaw

        if htmRaw <= '':
            print "Processor error: nothing returned from learning phase";
            SetInfoText("")
            return -1

        if htmRaw[:2]=='v2':
            htmRaw=htmRaw[3:]
            inst=htmRaw
            htmRaw=''
            phase=0
            exflag=False
            phase1complete=False
            verbose=0
            proc_args=''
            inst_prev=''
            headers={}

            v=NIPLVars()

            ## command parser
            lparse=re.compile('^([^ =]+)([ =])(.+)$')

            ## condition parser
            ifparse=re.compile('^([^<>=!]+)\s*([!<>=]+)\s*(.+)$');

            ## dot property parser
            dotvarparse=re.compile('^(nookies|s_headers)\.(.+)$');

            nookies=NookiesRead(mediaitem.processor)
            for ke in nookies:
                hkey='nookies.'+ke
                v[hkey]=nookies[ke]['value']

            while exflag==False:
                scrape=1
                phase=phase+1
                rep={}

                if_satisfied=False
                if_next=False
                if_end=False

                src_printed=False

                ## load defaults into v, leave undefined keys alone
                v.reset()

                ## get instructions if args present
                if proc_args>'':
                    SetInfoText("Processor: phase "+str(phase)+" learn")
                    print "Processor: phase "+str(phase)+" learn"
                    inst=getRemote(mediaitem.processor+'?'+proc_args)['content']
                    proc_args=''
                elif phase1complete:
                    SetInfoText("")
                    print "Processor error: nothing to do"
                    exflag=True
                else:
                    v['s_url']=mediaitem.URL

                if inst==inst_prev:
                    print "Processor error: endless loop detected"
                    SetInfoText("")
                    return -1

                inst_prev=inst
                v['NIPL']=inst
                lines=inst.splitlines()
                if len(lines) < 1:
                    print "Processor error: nothing returned from phase "+str(phase)
                    SetInfoText("")
                    return -1
                linenum=0
                for line in lines:
                    linenum=linenum+1
                    line=re.sub('^\s*', '', line)

                    if verbose>0 and src_printed==False:
                        print "Processor NIPL source:\n"+inst
                        src_printed=True

                    if line>'' and verbose>1:
                        noexec=''
                        if if_next or if_end:
                            noexec=' (skipped)'
                        str_report="NIPL line "+str(linenum)+noexec+": "+line
                        if verbose>2 and (if_next or if_satisfied or if_end):
                            str_report=str_report+"\n (IF: satisfied="+str(if_satisfied)+", skip to next="+str(if_next)+", skip to end="+str(if_end)+")"
                        print str_report

                    # skip comments and blanks
                    if line[:1]=='#' or line[:2]=='//' or line=='':
                        continue

                    if if_end and line!='endif':
                        continue

                    if if_next and line[0:5]!='elseif' and line!='else' and line!='endif':
                        continue

                    if line=='else':
                        if if_satisfied:
                            if_end=True
                        else:
                            if_next=False
                            if verbose>0:
                                print "Proc debug else: executing"
                        continue

                    elif line=='endif':
                        if_satisfied=False
                        if_next=False
                        if_end=False
                        continue

                    elif line=='scrape':
                        str_info="Processor:"
                        if phase>1:
                            str_info=str_info+" phase "+str(phase)
                        str_info=str_info+" scrape"
                        if scrape>1:
                            str_info=str_info+" "+str(scrape)
                        SetInfoText(str_info)
                        if v['s_url']=='':
                            print "Processor error: no scrape URL defined"
                            SetInfoText("")
                            return -1
                        scrape=scrape+1
                        scrape_args={
                          'referer': v['s_referer'],
                          'cookie': v['s_cookie'],
                          'method': v['s_method'],
                          'agent': v['s_agent'],
                          'action': v['s_action'],
                          'postdata': v['s_postdata'],
                          'headers': headers
                        }
                        print "Processor "+v['s_method'].upper()+"."+v['s_action']+": "+v['s_url']
                        if verbose>0:
                            print "Proc debug remote args:"
                            print scrape_args
                        remoteObj=getRemote(v['s_url'], scrape_args)
                        #print remoteObj


                        v['htmRaw']=remoteObj['content']
                        v['geturl']=remoteObj['geturl']
                        # backwards-compatibility for pre 3.5.4
                        if v['s_action']=='geturl':
                            v['v1']=v['geturl']
                        str_out="Proc debug headers:"
                        for ke in remoteObj['headers']:
                            hkey='headers.'+ke
                            str_out=str_out+"\n "+ke+": "+str(remoteObj['headers'][ke])
                            v[hkey]=str(remoteObj['headers'][ke])
                        if verbose>0:
                            print str_out

                        str_out="Proc debug cookies:"
                        for ke in remoteObj['cookies']:
                            hkey='cookies.'+ke
                            str_out=str_out+"\n "+ke+": "+str(remoteObj['cookies'][ke])
                            v[hkey]=str(remoteObj['cookies'][ke])
                        if verbose>0:
                            print str_out

#                        if v['s_action']=='headers':
#                            headers=remoteObj
#                            str_out="Proc debug headers:"
#                            for ke in headers:
#                                str_out=str_out+"\n "+ke+": "+str(headers[ke])
#                                v[ke]=str(headers[ke])
#                            if verbose>0:
#                                print str_out
#                        elif v['s_action']=='geturl':
#                            v['v1']=remoteObj
#                        else:
#                            v['htmRaw']=remoteObj

                        if v['s_action']=='read' and v['regex']>'' and v['htmRaw']>'':
                            # get finished - run regex, populate v(alues) and rep(ort) if regex is defined
                            v['nomatch']=''
                            rep['nomatch']=''
                            for i in range(1,11):
                                ke='v'+str(i)
                                v[ke]=''
                                rep[ke]=''
                            p=re.compile(v['regex'])
                            match=p.search(v['htmRaw'])
                            if match:
                                rerep='Processor scrape:';
                                for i in range(1,len(match.groups())+1):
                                    val=match.group(i)
                                    key='v'+str(i)
                                    rerep=rerep+"\n "+key+'='+val
                                    rep[key]=val
                                    v[key]=val
                                if verbose>0:
                                    print rerep

                            else:
                                if verbose>0:
                                    print 'Processor scrape: no match'
                                rep['nomatch']=1
                                v['nomatch']=1

                        # reset scrape params to defaults
                        v.reset('scrape')

                    elif line=='play':
                        if verbose==1:
                            print "Proc debug: play"
                        exflag=True
                        break

                    elif line=='report':
                        rep['phase']=str(phase)
                        proc_args=urllib.urlencode(rep)
                        proc_args=re.sub('v\d+=&','&',proc_args)
                        proc_args=proc_args.replace('nomatch=&','&')
                        proc_args=re.sub('&+','&',proc_args)
                        proc_args=re.sub('^&','',proc_args)
                        str_report="Processor report:"
                        for ke in rep:
                            if rep[ke]>'':
                                str_report=str_report+"\n "+ke+": "+rep[ke]
                        print str_report
                        break

                    else:
                        # parse
                        match=lparse.search(line)
                        if match is None:
                            print "Processor syntax error: "+line
                            SetInfoText("")
                            return -1
                        subj=match.group(1)
                        arg=match.group(3)

                        if subj=='if' or subj=='elsif':
                            if if_satisfied:
                                if_end=True
                            else:

                                ### process if / elseif operators
                                match=ifparse.search(arg)
                                if match:
                                    ### process if with operators
                                    lkey=match.group(1)
                                    oper=match.group(2)
                                    rraw=match.group(3)
                                    if oper=='=':
                                        oper='=='
                                    if rraw[0:1]=="'":
                                        rside=rraw[1:]
                                    else:
                                        rside=v[rraw]
                                    bool=eval("v[lkey]"+oper+"rside")
                                    if_report=" test: "+lkey+" "+oper+" "+rraw+"\n  left: "+v[lkey]+"\n right: "+rside

                                else:
                                    ### process single if argument for >''
                                    bool=v[arg]>''
                                    if_report=arg
                                    if bool:
                                        if_report=if_report+" > "
                                    else:
                                        if_report=if_report+" = "
                                    if_report=if_report+"'': "+str(v[arg])

                            if bool:
                                if_satisfied=True
                                if_next=False
                            else:
                                if_next=True

                            if verbose>0:
                                print "Proc debug "+subj+" => "+str(bool)+":\n "+if_report
                            continue

                        if match.group(2)=='=':
                            # assignment operator
                            if arg[0:1]=="'":
                                val=arg[1:]
                                areport="string literal"
                            else:
                                val=v[arg]
                                areport=arg

                            match=dotvarparse.search(subj);
                            if match:
                                dp_type=match.group(1)
                                dp_key=match.group(2)
                                tsubj=dp_key
                                if dp_type=='nookies':
                                    # set nookie
                                    treport="nookie"
                                    NookieSet(mediaitem.processor, dp_key, val, v['nookie_expires'])
                                    v[subj]=val

                                elif dp_type=='s_headers':
                                    # set scrape header
                                    treport="scrape header"
                                    headers[dp_key]=val

                            else:
                                # set variable
                                treport="variable"
                                tsubj=subj
                                v[subj]=val

                            if verbose>0:
                                print "Proc debug "+treport+": "+tsubj+" set to "+areport+"\n "+val

                        else:
                            ## do command
                            if subj=='verbose':
                                verbose=int(arg)

                            elif subj=='error':
                                print "Processor error: "+arg[1:]
                               	SetInfoText("")
                               	return -1

                            elif subj=='report_val':
                                match=lparse.search(arg)
                                if match is None:
                                    print "Processor syntax error: "+line
                                    SetInfoText("")
                                    return -1
                                ke=match.group(1)
                                va=match.group(3)
                                if va[0:1]=="'":
                                    rep[ke]=va[1:]
                                    if verbose>0:
                                        print "Proc debug report value: "+ke+" set to string literal\n "+va[1:]
                                else:
                                    rep[ke]=v[va]
                                    if verbose>0:
                                        print "Proc debug report value: "+ke+" set to "+va+"\n "+v[va]

                            elif subj=='concat':
                                match=lparse.search(arg)
                                if match is None:
                                    print "Processor syntax error: "+line
                                    SetInfoText("")
                                    return -1
                                ke=match.group(1)
                                va=match.group(3)
                                oldtmp=v[ke]
                                if va[0:1]=="'":
                                    v[ke]=v[ke]+va[1:]
                                else:
                                    v[ke]=v[ke]+v[va]
                                if verbose>0:
                                    print "Proc debug concat:\n old="+oldtmp+"\n new="+v[ke]

                            elif subj=='match':
                                v['nomatch']=''
                                rep['nomatch']=''
                                for i in range(1,11):
                                    ke='v'+str(i)
                                    v[ke]=''
                                    rep[ke]=''
                                p=re.compile(v['regex'])
                                try:
                                    match=p.search(v[arg])
                                except TypeError:
                                    v['nomatch']=1

                                if match:
                                    rerep='Processor match '+arg+':';
                                    for i in range(1,len(match.groups())+1):
                                        val=match.group(i)
                                        key='v'+str(i)
                                        rerep=rerep+"\n "+key+'='+val
                                        v[key]=val
                                    if verbose>0:
                                        print rerep

                                else:
                                    if verbose>0:
                                        print "Processor match: no match\n regex: "+v['regex']+"\n search: "+v[arg]
                                    v['nomatch']=1

                            elif subj=='replace':
                               # pre-set regex, replace var [']val
                                match=lparse.search(arg)
                                if match is None:
                                    print "Processor syntax error: "+line
                                    SetInfoText("")
                                    return -1
                                ke=match.group(1)
                                va=match.group(3)
                                if va[0:1]=="'":
                                    va=va[1:]
                                else:
                                    va=v[va]
                                oldtmp=v[ke]
                                v[ke]=re.sub(v['regex'], va, v[ke])
                                if verbose>0:
                                    print "Proc debug replace "+ke+":\n old="+oldtmp+"\n new="+v[ke]

                            elif subj=='unescape':
                                oldtmp=v[arg]
                                v[arg]=urllib.unquote(v[arg])
                                if verbose>0:
                                    print "Proc debug unescape:\n old="+oldtmp+"\n new="+v[arg]

                            elif subj=='escape':
                                oldtmp=v[arg]
                                v[arg]=urllib.quote_plus(v[arg])
                                if verbose>0:
                                    print "Proc debug escape:\n old="+oldtmp+"\n new="+v[arg]

                            elif subj=='debug':
                                if verbose>0:
                                    try:
                                        print "Processor debug "+arg+":\n "+v[arg]
                                    except KeyError:
                                        print "Processor debug "+arg+" - does not exist\n"

                            elif subj=='print':
                                if arg[0:1]=="'":
                                    print "Processor print: "+arg[1:]
                                else:
                                    print "Processor print "+arg+":\n "+v[arg]

                            elif subj=='countdown':
                                if arg[0:1]=="'":
                                    secs=arg[1:]
                                else:
                                    secs=v[arg]
                                cd_flag=countdown_timer(int(secs), v['countdown_title'], v['countdown_caption'])
                                if cd_flag==False:
                                    SetInfoText("")
                                    return -1
                            
                            else:
                                print "Processor error: unrecognized method '"+subj+"'"
                                SetInfoText("")
                                return -1

            if v['agent']>'':
                v['url']=v['url']+'?|User-Agent='+v['agent']
            mediaitem.URL=v['url']
            if useLibrtmp and (v['playpath']>'' or v['swfplayer']>''):
                mediaitem.URL=mediaitem.URL+' tcUrl='+v['url']
                if v['app']>'':
                    mediaitem.URL=mediaitem.URL+' app='+v['app']
                if v['playpath']>'':
                    mediaitem.URL=mediaitem.URL+' playpath='+v['playpath']
                if v['swfplayer']>'':
                    mediaitem.URL=mediaitem.URL+' swfUrl='+v['swfplayer']
                if v['pageurl']>'':
                    mediaitem.URL=mediaitem.URL+' pageUrl='+v['pageurl']
                if v['swfVfy']>'':
                    mediaitem.URL=mediaitem.URL+' swfVfy='+v['swfVfy']
                if v['live']>'':
                    mediaitem.URL=mediaitem.URL+' live=1'

            else:
                mediaitem.swfplayer=v['swfplayer']
                mediaitem.playpath=v['playpath']
                mediaitem.pageurl=v['pageurl']

            mediaitem.processor=''

            ## cache
            if v['cacheable']>'' and not is_cached:
                f=open(cache_filename, 'w')
                f.write(proc_ori)    
                f.close()
                print "Processor cached as " + cache_filename


        else:
            ## proc v1
            arr=htmRaw.splitlines()
            if len(arr) < 1:
                print "Processor error: nothing returned from learning phase";
                SetInfoText("")
                return -1
            URL=arr[0]
            if URL.find('error')==0:
                print "Processor: "+URL
                SetInfoText("")
                return -1
            report="Processor: phase 2 - instruct\n URL: "+URL
            if len(arr) < 2:
                self.loc_url = URL
                SetInfoText("")
                print "Processor: single-line processor stage 1 result\n playing "+URL
                return 0
            filt=arr[1]
            report=report+"\n filter: "+filt
            if len(arr) > 2:
                ref=arr[2]
                report=report+"\n referer: "+ref
            else:
                ref=''
            if len(arr) > 3:
                cookie=arr[3]
                report=report+"\n cookie: "+cookie
            else:
                cookie=''

            print report
            SetInfoText("Processor: scraping...")
            htm=getRemote(URL,{'referer':ref,'cookie':cookie})['content']
            if htm == '':
                print "Processor error: nothing returned from scrape"
                SetInfoText("")
                return -1

            p=re.compile(filt)
            match=p.search(htm)
            if match:
                tgt=mediaitem.processor
                sep='?'
                report='Processor: phase 3 - scrape and report'
                for i in range(1,len(match.groups())+1):
                    val=urllib.quote_plus(match.group(i))
                    tgt=tgt+sep+'v'+str(i)+'='+val
                    sep='&'
                    report=report+"\n v"+str(i)+": "+val
                print report
                SetInfoText("Processor: processing...")
                htmRaw2=getRemote(tgt)['content']
                if htmRaw2<='':
                    print "Processor error: could not retrieve data from process phase"
                    SetInfoText("")
                    return -1
                arr=htmRaw2.splitlines()
                mediaitem.URL=arr[0]

                if arr[0].find('error')==0:
                    print "Processor: "+arr[0]
                    SetInfoText("")
                    return -1
                if len(arr) > 1:
                    if useLibrtmp:
                        mediaitem.URL=mediaitem.URL+' tcUrl='+arr[0]+' swfUrl='+arr[1]
                        if len(arr) > 2:
                            mediaitem.URL=mediaitem.URL+' playpath='+arr[2]
                        if len(arr) > 3:
                            mediaitem.URL=mediaitem.URL+' pageUrl='+arr[3]
                    else:
                        mediaitem.swfplayer=arr[1]
                        if len(arr) > 2:
                            mediaitem.playpath=arr[2]
                        if len(arr) > 3:
                            mediaitem.pageurl=arr[3]
                mediaitem.processor=''
            else:
                print "Processor error: pattern not found in scraped data"
                SetInfoText("")
                return -1

        self.loc_url = mediaitem.URL

        SetInfoText("Processor complete - playing...")
        time.sleep(.1)
        SetInfoText("")
        report="Processor final result:\n URL: "+self.loc_url
        if mediaitem.playpath>'':
            report=report+"\n PlayPath: "+mediaitem.playpath
        if mediaitem.swfplayer>'':
            report=report+"\n SWFPlayer: "+mediaitem.swfplayer
        if mediaitem.pageurl>'':
            report=report+"\n PageUrl: "+mediaitem.pageurl
        print report

        return 0


######################################################################
# Description: This class is used to create the variable dictionary
#              object used by NIPL. Its primary purpose is to allow
#              querying dictionary elements which don't exist without
#              crashing Python, although a comple of methods have been
#              added for initializing and resetting the object.
#              
# Parameters : URL=source URL
# Return     : 0=successful, -1=fail
######################################################################
class NIPLVars:

    def __init__(self):
        self.data=self.defaults()

    def __getitem__(self, key):
        try:
            return self.data[key]
        except KeyError:
            return ''

    def __setitem__(self,key,value):
        self.data[key]=value

    def defaults(self):
        return {
            'htmRaw':'',
            's_url':'',
            'regex':'',
            's_method':'get',
            's_action':'read',
            's_agent':'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.4) Gecko/2008102920 Firefox/3.0.4',
            's_referer':'',
            's_cookie':'',
            's_postdata':'',
            'url':'',
            'swfplayer':'',
            'playpath':'',
            'agent':'',
            'pageurl':'',
            'app':'',
            'swfVfy':'',
            'nookie_expires':'0'
        }

    def reset(self,rtype=""):
        v_defaults=self.defaults()
        if rtype=="scrape":
            for ke in ('s_method','s_action','s_agent','s_referer','s_cookie','s_postdata'):
                self.data[ke]=v_defaults[ke]
        elif rtype=="hard":
            self.data=self.defaults()
        else:
            for ke in v_defaults:
                self.data[ke]=v_defaults[ke]

#end of file
