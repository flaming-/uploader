'''a utility / library for uploading to what.cd.
and also some converting things.

by flaming, 2012.

See license.txt for license information.
(MIT-style License) (permissive)

--- functions:

    --- helper functions (to be used by the main functions later)
    pprint (*things) -- if the global flag 'verbose' is True, prints things.
        otherwise, does nothing.
    select_folder(startfolder=default_folder,msg) -- presents a Tkinter folder
        select dialog starting at startfolder. msg is the title of the window.
        Usually this function is avoidable (if looking for automating).
    create_torrent(folder,tracker) -- creates a torrent file (using the
        py3createtorrent library) for 'folder' with tracker 'tracker'. Private
        flag is on. Outputs this torrent file into the directory this script
        is running from.
    get_auth() -- logs in and returns the authkey flag.
    get_tracker_url() -- gets the tracker url. only works if authed.
    to_imgur(filename) -- uploads the image 'filename' to imgur, using their
        lovely API. returns the url of the image on imgur.
        notes -- hoping for whatimg to release an API so this can be to it!
    get_tags(folder) -- gets tags from the files in that folder (using the
        mutagen library, with some modifications) and returns this tuple:
        (artist,album,year,format,bitrate,image,tracks,total_length)
        notes -- there is an addformat argument that isn't implemented yet.
        Also, the artist,album,year,format,bitrate stuff is extracted from
        the first file it finds in the folder! So a multi-artist album will not
        be uploaded properly!
    make_tracklist(tracks,total_length=None) -- makes a beautiful tracklist
        using the titles and durations of the tracks. this is used in the album
        description of new uploads.
    get_extra_data(addformat=False) -- prompts the user to enter extra data
        (using the console). If addformat == True, only prompts for 'media',
        otherwise prompts for media, tags, release_type and an optional
        additional description.
    create_data(torrent,tags,extra_data,authkey) -- creates the data form used
        by upload.php (and by submit_form() ). This method is only for primary
        uploads (i.e., not adding a format of an album that exists onsite
        already). For addformat, see function create_data_addformat() .
    submit_form(data) -- takes data in the form returned by create_data() and
        sends it to upload.php . If upload was successful, returns the groupid
        of the newly uploaded torrent. If not successful, writes the response
        page to response.html .
    create_data_addformat(torrent,tags,extra_data,authkey,groupid) --
        same as create_data but takes additional argument groupid. 'tags' and
        'extra_data' require less actual values, because you're just adding a
        format; see code for more info.
    submit_form_addformat(data,groupid) -- takes data created by
        create_data_addformat() and sends it to upload.php?groupid=whatever .
        Same response.html as submit_form() , also returns groupid.

    --- main functions for use
    run(folder=None,reuse_extras=False) -- folder is the folder to be uploaded.
        reuse_extras is for if you are going to be using the same extras later
        for an addformat (as used by perfect_three_and_upload() ).
    run_addformat(folder=None,groupid=None,extras=None) -- folder is folder to
        be uploaded, groupid is the groupid you're adding this to, extras
        is optional if you want to reuse the data from a previous
        get_extra_data() .

    --- functions that deal with threaded / conversion
    get_number_of_processors() -- returns number of processors on this system
    actives() -- an alias for threading.activeCount() . returns the number of
        active threads at any given moment.
    get_threads_number() -- returns the max number of threads that we are aiming
        for using. This is actives() + num_proc .
    filecopy(file_in,file_out) -- copies file_in to file_out . We use this to
        copy the images and other non-music files from original folder to new
        converted folders.
    make_lame_metadata(artist,title=None,album=None,year=None,track_num=None) --
        makes lame metadata string using the given values. You can pass the
        arguments individually, or you can also pass just one arg, a tuple:
        (artist,title,album,year,track_num)
    make_lame_params(bitrate) -- turns string 'V0' into '-V 0' , etc.
    flac_to_mp3(file_in,file_out,lame_params,lame_metadata) -- basically:
        opens up flac file for decoding, opens mp3 file for encoding, decodes
        flac into buffer, simultaneously feeds that buffer into lame for
        encoding. Uses the lame metadata string from make_lame_metadata() .
    convert_perfect_three(folder=None,outfolder=None) -- you give it a folder
        with flacs in it, and another folder, for example '/user/etc/' . Creates
        subdirectories of outfolder named 'Artist - Album (Year) [format]', as
        in '/user/etc/Deastro - Moondagger (2009) [V0]'. Converts the flac files
        to perfect three (320, V0, V2) in their respective directories. Copies
        the extra files (cover.jpg, etc) over to the new directories. Does not
        copy any files ending in .log or .cue . Returns a list of the new
        directories.
        notes -- this is threaded! appreciate how cool / useful that is, please.
    perfect_three_and_upload(infolder=None,outfolder=None) -- basically:
        does convert_perfect_three(infolder,outfolder) and then uploads them.
        only prompts you for get_extra_data once, it reuses it between uploads.
    
--- globals
    num_proc -- the value from get_number_of_processors() . This probably should
        not change during the life of the program, unless you install another
        processor while your code is running...? So might as well put it in a
        global rather than having to call a function over and over.
    threads_number -- calls get_threads_number() when no extra threads are
        running. This value is usually 1 or 2 depending on the environment.
    USERNAME -- set in your config.txt . Your site username.
    PASSWORD -- set in your config.txt . Your site password. Don't worry, this
        is only ever transferred over ssl.
    flac_path -- set in your config.txt . The path to your flac binary.
        by default this is os.path.join('codecs','flac')
    lame_path -- set in your config.txt . The path to your lame binary.
        by default this is os.path.join('codecs','lame')

'''

