#!/usr/bin/python3

from logging.config import dictConfig
from datetime       import datetime, timedelta
from requests       import request as r
from pathlib        import Path
from inspect        import getsourcefile
from sys            import exit, argv
import logging
import json
import yaml

'''
    Server config must be saved in the same directory(folder) as this script and with the name \'server_config.yaml\'
    Each playlist configuration must also be in the playlists directory saved as <playlist_name>.yml or <playlist_name>.yaml
    Each show can be listed with an optional airtime in 24HR format (0:00-23:59)
'''
debug = False
if len(argv) > 1 and argv[1].lower() == 'debug':
    debug = True

source = Path(getsourcefile(lambda:0))
if source.is_file():
    appDir = source.parent
playlistDir = appDir.joinpath('playlists')
server_config = appDir.joinpath('server_config.yaml')
log_config = appDir.joinpath('log.yaml')
log_file = appDir.joinpath('log')
lf = open(log_file,'a+')
lf.close()

with open(log_config,'r') as _loader:
    log_config = yaml.safe_load(_loader)
log_config['handlers']['fh']['filename'] = log_file
if debug:
    log_config['loggers'][__name__]['level'] = 'DEBUG'
dictConfig(log_config)
log = logging.getLogger(__name__)
log.info(f'Debugging: {debug}')

with open(server_config,'r')as _loader:
    config = yaml.safe_load(_loader)

class server:
    
    def __init__(self,host:str,headers:dict,port:str=None,playlistid:str=None,userid:str=None):
        self.url = f'{host}:{port}' if port is not None else host
        self.headers = headers
        self._playlistid = playlistid
        self.userid = userid


    def _get(self,endpoint:str,params:dict=False):
        _url = f'{self.url}/{endpoint}'
        log.debug(f'Sending \'GET\' request to {_url} with\nparams:\n{params}')
        _response = r('GET',_url,headers=self.headers,params=params,data={}) if params else r('GET',_url,headers=self.headers,data={})
        _json = json.loads(_response.text)
        log.debug(f'{_response} :{_response.status_code}')
        return _json

    def _post(self,endpoint:str,params:dict=None):
        _url = f'{self.url}/{endpoint}'
        log.debug(f'Sending \'POST\' request to {_url} with\nparams:\n{params}')
        _response = r('POST',_url,headers=self.headers,params=params,data={}) if params else r('POST',_url,headers=self.headers,data={})
        log.debug(f'{_response} :{_response.status_code}')
        return _response

    def _delete(self,endpoint:str,params:dict=None):
        _url = f'{self.url}/{endpoint}'
        log.debug(f'Sending \'DELETE\' request to {_url} with\nparams:\n{params}')
        _response = r('DELETE',_url,headers=self.headers,params=params,data={}) if params else r('DELETE',_url,headers=self.headers,data={})
        log.debug(f'{_response} :{_response.status_code}')

    def users(self):
        _endpoint = 'Users'
        log.debug(__name__)
        _output = self.get(_endpoint)
        log.debug(_output)
        return _output

    def getPlaylists(self):
        _endpoint = 'Items'
        _params = {"UserId":self.userid,'format':'json','Recursive': True,'IncludeItemTypes':'Playlist'}
        log.debug(__name__)
        _output = self._get(_endpoint,_params)
        return _output

    def createPlaylist(self,name,mediatype):
        _endpoint = 'Playlists'
        _params = {'Name':name,'MediaType':mediatype,'UserId':self.userid}
        _output = self._post(_endpoint,_params)
        _json = json.loads(_output.text)
        log.debug(__name__)
        self._playlistid = _json['Id']
        log.info(f'Created new playlist: {name} - {self._playlistid}')


    def addToPlaylist(self,playlist):
        log.debug(__name__)
        _endpoint = f'Playlists/{self._playlistid}/Items'
        '''
            How many playlist items to send per request.
            In testing, the request would fail if much larger.
        '''
        max_send = 200
        _items = len(playlist)
        _num_to_add = _items if _items < max_send else max_send
        while True:
            _tmp = []
            log.info(f'{_items} items left to add to playlist.')
            log.info(f'Sending {_num_to_add} items to add to playlist.')
            for x in playlist[:_num_to_add]:
                _tmp.append(x)
            for i in range(_num_to_add):
                playlist.pop(0)
            _items = len(playlist)
            _ids = ','.join(_tmp)
            _params = {'Ids':_ids}
            self._post(_endpoint,_params)
            if _items < _num_to_add:
                _num_to_add = _items
            if _items <= 0:
                log.info('Complete.')
                break

    def removeFromPlaylist(self,to_remove:list):
        log.debug(__name__)
        _endpoint = f'Playlists/{self._playlistid}/Items'
        '''
            How many playlist items to send per request.
            In testing, the request would fail if much larger.
        '''
        max_send = 200
        _items = len(to_remove)
        _num_to_remove = _items if _items < max_send else max_send
        while True:
            _tmp = []
            log.info(f'{_items} items remaining to remove.')
            log.info(f'Sending {_num_to_remove} items to remove.')
            for x in to_remove[:_num_to_remove]:
                _tmp.append(x)
            for i in range(_num_to_remove):
                to_remove.pop(0)
            _items = len(to_remove)
            _ids = ','.join(_tmp)
            _params = {'EntryIds':_ids}
            self._delete(_endpoint,_params)
            if _items < _num_to_remove:
                _num_to_remove = _items
            if _items <= 0:
                log.info('Complete.')
                break



        

    def getPlaylist(self):
        _endpoint = f'Playlists/{self._playlistid}/Items'
        _params = {'UserId':self.userid,'EnableImages':False}
        log.debug(__name__)
        return self._get(_endpoint,_params)['Items']

    def setPlaylistid(self,_id:str):
        log.debug(__name__)
        self._playlistid = _id
        return True

    def getPlaylistId(self):
        log.debug(__name__)
        return self._playlistid

    def getShow(self,show):
        _params = {'SearchTerm':show,'UserId':self.userid}
        _endpoint = 'Search/Hints'
        log.debug(__name__)
        _data = self._get(_endpoint,_params)
        _data = _data['SearchHints']
        for _item in _data:
            _name = _item['Name']
            if show == _name:
                _id = _item['Id']
                return _id

    def getEpisodes(self,showid,):
        _params = {'SortBy':'PremiereDate','SortOrder':'Ascending','UserId':self.userid}
        _endpoint = f'Shows/{showid}/Episodes'
        log.debug(__name__)
        _data = self._get(_endpoint,_params)
        _data = _data['Items']
        return _data

