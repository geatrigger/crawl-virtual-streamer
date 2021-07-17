import pymysql
from pymongo import MongoClient
import requests
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import time
import os
import json
from operator import itemgetter
from threading import Timer
import re
from datetime import datetime

re_image = re.compile('[a-zA-Z0-9:/?=.]+(?=\')')
re_text = re.compile('[^가-힣a-zA-Z0-9.]')
re_manager = re.compile('[(](\S+)[)]')

s = requests.Session()
retries = Retry(total=5,
               backoff_factor=4, # 2, 4, 8, 16, 32
               status_forcelist=[500, 502, 503, 504])
headers= {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:87.0) Gecko/20100101 Firefox/87.0'
}

def crawl(base_url, params, how):
  if how == 'get':
    res = s.get(base_url, headers=headers, params=params)
  elif how == 'post':
    res = s.post(base_url, headers=headers, params=params)
  now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  if res.status_code == 200:
    return (res.content, now, res.status_code)
  else:
    return (None, now, res.status_code)
def save_to_db(html, crawl_time, mode, board_cnt, file_name='./test_test/dummy'):
  '''
  parameter:
      html(string like): 크롤링한 내용
      crawl_time(string): %Y-%m-%d %H:%M:%S형식의 크롤링 끝난 시간정보
      mode(string): post, board, comment
      file_name(string): (임시용)크롤링한 파일을 저장할 장소
  '''
  start = time.time()
  soup = BeautifulSoup(html, 'lxml')
  if mode == 'post':
    gall_num = soup.select_one('#no')['value']
    title = soup.select_one('html.darkmode body div#top.dcwrap.width1160.view_wrap.miniwrap div.wrap_inner main#container.clear.mini_view section article div.view_content_wrap header div.gallview_head.clear.ub-content h3.title.ub-word span.title_subject')
    if not title:
      return
    nickname = soup.select_one('html.darkmode body div#top.dcwrap.width1160.view_wrap.miniwrap div.wrap_inner main#container.clear.mini_view section article div.view_content_wrap header div.gallview_head.clear.ub-content div.gall_writer.ub-writer div.fl span.nickname')
    ip = soup.select_one('html.darkmode body div#top.dcwrap.width1160.view_wrap.miniwrap div.wrap_inner main#container.clear.mini_view section article div.view_content_wrap header div.gallview_head.clear.ub-content div.gall_writer.ub-writer div.fl span.ip')
    uid = soup.select_one('html.darkmode body div#top.dcwrap.width1160.view_wrap.miniwrap div.wrap_inner main#container.clear.mini_view section article div.view_content_wrap header div.gallview_head.clear.ub-content div.gall_writer.ub-writer')
    gall_date = soup.select_one('html.darkmode body div#top.dcwrap.width1160.view_wrap.miniwrap div.wrap_inner main#container.clear.mini_view section article div.view_content_wrap header div.gallview_head.clear.ub-content div.gall_writer.ub-writer div.fl span.gall_date')
    content = soup.select_one('html.darkmode body div#top.dcwrap.width1160.view_wrap.miniwrap div.wrap_inner main#container.clear.mini_view section article div.view_content_wrap div.gallview_contents div.inner.clear div.writing_view_box div.write_div')
    embed_links = soup.select('#container > section > article:nth-child(3) > div.view_content_wrap > div > div.inner.clear > div.writing_view_box > div.write_div > div > embed')
    img_links = soup.select('#container > section > article:nth-child(3) > div.view_content_wrap > div > div.inner.clear > div.writing_view_box > div.write_div > p > img')
    view_cnt = soup.select_one('#container > section > article:nth-child(3) > div.view_content_wrap > header > div > div > div.fr > span.gall_count')
    comment_cnt = soup.select_one('#container > section > article:nth-child(3) > div.view_content_wrap > header > div > div > div.fr > span.gall_comment')
    up_cnt = soup.select_one('#recommend_view_up_' + str(gall_num))
    up_fix_cnt = soup.select_one('#recommend_view_up_fix_' + str(gall_num))
    down_cnt = soup.select_one('#recommend_view_down_' + str(gall_num))
    head_text = soup.select_one('#container > section > article:nth-child(3) > div.view_content_wrap > header > div > h3 > span.title_headtext')

    json_file = {}
    json_file['crawl_time'] = crawl_time
    json_file['gall_num'] = gall_num
    json_file['title'] = title.get_text()
    json_file['nickname'] = nickname.get_text()
    json_file['uid'] = uid.attrs['data-uid'] if uid and uid != '' else None
    json_file['ip'] = re_text.sub('', ip.get_text()) if ip else None
    json_file['gall_date'] = gall_date['title']
    json_file['content'] = content.get_text("\n", strip=True)
    json_file['embed_links'] = [embed_link['src'] for embed_link in embed_links] if embed_links else None
    json_file['img_links'] = [re_image.search(img_link['src']).group() if re_image.search(img_link['src']) else '' for img_link in img_links] if img_links else None
    json_file['view_cnt'] = view_cnt.get_text() if view_cnt else None
    json_file['comment_cnt'] = comment_cnt.get_text() if comment_cnt else None
    json_file['up_cnt'] = up_cnt.get_text() if up_cnt else None
    json_file['up_fix_cnt'] = up_fix_cnt.get_text() if up_fix_cnt else None
    json_file['down_cnt'] = down_cnt.get_text() if down_cnt else None
    json_file['head_text'] = re_text.sub('', head_text.get_text()) if head_text else None
    client['virtual_streamer_gall']['post'].insert_one(json_file)
  elif mode == 'board':
    if not soup.select_one('#container > section.left_content > article:nth-child(3) > div.gall_listwrap.list'):
      print(soup)
      return
    gall_nums = soup.select('#container > section.left_content > article:nth-child(3) > div.gall_listwrap.list > table > tbody > tr:not([data-type="icon_notice"]).us-post > td.gall_num')
    head_texts = soup.select('#container > section.left_content > article:nth-child(3) > div.gall_listwrap.list > table > tbody > tr:not([data-type="icon_notice"]).us-post > td.gall_subject')
    titles = soup.select('#container > section.left_content > article:nth-child(3) > div.gall_listwrap.list > table > tbody > tr:not([data-type="icon_notice"]).us-post > td.gall_tit.ub-word > a:nth-child(1)')
    comment_cnts = soup.select('#container > section.left_content > article:nth-child(3) > div.gall_listwrap.list > table > tbody > tr:not([data-type="icon_notice"]).us-post > td.gall_tit.ub-word')
    writers = soup.select('#container > section.left_content > article:nth-child(3) > div.gall_listwrap.list > table > tbody > tr:not([data-type="icon_notice"]).us-post > td.gall_writer.ub-writer')
    gall_dates = soup.select('#container > section.left_content > article:nth-child(3) > div.gall_listwrap.list > table > tbody > tr:not([data-type="icon_notice"]).us-post > td.gall_date')
    view_cnts = soup.select('#container > section.left_content > article:nth-child(3) > div.gall_listwrap.list > table > tbody > tr:not([data-type="icon_notice"]).us-post > td.gall_count')
    up_cnts = soup.select('#container > section.left_content > article:nth-child(3) > div.gall_listwrap.list > table > tbody > tr:not([data-type="icon_notice"]).us-post > td.gall_recommend')
    manager = soup.select_one('#container > section.left_content > article:nth-child(2) > div > div > div.issue_contentbox.clear > div > div.info_contbox > div > div:nth-child(1) > p > span')
    sub_managers = soup.select('#container > section.left_content > article:nth-child(2) > div > div > div.issue_contentbox.clear > div > div.info_contbox > div > div:nth-child(2) > p span[title]')

    json_file = {}
    json_file['crawl_time'] = crawl_time
    json_file['gall_nums'] = [int(gall_num.get_text()) for gall_num in gall_nums] if gall_nums else None
    json_file['head_texts'] = [re_text.sub('', head_text.get_text()) for head_text in head_texts] if head_texts else None
    json_file['titles'] = [title.get_text() for title in titles] if titles else None
    json_file['comment_cnts'] = [re_text.sub('', comment_cnt.select_one('a.reply_numbox').get_text()) if comment_cnt.select_one('a.reply_numbox') else '0' for comment_cnt in comment_cnts] if comment_cnts else None
    json_file['writers'] = list(zip([writer['data-nick'] for writer in writers], [writer['data-uid'] for writer in writers], [writer['data-ip'] for writer in writers])) if writers else None
    json_file['gall_dates'] = [gall_date['title'] for gall_date in gall_dates] if gall_dates else None
    json_file['view_cnts'] = [view_cnt.get_text() for view_cnt in view_cnts] if view_cnts else None
    json_file['up_cnts'] = [up_cnt.get_text() for up_cnt in up_cnts] if up_cnts else None
    json_file['manager'] = re_manager.search(manager.get_text()).group(1) if manager else None
    json_file['sub_managers'] = [sub_manager['title'] for sub_manager in sub_managers] if sub_managers else None
    json_file['board_cnt'] = board_cnt
    client['virtual_streamer_gall']['board'].insert_one(json_file)
    return json_file['gall_nums']
  elif mode == 'comment':
    with open(path + 'comment.html', 'w', encoding='UTF-8') as f:
      f.write(html.decode('utf-8'))
    