import urllib, urllib2 as req, Tkinter, tkFileDialog, os, threading, time, sys

from mutagen import flac, mp3
from MultipartPostHandler import MultipartPostHandler as mph
from py3ct import py3createtorrent as ct

relpath = ct.relpath
cookie = req.build_opener(req.HTTPCookieProcessor(),mph.MultipartPostHandler)
req.install_opener(cookie)

curdir = os.path.split(sys.argv[0])[0]
configfile = os.path.join(curdir,'config.txt')
execfile(configfile)                  ## loading config settings

##  ----    below this is what should be in a config.txt    ----

##USERNAME = 'username'    
##PASSWORD = 'password'
##default_folder = '/'      ## using forward slashes
##flac_path = os.path.join('codecs','flac')   ## can be either relative or not
##lame_path = os.path.join('codecs','lame')
##
##verbose = True      ## should it print out status and stuff or just be quiet

##  ----    end config.txt                                  ----

flac_path = os.path.join(curdir,flac_path)
lame_path = os.path.join(curdir,lame_path)

tk = None

def pprint(*things):
    if verbose:
        for thing in things:
            print(thing)

def select_folder(startfolder=default_folder,msg=None):
    global tk
    if not tk:
        tk = Tkinter.Tk()
        tk.withdraw()
    if not msg:
        msg = 'Sup. Select dat folder.'
    folder = tkFileDialog.askdirectory(
        parent=tk,initialdir=default_folder,title=msg)
    pprint('Folder selected...')
    return folder

def create_torrent(folder,tracker):
    ct.main(folder,tracker)
##    torrent_filename = '%s/%s.torrent' % (folder, folder.split('/')[-1])
    torrent_filename = '%s.torrent' % (os.path.split(folder)[1])
    pprint('Torrent created...')
    return torrent_filename

def get_auth():
    ## could also get the tracker passkey from this if you wanted
    ## it's just 'passkey=' instead of 'authkey=' down there
    try:
        login = urllib.urlencode({'username':USERNAME, 'password':PASSWORD})   
        data = req.urlopen('https://what.cd/login.php', login).read()
        authkey = data.split('authkey=')[1].split('"')[0]
        if authkey:
            pprint('Authed...')
            return authkey
        else:
            pprint('Auth failed.')
            return False
    except:
        pprint('Auth failed.')
        return False

