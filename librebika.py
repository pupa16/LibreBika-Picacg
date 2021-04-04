'''
LibreBika: An Open-source Third-party Client of PicaComic.
Copyright © 2021 by Stanley Jian <jianstanley@outlook.com>

This file is a part of LibreBika.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License Version 2 as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

@license GPL-2.0 <http://spdx.org/licenses/GPL-2.0>
'''

import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk as gtk
from time import time_ns
start_time=time_ns()

'''
class class_logger():
    def __init__(self,name='LibreBika'):
        self.name=name
        self.writer=open(f'log_{int(time_ns()/1000000)}.txt','w')
    def log(self,mode,string):
        self.writer.write(f'[{mode}/{int(time_ns()/1000000)}] {string}\n')
    def info(self,string):
        self.log('INFO',string)
    def warn(self,string):
        self.log('WARN',string)
    def error(self,string):
        self.log('ERROR',string)
    def close(self):
        self.writer.close()
logger=class_logger()
'''

from time import sleep
import os
import connections
import uis

GTK_VERSION=f'{gtk.MAJOR_VERSION}.{gtk.MINOR_VERSION}.{gtk.MICRO_VERSION}'
LB_DIRECTORY='librebika/'
LB_NAME = 'LibreBika'
LB_VERSION='BETA'

requires_login=True
token=None
if not os.path.exists(LB_DIRECTORY):
    os.mkdir(LB_DIRECTORY)
if os.path.exists(LB_DIRECTORY+'token'):
    with open(LB_DIRECTORY+'token','r') as f:
        token=f.read().replace('\n','')
        ret=connections.validate_token(token)
        if ret==None:
            print('LB EARLY: validate indicate offline') #OFFLINE
            requires_login=False
        elif ret:
            requires_login=False
        else:
            print('LB EARLY: validate expired')
    if requires_login:
        os.remove(LB_DIRECTORY+'token')
if requires_login:
    login_window=uis.LoginWindow()
    login_window.connect('destroy',gtk.main_quit)
    login_window.show_all()
    gtk.main()
    try:
        token=login_window.acquired_token
    except:
        print('LB EARLY: login failure')  #OFFLINE
    with open(LB_DIRECTORY+'token','w') as f:
        f.write(token+'\n')

librebika_window=uis.LibreBikaWindow('LibreBika '+LB_VERSION,token)
librebika_window.show_all()
gtk.main()