# conn = pymysql.connect(host='mysql', port=3306, user='root', passwd='bus', db='virtual_streamer_board')
# cur = conn.cursor()
# sql = '''create table test(
#     name varchar(20) primary key,
#     num int not null
# );'''
# cur.execute(sql)
# conn.commit()
# conn.close()
# with open('./hi.txt', 'w', encoding='utf-8') as f:
#     f.write('where are you slave..\n')
# client = MongoClient('mongo', 27017, username='root', password='password', authSource='virtual_streamer_gall')
client = MongoClient('mongo', 27017)
# client['virtual_streamer_gall']['test'].insert_one({
#   'name': 'kim',
#   'age': 10
# })
print('hello print test')
with open('./hi.txt', 'w', encoding='utf-8') as f:
  f.write(str(client['virtual_streamer_gall']['test']))

path = './test_test/'
if not os.path.exists(path):
  os.makedirs('test_test')

base_url = "https://gall.dcinside.com/mini/board/lists"
view_url = 'https://gall.dcinside.com/mini/board/view/'
comment_url = 'http://gall.dcinside.com/mini/board/comment/'

start = time.time()

page_cnt = 100000
# read most recent
# board_cnt, gall_nums
board_cnt = -1
is_done = False
end_gall_num = 10000000000
with open('./crawl_info.txt', 'r', encoding='utf-8') as f:
  board_cnt = int(f.readline())
  end_gall_num = int(f.readline())