def get_tracker_url(url='https://what.cd/upload.php'):
    data = req.urlopen(url).read()
    tracker_url = '%s%s' % ('http://tracker.what.cd',
                        data.split('http://tracker.what.cd')[1].split('"')[0]) 
    pprint('Got tracker url...')
    return tracker_url

def to_imgur(filename):
    imgurl = 'http://api.imgur.com/2/upload.json'
    key = '0ce055776a9bf40f79bad64ae3c2900e'
    data = req.urlopen(imgurl,data={'image':open(filename,'rb'),
                                    'key':key}).read()
    url = data.split('"original":"')[1].split('"')[0].replace('\\','')
    pprint('Cover art uploaded...')
    return url

def get_tags(folder,addformat=False):
    flacs = []
    mp3s = []
    images = []
    tracks = []
    for root, dirnames, filenames in os.walk(folder):
        for filename in [f for f in filenames if f.endswith(('.flac'))]:
            flacs.append(os.path.join(root, filename))
        for filename in [f for f in filenames if f.endswith('.mp3')]:
            mp3s.append(os.path.join(root, filename))
        for filename in [f for f in filenames if f.endswith('cover.jpg')]:
            images.append(os.path.join(root, filename))
    tracks = []
    tracks_tags = []
    total_length = 0
    if flacs:
        format = 'FLAC'
        flacfile = flac.FLAC(flacs[0])
        if flacfile.info.bits_per_sample == 16:
            bitrate = 'Lossless'
        elif flacfile.info.bits_per_sample == 24:
            bitrate = '24bit Lossless'
        ## past here is irrelevant if addformat == True
        artist = flacfile['artist'][0]
        album = flacfile['album'][0]
        year = flacfile['date'][0]
        for filename in flacs:
            flacfile = flac.FLAC(filename)
            track_num = int(flacfile['tracknumber'][0])
            track_title = flacfile['title'][0]
            length = int(flacfile.info.length)
            tracks.append((track_num, track_title, length))
            total_length += length
            tracks_tags.append(flacfile.tags)
    elif mp3s:
        format = 'MP3'
        mp3file = mp3.MP3(mp3s[0])
        if mp3file.info.VBR_preset:     ## only for LAME V*
            bitrate = mp3file.info.VBR_preset
        else:
            bitrate = mp3file.info.bitrate / 1000
        ## past here is irrelevant if addformat == True
        artist = str(mp3file['TPE1'])
        album = str(mp3file['TALB'])
        year = str(mp3file['TDRC'])
        for filename in mp3s:
            mp3file = mp3.MP3(filename)
            track_num = int(mp3file['TRCK'].text[0])
            track_title = str(mp3file['TIT2'].text[0])
            length = int(mp3file.info.length)
            tracks.append((track_num, track_title, length))
            total_length += length
    else:
        raise Exception('No music files found!')
    tracks.sort()
    if images and not addformat:
        image = to_imgur(images[0])
    else:
        image = ''
    pprint('Tags extracted from files...')
    return (artist,album,year,format,bitrate,image,tracks,total_length)

def make_tracklist(tracks,total_length=None):
    ## tracks is of form (track_num, track_title, length (int))
    desc = ''
    if not total_length:
        total_length = sum([track[2] for track in tracks])
    secs = total_length % 60
    mins = (total_length - secs) / 60
    secs = str(secs).rjust(2,'0')
    for track in tracks:
        t_secs = track[2] % 60
        t_mins = (track[2] - t_secs) / 60
        t_secs = str(t_secs).rjust(2,'0')
        desc = '%s%s. %s (%s:%s)\n' % (desc,track[0],track[1],t_mins,t_secs)
    desc = '%s\nTotal length: %s:%s' % (desc,mins,secs)
    return desc