host             = config['host']
port             = config.get('port',None)
headers          = {'Content-Type': 'application/json','X-Emby-Token':config['token']}
playlist_configs = []
def main(file:str,playlist_config:dict):
    global config
    userName        = playlist_config['User']
    playlistname    = playlist_config['Name']
    mediatype       = playlist_config['MediaType']
    shows           = playlist_config['Shows']
    playlistid      = playlist_config.get('Id',None)
    to_remove       = []
    playlist        = []
    sorted_playlist = []

    log.debug(f'userName: {userName}')
    log.debug(f'playlistname: {playlistname}')
    log.debug(f'mediatype: {mediatype}')
    log.debug(f'shows: {shows}')
    log.debug(f'playlistid: {playlistid}')
    log.debug(f'to_remove: {to_remove}')
    log.debug(f'playlist: {playlist}')
    log.debug(f'sorted_playlist: {sorted_playlist}')

    userid          = config['users'].get(userName,False)
    playlist_exists = False

    jf = server(host,headers,port,playlistid,userid)

    ''' 
        check if userid exists in config and adds if not
        this limits API Calls increasing speed of subsequent runs
    '''
    if not userid:
        users = jf.users()
        for user in users:
            _name = user.get('Name',False)
            if _name:
                log.info(_name)
                if _name == userName:
                    jf.userid = user['Id']
                    config['users'].update({userName:user['Id']})
                    with open(server_config,'w') as _writer:
                        yaml.dump(config,_writer)
                    break
            else:
                log.error(f'User, {userName}, does not exist on server. Please check spelling and case.')
                exit()

    # check if playlist exists
    if not playlistid:
        log.info('No playlist id in config, checking server')
        _playlists = jf.getPlaylists()
        _playlists = _playlists['Items']
        for _playlist in _playlists:
            _playlistname = _playlist.get('Name',False)
            log.info(f'checking {_playlistname}')
            if _playlistname:
                if  playlistname == _playlistname:
                    log.info('playlist exists')
                    playlist_exists = jf.setPlaylistid(_playlist['Id'])
                    break
            else:
                log.warn('No existing playlists for user on server')
                log.info('No existing playlists for user on server')
    else:
        playlist_exists = True

    if playlist_exists:
        existing_playlist = jf.getPlaylist()
        playlist_items = dict((i['Id'], i['PlaylistItemId']) for i in existing_playlist)
        log.debug(playlist_items)
    else:
        jf.createPlaylist(playlistname,mediatype)
    playlistid = jf.getPlaylistId()
    playlist_config['Id'] = playlistid
    log.debug(playlist_config)
    log.info(f'writing playlistid to file: {file}')
    with open(file, 'w') as f:
        yaml.dump(playlist_config,f)

        
    for _show in shows:
        _episode_count = 0
        _showname = _show['name']
        _showtime = _show.get('time',False)
        if _showtime:
            _showtime_split = _showtime.split(':')
            _showtime_hour = int(_showtime_split[0])
            _showtime_min = int(_showtime_split[1])
        log.info(f'fetchin showId for {_showname}')
        _showid = jf.getShow(_showname)
        log.debug(f'showId: {_showid}')
        log.info(f'Fetching episodes:')
        _episodes = jf.getEpisodes(_showid)
        log.debug(_episodes)
        for _episode in _episodes:
            _status_text = ''
            _episode_name = _episode['Name']
            log.debug(_episode_name)
            _episode_id = _episode['Id']
            log.debug(_episode_id)
            _episode_played = _episode['UserData']['Played']
            log.debug(_episode_played)
            log.debug(f'Checking play status for {_showname}')
            if _episode_played:
                if playlist_exists:
                    if _episode_id in playlist_items:
                        to_remove.append(playlist_items[_episode_id])
                        _status_text = 'Removing from playlist.'
                        log.info(_status_text)
                    else:
                        _status_text = 'Skipping.'
                log.debug(f'{_episode_name} is marked as watched.{_status_text}')
                continue
            else:
                _airdate = _episode['PremiereDate']
                log.debug(_airdate)
                _airdate = datetime.strptime(_airdate,'%Y-%m-%dT%H:%M:%S.%f0Z')
                log.debug(_airdate)
                if _showtime:
                    log.debug(f'adding show time: {_showtime}')
                    _delta = timedelta(hours=_showtime_hour,minutes=_showtime_min)
                    _airdate += _delta
                    log.debug(_airdate)
                log.debug(f'{_episode_name}: {_episode_id} - {_airdate}')
                _timestamp = _airdate.timestamp()
                playlist.append({'id':_episode_id,'aired':_timestamp})
                _episode_count+=1
        log.info(f'Added {_episode_count} episodes to list.')
    
    log.info(f'Sorting {len(playlist)} items.')
    playlist.sort(key = lambda x:x['aired'])
    for media in playlist:
        sorted_playlist.append(media['id'])
    if len(to_remove) > 0:
        log.debug(f'{len(to_remove)} watched items found in playlist, removing.')
        jf.removeFromPlaylist(to_remove)
    jf.addToPlaylist(sorted_playlist)


for file in playlistDir.glob('*.yml'):
    playlist_configs.append(file)
for file in playlistDir.glob('*.yaml'):
    playlist_configs.append(file)
for file in playlist_configs:
    log.debug(f'Reading {file.name}')
    with open(file,'r') as _loader:
        playlist_config = yaml.safe_load(_loader)
    log.debug(playlist_config)
    if not playlist_config['Name'] == 'Template':
        main(file,playlist_config)