try:
  board_gall_nums = []
  board_gall_nums_arr = [ith_board['gall_nums'] for ith_board in client['virtual_streamer_gall']['board'].find({'board_cnt': board_cnt})]
  for ith_gall_nums in board_gall_nums_arr:
    board_gall_nums += list(map(int, ith_gall_nums))
  post_gall_nums = list(map(int, client['virtual_streamer_gall']['post'].distinct('gall_num')))
  gall_nums = list(set(board_gall_nums) - set(post_gall_nums))
  while True:
    work_start = time.time()
    # crawl_info.txt must have complete crawling board_cnt
    # if not complete crawling posts at board_cnt, resume
    if not gall_nums:
      board_cnt += 1
      for i in range(1, page_cnt):
        params = {
          'id': 'virtual_streamer',
          'list_num': '100',
          'sort_type': 'N',
          'page': i
        }
        html, crawl_time, status_code = crawl(base_url, params, 'get')
        if html:
          gall_nums_part = save_to_db(html, crawl_time, 'board', board_cnt, path)
          time.sleep(2)
        else:
          with open('./' + 'boarderror' + '.txt', 'a', encoding='utf-8') as f:
            f.write('error at: ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '\n')
            f.write('not 200 at status_code: ' + str(status_code) + '\n')
            f.write('not 200 at board_cnt: ' + str(board_cnt) + '\n')
            f.write('not 200 at end_gall_num: ' + str(end_gall_num) + '\n')
            f.write('not 200 at ith page: ' + str(i) + '\n')
          continue
        gall_nums += gall_nums_part
        if end_gall_num >= min(gall_nums):
          break
    # mongo에서 end_gall_num값보다 더 큰 gall_num값들만 가져옴
    # 해당 값이 나오면 스킵
    with open('./crawl_info.txt', 'w', encoding='utf-8') as f:
      f.write(str(board_cnt) + '\n')
      f.write(str(end_gall_num) + '\n')
    gall_nums = sorted(list(set(gall_nums)), reverse=True)
    for gall_num in gall_nums:
      if gall_num <= end_gall_num:
        continue
      params = {
        'id': 'virtual_streamer',
        'no': gall_num,
      }
      html, crawl_time, status_code = crawl(view_url, params, 'get')
      if html:
        save_to_db(html, crawl_time, 'post', None, path)
        time.sleep(2)
      else:
        with open('./' + str(gall_num) + '.txt', 'w', encoding='utf-8') as f:
          f.write('error at: ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '\n')
          f.write('not 200 at board_cnt: ' + str(board_cnt) + '\n')
          f.write('not 200 at end_gall_num: ' + str(end_gall_num) + '\n')
          f.write('not 200 at gall_num: ' + str(gall_num) + '\n')
          f.write('not 200 at status_code: ' + str(status_code) + '\n')

    end_gall_num = max(gall_nums)
    with open('./crawl_info.txt', 'w', encoding='utf-8') as f:
      f.write(str(board_cnt) + '\n')
      f.write(str(end_gall_num) + '\n')
    gall_nums = []
    work_end = time.time()
    while work_end - work_start < 30:
      work_end = time.time()
    end = time.time()
except Exception as e:
  with open('./error.txt', 'w', encoding='utf-8') as f:
    f.write('error at: ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '\n')
    f.write('error name is: ' + str(e) + '\n')
    f.write('error at board_cnt: ' + str(board_cnt) + '\n')
    f.write('error at end_gall_num: ' + str(end_gall_num) + '\n')
    f.write('error at gall_num: ' + str(gall_num) + '\n')
    f.write('error at status_code: ' + str(status_code) + '\n')