def get_extra_data(addformat=False):
    if addformat:
        release_type = ''
        genre_tags = ''
        desc = ''
    else:
        release_type = raw_input('''Release type? (number)\n
<option value='1'> Album </option>
<option value='3'> Soundtrack </option>
<option value='5'> EP </option>
<option value='6'> Anthology </option>
<option value='7'> Compilation </option>
<option value='8'> DJ Mix </option>
<option value='9'> Single </option>
<option value='11'> Live album </option>
<option value='13'> Remix </option>
<option value='14'> Bootleg </option>
<option value='15'> Interview </option>
<option value='16'> Mixtape </option>
<option value='21'> Unknown </option>\n\n>>> ''')
        genre_tags = raw_input('Tags (comma-separated):\n\n>>> ')
        desc = raw_input('Description (in addition to the auto-generated\
track listing) (optional):\n\n>>> ')

    media = raw_input('''Media?\n
    CD
    DVD
    Vinyl
    Soundboard
    SACD
    DAT
    Cassette
    WEB
    Blu-ray\n\n>>> ''')
    return (release_type,media,genre_tags,desc)


def create_data(torrent,tags,extra_data,authkey):
    data = {}
    artist = tags[0]
    album = tags[1]
    year = tags[2]
    format = tags[3]
    bitrate = str(tags[4])
    image = tags[5]
    if not bitrate in ('320','256','192','Lossless','24bit Lossless','V0','V2'):
        bitrate = 'Other'
        other_bitrate = str(tags[4])
        data['vbr'] = '1'
    if bitrate == 'V0':
        bitrate = 'V0 (VBR)'
    if bitrate == 'V2':
        bitrate = 'V2 (VBR)'
    release_type = extra_data[0]
    media = extra_data[1]
    genre_tags = extra_data[2]
    auto_tracklist = make_tracklist(tags[6],tags[7])
    desc = '%s\n\n%s' % (auto_tracklist,extra_data[3])
    
    data = {'file_input': open(torrent,'rb'),
            'submit':   'true',
            'type': '0', ## music
            'artists[]':   artist,
            'importance[]': '1', ## main artist rather than guest etc.
            'title':    album,
            'year':     year,
            'format':   format,
            'bitrate':  bitrate,
            'image':    image,
            'releasetype':  release_type,
            'media':    media,
            'tags':     genre_tags,
            'album_desc':     desc,
            'auth':     authkey
            }
    pprint('Data created...')
    ## pprint(data)
    return data

def submit_form(data):
    response = req.urlopen('https://what.cd/upload.php',data).read()
    if '<title>Upload :: What.CD</title>' in response:
        pprint('Upload failed.')
        log = open('response.html','w')
        log.write(response)
        log.close()
        return False
    else:
        findit = 'torrents.php?action=editgroup&amp;groupid='
        groupid = response.split(findit)[1].split('"')[0]
        pprint('Upload success.')
        return groupid


def create_data_addformat(torrent,tags,extra_data,authkey,groupid):
    data = {}
    format = tags[3]
    bitrate = str(tags[4])
    print(bitrate)
    if not bitrate in ('320','256','192','Lossless','24bit Lossless','V0','V2'):
        bitrate = 'Other'
        other_bitrate = str(tags[4])
        data['vbr'] = '1'
    if bitrate == 'V0':
        bitrate = 'V0 (VBR)'
    if bitrate == 'V2':
        bitrate = 'V2 (VBR)'
    media = extra_data[1]
    
    data = {'file_input': open(torrent,'rb'),
            'submit':   'true',
            'type': '0', ## music
            'format':   format,
            'bitrate':  bitrate,
            'media':    media,
            'groupid'   :   groupid,
            'auth':     authkey
            }
    pprint('Data created...')
    ## pprint(data)
    return data

