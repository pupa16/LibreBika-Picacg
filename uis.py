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
from gi.repository import Gdk as gdk
from gi.repository import GdkPixbuf

import connections
import re
import configparser
import os
import threading
from time import sleep

BK_CATEGORIES=['嗶咔汉化','全彩','长篇','同人','短篇','圆神领域','碧蓝幻想','CG杂图','英语','生肉','纯爱','百合','耽美','伪娘','后宫','扶他','单行本','姐姐','妹妹','SM','性转','恋足','人妻','NTR','强暴','非人类','舰队','Love Live','刀剑神域','Fate','东方','WEBTOON','一般漫画','欧美','Cosplay','重口']
BK_CATEGORIES_RAW=['嗶咔漢化','全彩','長篇','同人','短篇','圓神領域','碧藍幻想','CG雜圖','英語ENG','生肉','純愛','百合花園','耽美花園','偽娘哲學','後宮閃光','扶他樂園','單行本','姐姐系','妹妹系','SM','性轉換','足の恋','人妻','NTR','強暴','非人類','艦隊收藏','LoveLive','SAO刀劍神域','Fate','東方','WEBTOON','禁書目錄','歐美','Cosplay','重口地帶']
BK_QUALITIES={'l':'low','m':'medium','h':'high','o':'original'}
BK_SORT={'d':'dd','t':'da','h':'ld','p':'vd'}

username_regex=re.compile('[^\da-z\._]')
config_service_entries=['quality','channel']
config_search_entries=['includeoriginaltext','includegay','includenonadult','includegore']
config_search_indices={'includeoriginaltext':32,'includegay':12,'includenonadult':9,'includegore':35}

def g_set_margins(widget,top=0,right=0,bottom=0,left=0):
    widget.set_margin_start(left)
    widget.set_margin_end(right)
    widget.set_margin_top(top)
    widget.set_margin_bottom(bottom)

def g_menu_item_with_callback(label,function):
    mi=gtk.MenuItem.new_with_label(label)
    mi.connect('activate',function)
    return mi

def g_button_with_callback(label,function):
    b=gtk.Button.new_with_label(label)
    b.connect('clicked',function)
    return b

def g_combobox_with_entries(entries):
    ct=gtk.ComboBoxText()
    for i in entries:
        ct.append(i,entries[i])
    return ct

def g_label_bold(label):
    l=gtk.Label('')
    l.set_markup('<b>'+label+'</b>')
    l.set_valign(gtk.Align.START)
    return l

def g_label_set_wrap(length_per_line):
    widget=gtk.Label(None)
    widget.set_line_wrap(True)
    widget.set_line_wrap_mode(gtk.WrapMode.CHAR)
    widget.set_max_width_chars(length_per_line)
    return widget