def submit_form_addformat(data,groupid):
    response = req.urlopen(
        'https://what.cd/upload.php?groupid=%s' % groupid,data).read()
    if '<title>Upload :: What.CD</title>' in response:
        pprint('Upload failed.')
        log = open('response.html','w')
        log.write(response)
        log.close()
        return False
    else:
        findit = 'torrents.php?action=editgroup&amp;groupid='
        groupid = response.split(findit)[1].split('"')[0]
        pprint('Upload success.')
        return groupid

    

def run(infolder=None,reuse_extras=False,argv=None):
    if not infolder:
        folder = select_folder()
    else:
        folder = infolder
    authkey = get_auth()
    tracker_url = get_tracker_url()
    torrent = create_torrent(folder, tracker_url)
    tags = get_tags(folder)
    extras = get_extra_data()
    data = create_data(torrent, tags, extras, authkey)
##    return(data)               ## for debugging
    response = submit_form(data)
    if response:
        print('Torrent uploaded successfully!\n')
        if reuse_extras:
            return response, extras
        else:
            return response         # this is groupid
    else:
        print('Torrent upload failed :(\n')

def run_addformat(folder=None,groupid=None,extras=None):
    if not folder:
        folder = select_folder()
    authkey = get_auth()
    tracker_url = get_tracker_url()
    torrent = create_torrent(folder, tracker_url)
    tags = get_tags(folder,addformat=True)
    if not extras:
        extras = get_extra_data(addformat=True)
    data = create_data_addformat(torrent, tags, extras, authkey, groupid)
##    return(data)               ## for debugging
    response = submit_form(data)
    if response:
        print('Torrent uploaded successfully!\n')
    else:
        print('Torrent upload failed :(\n')

## Code from here down is to deal with converting, and stuff

def get_number_of_processors():
    try:
        res = int(os.environ['NUMBER_OF_PROCESSORS'])
        if res > 0:
            return res
    except (KeyError, ValueError):
        pass
    try:
        res = open('/proc/cpuinfo').read().count('processor\t:')
        if res > 0:
            return res
    except IOError:
        pass
    raise Exception('cant determine number of processors!')

num_proc = get_number_of_processors()

actives = threading.activeCount
default_actives = actives()

def get_threads_number():
    '''returns the number of processors, plus the number of currently running
threads.'''
    current_threads = actives()   #why camel case...
    return current_threads + num_proc

threads_number = get_threads_number()

def filecopy(file_in,file_out):
    f_in = open(file_in,'rb')
    f_out = open(file_out,'wb')
    for line in f_in.readlines():
        f_out.write(line)
    f_in.close()
    f_out.close()

def make_lame_metadata(artist,title=None,album=None,year=None,track_num=None):
    if not isinstance(artist,str):
        title = artist[1]
        album = artist[2]
        year = artist[3]
        track_num = artist[4]
        artist = artist[0]
    string = '--ta "%s" --tt "%s" --tl "%s" --ty "%s" --tn "%s"' % (
        artist,title,album,year,track_num)
    return string
    

def make_lame_params(bitrate):
    if bitrate == '320':
        return '-b 320'
    elif bitrate == 'V0':
        return '-V 0'
    elif bitrate == 'V2':
        return '-V 2'
    else:
        raise Exception('bitrate was not "320", "V0", or "V2"')

def flac_to_mp3(file_in,file_out,lame_params,lame_metadata):
##    pprint(file_in)
##    pprint(file_out)
    decoder = os.popen('%s -d -s -c "%s"' % (
        flac_path, file_in), 'rb', -1)
##    pprint((lame_path, lame_params, file_out, lame_metadata))
    encoder = os.popen(u'%s --silent %s - -o "%s.mp3" %s' % (
        lame_path, lame_params, file_out, lame_metadata) , 'wb', -1)
    for line in decoder.readlines():
        encoder.write(line)
    decoder.flush()
    decoder.close()
    encoder.flush()
    encoder.close()

def convert_perfect_three(folder=None,outfolder=None):
    #folders are created within outfolder for each bitrate
    #e.g., if outfolder = /files/, three folders would be created
    #/files/whatever [V2] , /files/whatever [V0] , /files/whatever [320]
    if not folder:
        folder = select_folder(msg='Select infolder')
    if not outfolder:
        outfolder = select_folder(msg='Select outfolder')
    #get files
    flacs = []      #contains tuples: (abspath, rel_path, filename)
    logs_cues = []  #same. we don't copy these
    etc = []        #same. we do copy these
    for root, dirs, filenames in os.walk(folder):
        for filename in filenames:
            abspath = os.path.join(root,filename)
            if filename.endswith('.flac'):
                flacs.append((abspath,relpath(abspath,folder),filename))
            elif filename.endswith('.log') or filename.endswith('.cue'):
                logs_cues.append((abspath,relpath(abspath,folder),filename))
            else:
                etc.append((abspath,relpath(abspath,folder),filename))
    #get metadata
    files = []          ## tuples: ((abspath,rel_path,filename),metadata)
    for f in flacs:
        flacfile = flac.FLAC(f[0])
        artist = flacfile['artist'][0].encode('utf-8')
        title = flacfile['title'][0].encode('utf-8')
        album = flacfile['album'][0].encode('utf-8')
        year = flacfile['date'][0].encode('utf-8')
        track_num = flacfile['tracknumber'][0].encode('utf-8')
        metadata = (artist,title,album,year,track_num)
        files.append((f,metadata))
    for f in flacs:
        reldir = os.path.split(f[1])[0]
        print(reldir)
        if not os.path.isdir(reldir):
            os.makedirs(reldir)
    #prepare the different convert bathes
    converts = []
    return_dirs = []
    for bitrate in ('V0','V2','320'):
        #using values of 'artist' and 'album' left over from the above for loop
        makedir = os.path.normpath(
            os.path.join(outfolder,'%s - %s (%s) [%s]' % (
                                    artist,album,year,bitrate)))
        return_dirs.append(makedir)
        converts.append([(f[0][0],
                          os.path.join(makedir,f[0][1][:-5]), #-5 = '.flac'
                          make_lame_params(bitrate),
                          make_lame_metadata(f[1])) for f in files])
        
        try:
            os.mkdir(makedir)
        except OSError:
            pass        #folder already exists - that's fine
        #copy over 'etc' (cover art, anything else)
        for f in etc:
            filecopy(f[0],os.path.join(makedir,f[1]))
        #make subdirectories, if any exist
        for convert in converts:
            for job in convert:
                reldir = os.path.split(job[1])[0]
                if not os.path.isdir(reldir):
                    os.makedirs(reldir)
##    return converts                   ##for debugging
    convert_id = 0
    for convert in converts:
        pprint('converting to %s' % return_dirs[convert_id])
        convert_id += 1
        jobid = 0
        for job in convert:
            jobid += 1
            while actives() == threads_number:
                time.sleep(1)
            pprint('%s of %s' % (jobid,len(convert)))
            threading.Thread(
                target = flac_to_mp3,
                args = (job[0],job[1],job[2],job[3])).start()
    #wait for all threads to finish
    while actives() != default_actives:
        time.sleep(1)
    return return_dirs

def perfect_three_and_upload(infolder=None,outfolder=None):
    if not infolder:
        infolder = select_folder()
    if not outfolder:
        outfolder = select_folder()
    converted = convert_perfect_three(infolder,outfolder)
    print(converted)
    time.sleep(10)
    groupid,extras = run(infolder,reuse_extras=True)    # da flac = main upload
    for f in converted:
        run_addformat(f,groupid,extras=extras)
    
if __name__ == "__main__":
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = None
##    print(folder)
##    print(sys.argv)           # for debugging
##    time.sleep(4)
    try:
        globals()[main_action](infolder=folder)
    except Exception, error:
        print(error)        ## for debugging - leave this active so user can see
        time.sleep(10)
##    run()    