class LibreBikaDownloadManager(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.pending=[]
        self.should_die=False
    def run(self):
        print('DOWNLOADER IS RUNNING')
        while not self.should_die:
            if len(self.pending)==0:
                #print('Pending stack size = 0, next check in 1 sec')
                sleep(1)
            else:
                print('Pending stack size = '+str(len(self.pending)))
                target=self.pending[0]
                success=0
                failure=0
                print('  Found work target size = '+str(len(target[1]))+', id = '+target[0]+', order = '+str(target[2]))
                if not os.path.exists('librebika'):
                    os.mkdir('librebika')
                if not os.path.exists('librebika/local'):
                    os.mkdir('librebika/local')
                if not os.path.exists('librebika/local/'+target[0]):
                    os.mkdir('librebika/local/'+target[0])
                if not os.path.exists('librebika/local/'+target[0]+'/'+str(target[2])):
                    os.mkdir('librebika/local/'+target[0]+'/'+str(target[2]))
                for e in target[1]:
                    res=connections.downloader(e[1],'librebika/local/'+target[0]+'/'+str(target[2])+'/'+e[0])
                    if res==None:
                        print('    Download '+e[0]+' : NETWORK ERROR, url = '+e[1])
                        failure+=1
                    elif res:
                        print('    Download '+e[0]+' : SUCCESS, url = '+e[1])
                        success+=1
                    elif not res:
                        print('    Download '+e[0]+' : SERVER ERROR, url = '+e[1])
                        failure+=1
                print('  Finished, success = '+str(success)+', failure = '+str(failure))
                self.pending.remove(target)
        print('DOWNLOADER KILLED')

class LibreBikaWindow(gtk.Window):
    def __init__(self,title,token):
        gtk.Window.__init__(self,title=title)
        self.set_icon_from_file('librebika_logo.png')

        self.load_config()
        self.token=token
        self.user_profile=None
        self.update_user_profile()
        self.downloader=LibreBikaDownloadManager()
        self.downloader.start()

        self.layout=gtk.VBox(False,0)
        self.add(self.layout)

        self.menu=gtk.MenuBar()
        self.menu.set_valign(gtk.Align.START)
        self.menu_user=gtk.MenuItem.new_with_label('用户')
        self.menu_program=gtk.MenuItem.new_with_label('程序')
        self.menu_about=gtk.MenuItem.new_with_label('关于')
        self.menu_user_sub=gtk.Menu()
        self.menu_user_sub.attach(gtk.MenuItem.new_with_label('资料'),0,1,0,1)
        self.menu_user_sub.attach(g_menu_item_with_callback('注销',self.pre_logout),0,1,1,2)
        self.menu_user.set_submenu(self.menu_user_sub)
        self.menu_program_sub=gtk.Menu()
        self.menu_program_sub.attach(g_menu_item_with_callback('设置',self.create_settings_window),0,1,0,1)
        self.menu_program.set_submenu(self.menu_program_sub)
        self.menu_about_sub=gtk.Menu()
        self.menu_about_sub.attach(gtk.MenuItem.new_with_label('捐赠'),0,1,0,1)
        self.menu_about_sub.attach(g_menu_item_with_callback('许可',self.create_about_license_window),0,1,1,2)
        self.menu_about_sub.attach(gtk.MenuItem.new_with_label('信息'),0,1,2,3)
        self.menu_about_sub.attach(gtk.MenuItem.new_with_label('关于'),0,1,3,4)
        self.menu_about.set_submenu(self.menu_about_sub)
        self.menu.add(self.menu_user)
        self.menu.add(self.menu_program)
        self.menu.add(self.menu_about)
        self.layout.pack_start(self.menu,False,False,0)

        self.quick=gtk.HBox(True,0)
        self.quick.set_valign(gtk.Align.START)
        self.task_box=gtk.Box()
        g_set_margins(self.task_box,left=20)
        self.task_add=gtk.Button.new_with_label('+')
        self.task_del=gtk.Button.new_with_label('-')
        self.task_view=g_combobox_with_entries({'s':'搜索','f':'收藏','h':'历史','l':'下载'})
        self.task_view.props.active_id='s'
        g_set_margins(self.task_add,20,0,20,0)
        g_set_margins(self.task_del,20,0,20,20)
        g_set_margins(self.task_view,20,0,20,20)
        self.task_box.add(self.task_add)
        self.task_box.add(self.task_del)
        self.task_box.add(self.task_view)
        self.stamp_box=gtk.Box()
        self.stamp_box.set_halign(gtk.Align.CENTER)
        self.stamp=g_button_with_callback('签到不可用' if self.user_profile==None else ('已签到' if self.user_profile['isPunched'] else '签到'),self.perform_stamp)
        self.stamp.props.sensitive=False
        if self.user_profile!=None and not self.user_profile['isPunched']:
            self.stamp.props.sensitive=True
        self.stamp.set_halign(gtk.Align.CENTER)
        self.stamp.set_size_request(150,-1)
        g_set_margins(self.stamp,20,0,20,0)
        self.stamp_box.add(self.stamp)
        self.quick.add(self.task_box)
        self.quick.add(self.stamp_box)
        self.layout.pack_start(self.quick,False,False,0)

        self.task_data=gtk.ListStore(str,str,str,str)
        self.element_data=gtk.ListStore(str)
        self.chapter_data=gtk.ListStore(str)

        self.task_data_core=[]
        self.task_data_entries=[]

        self.explorer=gtk.HBox(True,20)
        self.explorer.fill=True
        g_set_margins(self.explorer,20,20,20,20)
        self.task_list_box=gtk.VBox(False,20)
        self.task_list_parent=gtk.ScrolledWindow()
        self.task_list_box.add(self.task_list_parent)
        self.element_list_box=gtk.VBox(False,20)
        self.element_list_parent=gtk.ScrolledWindow()
        self.task_list=gtk.TreeView()
        self.task_list.connect('row-activated',self.task_list_change)
        self.element_list=gtk.TreeView()
        self.element_list.connect('row-activated',self.element_list_change)
        self.task_list_parent.add(self.task_list)
        self.element_list_parent.add(self.element_list)
        self.element_list_cache_box=gtk.HBox(False,20)
        self.element_list_cache_box.set_halign(gtk.Align.CENTER)
        self.element_list_cache_box.add(gtk.Label.new('已访问：'))
        self.element_list_cache_list=gtk.ComboBoxText()
        self.element_list_cache_list.connect('changed',self.element_list_page_jump_from_cache)
        self.element_list_cache_box.add(self.element_list_cache_list)
        self.element_list_box.pack_start(self.element_list_cache_box,False,False,0)
        self.element_list_box.add(self.element_list_parent)
        self.element_list_action_box=gtk.HBox(False,20)
        self.element_list_action_box.set_halign(gtk.Align.CENTER)
        self.element_list_action_previous=g_button_with_callback('←',self.element_page_previous)
        self.element_list_action_jump=g_button_with_callback('↔',self.element_page_jump_pre)
        self.element_list_action_next=g_button_with_callback('→',self.element_page_next)
        self.element_list_action_previous.props.sensitive=False
        self.element_list_action_jump.props.sensitive=False
        self.element_list_action_next.props.sensitive=False
        self.element_list_action_box.add(self.element_list_action_previous)
        self.element_list_action_box.add(self.element_list_action_jump)
        self.element_list_action_box.add(self.element_list_action_next)
        self.element_list_box.pack_end(self.element_list_action_box,False,False,0)

        self.task_list_stat_box=gtk.HBox()
        self.task_list_stat_all=gtk.Label('总数：')
        self.task_list_stat_pages=gtk.Label('页面数：')
        self.task_list_stat_box.add(self.task_list_stat_all)
        self.task_list_stat_box.add(self.task_list_stat_pages)
        self.task_list_box.pack_end(self.task_list_stat_box,False,False,0)

        self.chapter_list_parent=gtk.ScrolledWindow()
        self.chapter_list=gtk.TreeView()
        self.chapter_list.connect('row-activated',self.chapter_list_change)
        self.chapter_list_box=gtk.VBox(False,20)
        self.chapter_list_parent.add(self.chapter_list)
        self.chapter_list_box.add(self.chapter_list_parent)
        self.chapter_list_load=g_button_with_callback('加载更多',self.chapter_load)
        self.chapter_list_load.set_halign(gtk.Align.CENTER)
        self.chapter_list_load.set_size_request(50,-1)
        self.chapter_list_load.props.sensitive=False
        self.chapter_list_box.pack_end(self.chapter_list_load,False,False,0)

        self.task_list.set_activate_on_single_click(True)
        self.element_list.set_activate_on_single_click(True)
        self.chapter_list.set_activate_on_single_click(True)

        self.task_list.set_model(self.task_data)
        self.element_list.set_model(self.element_data)
        self.chapter_list.set_model(self.chapter_data)
        self.task_list.append_column(gtk.TreeViewColumn('内容',gtk.CellRendererText(),text=0))
        self.task_list.append_column(gtk.TreeViewColumn('方法',gtk.CellRendererText(),text=1))
        self.task_list.append_column(gtk.TreeViewColumn('排序',gtk.CellRendererText(),text=2))
        self.task_list.append_column(gtk.TreeViewColumn('类别',gtk.CellRendererText(),text=3))
        self.element_list.append_column(gtk.TreeViewColumn('名称',gtk.CellRendererText(),text=0))
        self.chapter_list.append_column(gtk.TreeViewColumn('名称',gtk.CellRendererText(),text=0))

        self.detail_parent=gtk.ScrolledWindow()
        self.detail=gtk.VBox()
        self.detail_parent.add_with_viewport(self.detail)
        self.detail.set_halign(gtk.Align.CENTER)
        self.detail_image=gtk.Image()
        self.detail_image.set_size_request(200,275)
        self.place_detail_image(GdkPixbuf.Pixbuf.new_from_file('picaph.png'))
        self.detail.pack_start(self.detail_image,False,False,0)
        self.comic_title=g_label_set_wrap(25)
        self.comic_author=g_label_set_wrap(25)
        self.comic_translator=g_label_set_wrap(25)
        self.comic_description=g_label_set_wrap(25)
        self.comic_categories=g_label_set_wrap(25)
        self.comic_tags=g_label_set_wrap(25)
        self.comic_status=g_label_set_wrap(25)
        self.comic_likes=g_label_set_wrap(25)
        self.comic_views=g_label_set_wrap(25)
        self.comic_comments=g_label_set_wrap(25)
        self.detail.pack_start(self.comic_title,False,False,0)
        self.detail.pack_start(self.comic_author,False,False,0)
        self.detail.pack_start(self.comic_translator,False,False,0)
        self.comic_description_box=gtk.HBox()
        self.comic_description_box.pack_start(g_label_bold('简介：'),False,False,0)
        self.comic_description_box.pack_start(self.comic_description,False,False,0)
        self.detail.pack_start(self.comic_description_box,False,False,0)
        self.comic_categories_box=gtk.HBox()
        self.comic_categories_box.pack_start(g_label_bold('类别：'),False,False,0)
        self.comic_categories_box.pack_start(self.comic_categories,False,False,0)
        self.detail.pack_start(self.comic_categories_box,False,False,0)
        self.comic_tags_box=gtk.HBox()
        self.comic_tags_box.pack_start(g_label_bold('标签：'),False,False,0)
        self.comic_tags_box.pack_start(self.comic_tags,False,False,0)
        self.detail.pack_start(self.comic_tags_box,False,False,0)
        self.comic_status_box=gtk.HBox()
        self.comic_status_box.pack_start(g_label_bold('状态：'),False,False,0)
        self.comic_status_box.pack_start(self.comic_status,False,False,0)
        self.detail.pack_start(self.comic_status_box,False,False,0)
        self.comic_likes_box=gtk.HBox()
        self.comic_likes_box.pack_start(g_label_bold('点赞数量：'),False,False,0)
        self.comic_likes_box.pack_start(self.comic_likes,False,False,0)
        self.detail.pack_start(self.comic_likes_box,False,False,0)
        self.comic_views_box=gtk.HBox()
        self.comic_views_box.pack_start(g_label_bold('浏览量：'),False,False,0)
        self.comic_views_box.pack_start(self.comic_views,False,False,0)
        self.detail.pack_start(self.comic_views_box,False,False,0)
        self.comic_comments_box=gtk.HBox()
        self.comic_comments_box.pack_start(g_label_bold('评论数量：'),False,False,0)
        self.comic_comments_box.pack_start(self.comic_comments,False,False,0)
        self.detail.pack_start(self.comic_comments_box,False,False,0)

        self.explorer.add(self.task_list_box)
        self.explorer.add(self.element_list_box)
        self.explorer.add(self.chapter_list_box)
        self.explorer.add(self.detail_parent)
        self.layout.pack_start(self.explorer,True,True,0)

        self.task_add.connect('clicked',self.create_search_window)

        self.task_list_index=-1
        self.element_list_index=-1
        self.element_list_snapshot_index=-1
        self.comic_profiles_cache={}
        self.comic_episodes_cache={}
        self.comic_episodes_load_cache={}

        self.connect('destroy',self.quit)
    def quit(self,window):
        self.downloader.should_die=True
        gtk.main_quit()
    def create_about_license_window(self,button):
        dialog=AboutLicenseWindow()
        dialog.run()
        dialog.destroy()
    def gen_context(self):
        return [self.token,self.config_mapping_service['channel'],BK_QUALITIES[self.config_mapping_service['quality']]]
    def show_auth_error(self,resp,transient_for=None):
        if transient_for==None:
            transient_for=self
        notice=gtk.MessageDialog(transient_for=transient_for,message_type=gtk.MessageType.WARNING,buttons=gtk.ButtonsType.YES_NO,text='加载错误')
        notice.format_secondary_text('服务器访问失败。代码：'+str(resp)+'\n'+('原因未知。' if resp!=1005 else '用户凭证过期或无效。')+'\n是否立刻注销以重启服务?')
        ret=notice.run()
        notice.destroy()
        if ret==gtk.ResponseType.YES:
            self.logout()
    def show_network_error(self,transient_for=None):
        if transient_for==None:
            transient_for=self
        notice=gtk.MessageDialog(transient_for=transient_for,message_type=gtk.MessageType.WARNING,buttons=gtk.ButtonsType.OK,text='加载错误')
        notice.format_secondary_text('网络连接失败。')
        notice.run()
        notice.destroy()
    def perform_stamp(self):
        resp=connections.sv_stamp(self.gen_context())
        if resp==None:
            self.show_network_error()
        elif type(resp)==int:
            self.show_auth_error(resp)
        else:
            if resp:
                if self.update_user_profile():
                    self.stamp.set_text('签到不可用' if self.user_profile==None else ('已签到' if self.user_profile['isPunched'] else '签到'))
                    if self.user_profile!=None and self.user_profile['isPunched']:
                        self.stamp.props.sensitive=False
            else:
                notice=gtk.MessageDialog(transient_for=transient_for,message_type=gtk.MessageType.WARNING,buttons=gtk.ButtonsType.OK,text='签到错误')
                notice.format_secondary_text('出现了未知的错误。')
                notice.run()
                notice.destroy()
    def update_user_profile(self):
        resp=connections.sv_user_profile(self.gen_context())
        if resp==None:
            self.show_network_error()
        elif type(resp)==int:
            self.show_auth_error(resp)
        else:
            self.user_profile=resp
            return True
        return False
    def chapter_load(self,button):
        id=self.task_data_entries[self.task_list_index][str(self.element_list_index+1)][self.element_list_snapshot_index]['_id']
        resepi=connections.sv_comic_episode(self.gen_context(),id,self.comic_episodes_load_cache[id]+1)
        if resepi==None:
            self.show_network_error()
        elif type(resepi)==int:
            self.show_auth_error()
        else:
            for i in resepi['docs']:
                self.comic_episodes_cache[id]['docs'].append(i)
                self.chapter_data.append([i['title']])
            self.comic_episodes_load_cache[id]+=1
        self.chapter_list_load.props.sensitive=self.comic_episodes_load_cache[id]<self.comic_episodes_cache[id]['pages']
    def chapter_list_change(self,tree,path,col):
        id=self.task_data_entries[self.task_list_index][str(self.element_list_index+1)][self.element_list_snapshot_index]['_id']
        page=1
        imgs=[]
        all=False
        order=int(self.comic_episodes_cache[id]['docs'][path.get_indices()[0]]['order'])
        while True:
            resp=connections.sv_comic_resource_list(self.gen_context(),id,order,page)
            if resp==None:
                self.show_network_error()
                break
            elif type(resp)==int:
                self.show_auth_error(resp)
                break
            else:
                start=1 if resp['page']==1 else (resp['page']-1)*resp['limit']+1
                for e in resp['docs']:
                    local=str(start)+'.'+e['media']['path'].split('.')[-1]
                    if not os.path.exists('librebika/local/'+id+'/'+str(order)+'/'+local):
                        imgs.append([local,e['media']['fileServer']+'/static/'+e['media']['path']])
                    start+=1
                if page==resp['pages']:
                    all=True
                    break
                else:
                    page+=1
        if all:
            l=[id,imgs,order]
            is_new=True
            for e in self.downloader.pending:
                if e[0]==l[0] and e[2]==l[2]:
                    is_new=False
                    break
            if is_new:
                self.downloader.pending.append(l)
                print('Main: Added new task, id = '+id+', order = '+str(order))
            else:
                print('Main: Skipped, id = '+id+', order = '+str(order))
        else:
            print('Main: Aborted for error, id = '+id+', order = '+str(order))
    def element_list_change(self,tree,path,col):
        id=self.task_data_entries[self.task_list_index][str(self.element_list_index+1)][path.get_indices()[0]]['_id']
        self.element_list_snapshot_index=path.get_indices()[0]
        if not os.path.exists('librebika/thumbnails/'):
            os.mkdir('librebika/thumbnails/')
        if id not in self.comic_profiles_cache:
            resp=connections.sv_comic_profile(self.gen_context(),id)
        else:
            resp=self.comic_profiles_cache[id]
        if resp==None:
            self.show_network_error()
        elif type(resp)==int:
            self.show_auth_error(resp)
        else:
            if id not in self.comic_profiles_cache:
                self.comic_profiles_cache[id]=resp
            self.chapter_data.clear()
            if id not in self.comic_episodes_cache:
                resepi=connections.sv_comic_episode(self.gen_context(),id,1)
                if resepi==None:
                    self.show_network_error()
                elif type(resepi)==int:
                    self.show_auth_error()
                else:
                    self.comic_episodes_cache[id]=resepi
                    self.comic_episodes_load_cache[id]=1
            self.chapter_list_load.props.sensitive=self.comic_episodes_load_cache[id]<self.comic_episodes_cache[id]['pages']
            for i in self.comic_episodes_cache[id]['docs']:
                self.chapter_data.append([i['title']])
            if not os.path.exists('librebika/thumbnails/'+id+'.'+resp['thumb']['path'].split('.')[-1]):
                resdown=connections.downloader(resp['thumb']['fileServer']+'/static/'+resp['thumb']['path'],'librebika/thumbnails/'+id+'.'+resp['thumb']['path'].split('.')[-1])
                if resdown==None:
                    self.show_network_error()
                elif resdown:
                    self.place_detail_image(GdkPixbuf.Pixbuf.new_from_file('librebika/thumbnails/'+id+'.'+resp['thumb']['path'].split('.')[-1]))
                elif not resdown:
                    pass #do anything?
            else:
                self.place_detail_image(GdkPixbuf.Pixbuf.new_from_file('librebika/thumbnails/'+id+'.'+resp['thumb']['path'].split('.')[-1]))
            self.update_comic_profile_display(id)
    def update_comic_profile_display(self,id):
        cache=self.comic_profiles_cache[id]
        self.comic_title.set_markup('<b>'+cache['title']+'</b>')
        self.comic_author.set_text(cache['author'])
        self.comic_translator.set_text(cache['chineseTeam'] if len(cache['chineseTeam'])>0 else '未知')
        self.comic_description.set_text(cache['description'])
        self.comic_categories.set_text(','.join(cache['categories']))
        self.comic_tags.set_text(','.join(cache['tags']))
        self.comic_status.set_text('完结' if cache['finished'] else '未完结')
        self.comic_likes.set_text(str(cache['totalLikes']))
        self.comic_views.set_text(str(cache['totalViews']))
        self.comic_comments.set_text(str(cache['commentsCount']))
    def create_settings_window(self,button):
        dialog=SettingsWindow(self)
        ret=dialog.run()
        if ret==0:
            self.config_mapping_service['channel']=dialog.select_channel.props.active_id
            self.config_mapping_service['quality']=dialog.select_quality.props.active_id
            for i in range(len(config_search_entries)):
                self.config_mapping_search[config_search_entries[i]]='yes' if dialog.toggle_buttons[i].props.active else 'no'
            self.save_config()
        dialog.destroy()
    def create_search_window(self,button):
        dialog=CreateSearchWindow()
        while True:
            ret=dialog.run()
            if ret==0:
                kw=dialog.search.get_text().strip()
                if len(kw)==0:
                    notice=gtk.MessageDialog(transient_for=dialog,message_type=gtk.MessageType.WARNING,buttons=gtk.ButtonsType.OK,text='搜索错误')
                    notice.format_secondary_text('关键字不能为空。')
                    notice.run()
                    notice.destroy()
                    continue
                else:
                    categories=None
                    if dialog.categorize.props.active:
                        categories=[]
                        for i in range(36):
                            if dialog.categories_children[i].props.active:
                                categories.append(BK_CATEGORIES_RAW[i])
                        if len(categories)==0:
                            categories=None
                    for i in self.config_mapping_search:
                        if self.config_mapping_search[i]=='no':
                            if categories==None:
                                categories=BK_CATEGORIES_RAW.copy()
                            if BK_CATEGORIES_RAW[config_search_indices[i]] in categories:
                                categories.remove(BK_CATEGORIES_RAW[config_search_indices[i]])
                    resp=connections.sv_keyword(self.gen_context(),kw,BK_SORT[dialog.sort.props.active_id],1,categories)
                    if resp==None:
                        self.show_network_error(dialog)
                        continue
                    elif type(resp)==int:
                        self.show_auth_error(resp,dialog)
                    else:
                        self.task_data_core.append([kw,'k',dialog.sort.props.active_id,categories,resp['total'],resp['pages']])
                        self.task_data_entries.append({'1':resp['docs']} if len(resp['docs'])!=0 else {})
                        self.task_data.append([kw,'关键字',dialog.sort.get_active_text(),','.join(categories) if categories!=None else ''])
            dialog.destroy()
            break
    def pre_logout(self,button):
        notice=gtk.MessageDialog(transient_for=self,message_type=gtk.MessageType.WARNING,buttons=gtk.ButtonsType.YES_NO,text='确认操作')
        notice.format_secondary_text('是否注销?')
        ret=notice.run()
        notice.destroy()
        if ret==gtk.ResponseType.YES:
            self.logout()
    def logout(self):
        path='librebika/token'
        if os.path.exists(path):
            os.remove(path)
        self.destroy()
    def task_list_change(self,tree,path,col):
        self.task_list_index=path.get_indices()[0]
        self.task_list_stat_all.set_text('总数：'+str(self.task_data_core[self.task_list_index][4]))
        self.task_list_stat_pages.set_text('页面数：'+str(self.task_data_core[self.task_list_index][5]))
        self.element_list_action_previous.props.sensitive=False
        self.element_list_action_jump.props.sensitive=self.task_data_core[self.task_list_index][5]>1
        self.element_list_action_next.props.sensitive=self.task_data_core[self.task_list_index][5]>1
        self.element_list_index=0
        self.element_data.clear()
        self.chapter_data.clear()
        self.chapter_list_load.props.sensitive=False
        self.element_list_cache_list.remove_all()
        if len(self.task_data_entries[self.task_list_index])!=0:
            for i in self.task_data_entries[self.task_list_index]['1']:
                self.element_data.append([i['title']])
            tmp_cache=[]
            for i in self.task_data_entries[self.task_list_index]:
                tmp_cache.append(int(i))
            tmp_cache.sort()
            for i in range(len(tmp_cache)):
                self.element_list_cache_list.append(str(tmp_cache[i]),str(tmp_cache[i]))
            self.element_list_cache_list.props.active_id='1'
    def element_page_next(self,button):
        data=self.task_data_core[self.task_list_index]
        if self.element_list_index<data[5]-1:
            self.element_list_jump_to(self.element_list_index+1)
    def element_page_previous(self,button):
        data=self.task_data_core[self.task_list_index]
        if self.element_list_index>0:
            self.element_list_jump_to(self.element_list_index-1)
    def element_page_jump_pre(self,button):
        data=self.task_data_core[self.task_list_index]
        dialog=ElementPageControlWindow(1,data[5],self.element_list_index)
        ret=dialog.run()
        if ret==0:
            if int(dialog.slider.get_value())-1!=self.element_list_index:
                self.element_list_jump_to(int(dialog.slider.get_value())-1)
        dialog.destroy()
    def element_list_page_jump_from_cache(self,selector):
        if selector.props.active_id!=None and selector.props.active_id!=str(self.element_list_index+1):
            self.element_list_jump_to(int(selector.props.active_id)-1)
    def element_list_jump_to(self,page):
        data=self.task_data_core[self.task_list_index]
        if 0<=page<data[5]:
            stored=self.task_data_entries[self.task_list_index]
            if str(page+1) in stored:
                self.element_data.clear()
                for i in self.task_data_entries[self.task_list_index][str(page+1)]:
                    self.element_data.append([i['title']])
            else:
                resp=connections.sv_keyword(self.gen_context(),data[0],BK_SORT[data[2]],page+1,data[3])
                if resp==None:
                    self.show_network_error()
                elif type(resp)==int:
                    self.show_auth_error(resp)
                else:
                    self.task_data_entries[self.task_list_index][str(page+1)]=resp['docs']
                    self.element_data.clear()
                    for i in self.task_data_entries[self.task_list_index][str(page+1)]:
                        self.element_data.append([i['title']])
            self.element_list_index=page
            self.element_list_action_previous.props.sensitive=self.element_list_index>0
            self.element_list_action_jump.props.sensitive=self.task_data_core[self.task_list_index][5]>1
            self.element_list_action_next.props.sensitive=self.element_list_index<self.task_data_core[self.task_list_index][5]-1
            self.element_list_cache_list.remove_all()
            tmp_cache=[]
            for i in self.task_data_entries[self.task_list_index]:
                tmp_cache.append(int(i))
            tmp_cache.sort()
            for i in range(len(tmp_cache)):
                self.element_list_cache_list.append(str(tmp_cache[i]),str(tmp_cache[i]))
            self.element_list_cache_list.props.active_id=str(page+1)
    def place_detail_image(self,pixbuf):
        pixbuf=pixbuf.scale_simple(200,275,GdkPixbuf.InterpType.BILINEAR)
        self.detail_image.set_from_pixbuf(pixbuf)
    def load_config(self):
        if os.path.exists('librebika/config.ini'):
            config=configparser.ConfigParser()
            try:
                config.read('librebika/config.ini')
                if any([e not in config for e in ['service','search']]):
                    raise Exception()
                if any([e not in config['service'] for e in config_service_entries]):
                    raise Exception()
                if any([e not in config['search'] for e in config_search_entries]):
                    raise Exception()
                self.config_mapping_service={}
                self.config_mapping_search={}
                if config['service']['channel'] not in ['1','2','3']:
                    raise Exception()
                if config['service']['quality'] not in ['l','m','h','o']:
                    raise Exception()
                self.config_mapping_service['channel']=config['service']['channel']
                self.config_mapping_service['quality']=config['service']['quality']
                for i in config_search_entries:
                    if config['search'][i] not in ['yes','no']:
                        raise Exception()
                    self.config_mapping_search[i]=config['search'][i]
            except:
                self.gen_config()
        else:
            self.gen_config()
    def save_config(self):
        config=configparser.ConfigParser()
        service={}
        search={}
        for i in config_service_entries:
            service[i]=self.config_mapping_service[i]
        for i in config_search_entries:
            search[i]=self.config_mapping_search[i]
        config['service']=service
        config['search']=search
        with open('librebika/config.ini','w') as f:
            config.write(f)
    def gen_config(self):
        config=configparser.ConfigParser()
        service={}
        search={}
        service['channel']='1'
        service['quality']='o'
        search['includeoriginaltext']='yes'
        search['includegay']='yes'
        search['includenonadult']='yes'
        search['includegore']='yes'
        config['service']=service
        config['search']=search
        with open('librebika/config.ini','w') as f:
            config.write(f)
        self.config_mapping_service=service
        self.config_mapping_search=search

class AboutLicenseWindow(gtk.Dialog):
    def __init__(self):
        gtk.Dialog.__init__(self,title='许可声明')
        self.get_action_area().set_halign(gtk.Align.CENTER)
        self.set_default_size(200,-1)
        self.add_button('关闭',0)
        chlabel=gtk.Label('本软件（即LibreBika）的制作和传播秉承免费开源的精神，无意侵犯任何人的商业利益。本软件和嗶咔无合作关系。禁止贩卖本软件或以本软件为基础获得经济利益。基于GPL2.0（不包含新版本）许可，用户可自由使用、修改、和传播本软件。本作者不承担用户任何行为和后果的责任。本作者无义务和能力干涉经过修改的本软件的功能和传播。本软件依赖嗶咔的API。用户不可使用本软件进行干涉嗶咔服务器正常运行的行为。本软件的官方版本仅在Github由用户OddBirdStanley以Python源代码的形式发布。在运行第三方版本前，用户应当仔细检查源代码以确保使用安全。用户不应运行经过封装的闭源的本软件的版本。本软件仅可在桌面平台使用。任何声明皆以本软件的官方版本为准。')
        enlabel=gtk.Label('LibreBika: An Open-source Third-party Client of PicaComic.\nCopyright © 2021 by Stanley Jian <jianstanley@outlook.com>\n\nThis program is free software; you can redistribute it and/or modify\nit under the terms of the GNU General Public License Version 2 as published by\nthe Free Software Foundation.\n\nThis program is distributed in the hope that it will be useful,\nbut WITHOUT ANY WARRANTY; without even the implied warranty of\nMERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the\nGNU General Public License for more details.\n\nYou should have received a copy of the GNU General Public License along\nwith this program; if not, write to the Free Software Foundation, Inc.,\n51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.\n\n@license GPL-2.0 <http://spdx.org/licenses/GPL-2.0>')
        chlabel.set_line_wrap(True)
        chlabel.set_line_wrap_mode(gtk.WrapMode.CHAR)
        chlabel.set_max_width_chars(65)
        chlabel.set_halign(gtk.Align.CENTER)
        g_set_margins(chlabel,bottom=20)
        self.get_content_area().add(chlabel)
        self.get_content_area().add(enlabel)
        g_set_margins(self.get_content_area(),20,20,20,20)
        g_set_margins(self.get_action_area(),20,20,0,20)
        self.show_all()

class CreateSearchWindow(gtk.Dialog):
    def __init__(self):
        gtk.Dialog.__init__(self,title='关键字搜索')
        self.get_action_area().set_halign(gtk.Align.CENTER)
        self.add_button('提交',0)
        self.add_button('取消',1)
        content=self.get_content_area()
        g_set_margins(content,20,20,20,20)
        g_set_margins(self.get_action_area(),20,20,0,20)
        self.search=gtk.SearchEntry()
        self.search.set_placeholder_text('搜索您喜欢的内容')
        g_set_margins(self.search,bottom=10)
        self.sort_box=gtk.HBox()
        self.sort_box.pack_start(gtk.Label('排序'),False,False,10)
        self.sort=g_combobox_with_entries({'d':'默认','t':'旧新','h':'爱心','p':'人数'})
        self.sort.set_size_request(150,-1)
        self.sort.set_halign(gtk.Align.START)
        g_set_margins(self.sort_box,bottom=10)
        self.sort_box.add(self.sort)
        self.sort.props.active_id='d'
        self.categorize_box=gtk.HBox()
        self.categorize=gtk.CheckButton.new_with_label('筛选分类')
        self.categorize_all=gtk.CheckButton.new_with_label('全选开关')
        self.categorize_all.props.sensitive=False
        self.categorize_box.pack_start(self.categorize,False,False,0)
        self.categorize_box.pack_start(self.categorize_all,False,False,20)
        self.categories=gtk.Grid()
        self.categories_children=[]
        for i in range(6):
            for j in range(6):
                self.categories_children.append(gtk.CheckButton.new_with_label(BK_CATEGORIES[i*6+j]))
                self.categories_children[i*6+j].props.sensitive=False
                self.categories.attach(self.categories_children[i*6+j],j,i,1,1)
        content.add(self.search)
        content.add(self.sort_box)
        content.add(self.categorize_box)
        content.add(self.categories)
        self.label=gtk.Label('留空则不筛选类别')
        g_set_margins(self.label,top=15)
        content.pack_end(self.label,False,False,0)
        self.categorize.connect('toggled',self.categorize_toggle)
        self.categorize_all.connect('toggled',self.categorize_all_toggle)
        self.connect('key_press_event',self.on_key_press)
        self.show_all()
    def on_key_press(self,window,data):
        if data.keyval==gdk.KEY_Return:
            self.get_widget_for_response(0).clicked()
    def categorize_toggle(self,button):
        for i in self.categories_children:
            i.props.sensitive=button.props.active
        self.categorize_all.props.sensitive=button.props.active
    def categorize_all_toggle(self,button):
        for i in self.categories_children:
            i.props.active=button.props.active

class ElementPageControlWindow(gtk.Dialog):
    def __init__(self,min,max,curr):
        gtk.Dialog.__init__(self,title='跳转至页面')
        self.slider=gtk.Scale.new_with_range(gtk.Orientation.HORIZONTAL,min,max,1)
        self.slider.set_value(curr)
        self.add_button('提交',0)
        self.add_button('取消',1)
        self.get_content_area().add(self.slider)
        self.show_all()

class SettingsWindow(gtk.Dialog):
    def __init__(self,lb_window):
        gtk.Dialog.__init__(self,title='设置')
        self.get_action_area().set_halign(gtk.Align.CENTER)
        g_set_margins(self.get_action_area(),20,20,0,20)
        self.add_button('保存',0)
        self.add_button('取消',1)
        content=self.get_content_area()
        g_set_margins(content,20,20,20,20)
        self.select_lists=[]
        self.toggle_buttons=[]
        self.select_channel_box=gtk.HBox()
        self.select_quality_box=gtk.HBox()
        self.select_channel=g_combobox_with_entries({'1':'1','2':'2','3':'3'})
        self.select_channel_box.pack_start(gtk.Label('服务器'),False,False,20)
        self.select_channel.props.active_id=lb_window.config_mapping_service['channel']
        self.select_channel_box.add(self.select_channel)
        self.select_quality=g_combobox_with_entries({'l':'低','m':'中','h':'高','o':'原版'})
        self.select_quality_box.pack_start(gtk.Label('图片质量'),False,False,20)
        self.select_quality.props.active_id=lb_window.config_mapping_service['quality']
        self.select_quality_box.add(self.select_quality)
        g_set_margins(self.select_channel_box,bottom=10)
        g_set_margins(self.select_quality_box,bottom=10)
        self.select_lists.append(self.select_channel_box)
        self.select_lists.append(self.select_quality_box)
        self.toggle_buttons.append(gtk.CheckButton.new_with_label('显示生肉'))
        self.toggle_buttons.append(gtk.CheckButton.new_with_label('显示耽美'))
        self.toggle_buttons.append(gtk.CheckButton.new_with_label('显示非成人向'))
        self.toggle_buttons.append(gtk.CheckButton.new_with_label('显示重口'))
        for i in range(len(config_search_entries)):
            self.toggle_buttons[i].props.active=lb_window.config_mapping_search[config_search_entries[i]]=='yes'
        for i in self.select_lists:
            content.pack_start(i,False,False,0)
        for i in self.toggle_buttons:
            content.pack_start(i,False,False,0)
        self.label=gtk.Label('更改的设置不会影响过去的搜索任务')
        g_set_margins(self.label,top=15)
        content.pack_end(self.label,False,False,0)
        self.connect('key_press_event',self.on_key_press)
        self.show_all()
    def on_key_press(self,window,data):
        if data.keyval==gdk.KEY_Return:
            self.get_widget_for_response(0).clicked()

class LoginWindow(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self,title='登录')
        self.layout=gtk.VBox(False,20)
        self.layout.set_size_request(300,-1)
        self.layout.set_halign(gtk.Align.CENTER)
        self.layout.set_valign(gtk.Align.CENTER)
        g_set_margins(self.layout,30,30,30,30)
        self.add(self.layout)

        self.username=gtk.Entry()
        self.username.set_placeholder_text('用户名')

        self.password=gtk.Entry()
        self.password.set_placeholder_text('密码')
        self.password.props.visibility=False

        self.submit=gtk.Button.new_with_label('提交')
        self.submit.set_halign(gtk.Align.CENTER)
        self.submit.set_size_request(150,-1)
        self.submit.connect('clicked',self.on_submit)

        self.layout.add(self.username)
        self.layout.add(self.password)
        self.layout.add(self.submit)
        self.connect('key_press_event',self.on_key_press)
    def on_key_press(self,window,data):
        if data.keyval==gdk.KEY_Return:
            self.submit.clicked()
    def on_submit(self,button):
        if len(self.username.get_text())<1:
            notice=gtk.MessageDialog(transient_for=self,message_type=gtk.MessageType.WARNING,buttons=gtk.ButtonsType.OK,text='用户名格式错误')
            notice.format_secondary_text('用户名不能为空。')
            notice.run()
            notice.destroy()
        elif len(re.findall(username_regex,self.username.get_text()))!=0:
            notice=gtk.MessageDialog(transient_for=self,message_type=gtk.MessageType.WARNING,buttons=gtk.ButtonsType.OK,text='用户名格式错误')
            notice.format_secondary_text('用户名只能包含数字，小写英文字符，点，和下划线。')
            notice.run()
            notice.destroy()
        elif len(self.password.get_text())<8:
            notice=gtk.MessageDialog(transient_for=self,message_type=gtk.MessageType.WARNING,buttons=gtk.ButtonsType.OK,text='密码格式错误')
            notice.format_secondary_text('密码必须至少长度为8。')
            notice.run()
            notice.destroy()
        else:
            try:
                result=connections.log_in(self.username.get_text(),self.password.get_text())
                if result.startswith('!'):
                    notice=gtk.MessageDialog(transient_for=self,message_type=gtk.MessageType.WARNING,buttons=gtk.ButtonsType.OK,text='登录失败')
                    notice.format_secondary_text(result[1:])
                    notice.run()
                    notice.destroy()
                else:
                    self.acquired_token=result
                    self.destroy()
            except:
                notice=gtk.MessageDialog(transient_for=self,message_type=gtk.MessageType.WARNING,buttons=gtk.ButtonsType.OK,text='登录失败')
                notice.format_secondary_text('网络连接失败')
                notice.run()
                notice.destroy()
