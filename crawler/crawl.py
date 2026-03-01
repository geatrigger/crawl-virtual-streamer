from pymongo import MongoClient
import requests
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import time
import os
import json
import csv
import re
from datetime import datetime

re_text = re.compile('[^가-힣a-zA-Z0-9.]')
re_manager = re.compile('[(](\S+)[)]')

s = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=4,
    status_forcelist=[500, 502, 503, 504],
)
s.mount('https://', HTTPAdapter(max_retries=retries))
s.mount('http://', HTTPAdapter(max_retries=retries))

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:87.0) Gecko/20100101 Firefox/87.0',
    'X-Requested-With': 'XMLHttpRequest',
}


def crawl(base_url, params, how):
    if how == 'get':
        res = s.get(base_url, headers=headers, params=params, timeout=15)
    elif how == 'post':
        res = s.post(base_url, headers=headers, params=params, timeout=15)
    else:
        raise ValueError('how must be get or post')

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if res.status_code == 200:
        return (res.content, now, res.status_code)
    return (None, now, res.status_code)


def parse_post(html, crawl_time):
    soup = BeautifulSoup(html, 'lxml')
    gall_num = soup.select_one('#no')
    title = soup.select_one('span.title_subject')
    if not gall_num or not title:
        return None

    writer = soup.select_one('div.gall_writer.ub-writer')
    nickname = soup.select_one('span.nickname')
    ip = soup.select_one('span.ip')
    gall_date = soup.select_one('span.gall_date')
    content = soup.select_one('div.write_div')
    embed_links = soup.select('div.write_div embed')
    img_links = soup.select('div.write_div img')
    view_cnt = soup.select_one('span.gall_count')
    comment_cnt = soup.select_one('span.gall_comment')
    up_cnt = soup.select_one('#recommend_view_up_' + gall_num['value'])
    up_fix_cnt = soup.select_one('#recommend_view_up_fix_' + gall_num['value'])
    down_cnt = soup.select_one('#recommend_view_down_' + gall_num['value'])
    head_text = soup.select_one('span.title_headtext')

    return {
        'crawl_time': crawl_time,
        'gall_num': gall_num['value'],
        'title': title.get_text(strip=True),
        'nickname': nickname.get_text(strip=True) if nickname else None,
        'uid': writer.attrs.get('data-uid') if writer else None,
        'ip': re_text.sub('', ip.get_text()) if ip else None,
        'gall_date': gall_date['title'] if gall_date and gall_date.has_attr('title') else None,
        'content': content.get_text('\n', strip=True) if content else None,
        'embed_links': [embed_link['src'] for embed_link in embed_links if embed_link.has_attr('src')] or None,
        'img_links': [img_link['src'] for img_link in img_links if img_link.has_attr('src')] or None,
        'view_cnt': view_cnt.get_text(strip=True) if view_cnt else None,
        'comment_cnt': comment_cnt.get_text(strip=True) if comment_cnt else None,
        'up_cnt': up_cnt.get_text(strip=True) if up_cnt else None,
        'up_fix_cnt': up_fix_cnt.get_text(strip=True) if up_fix_cnt else None,
        'down_cnt': down_cnt.get_text(strip=True) if down_cnt else None,
        'head_text': re_text.sub('', head_text.get_text()) if head_text else None,
    }


def parse_board(html, crawl_time, board_cnt):
    soup = BeautifulSoup(html, 'lxml')
    rows = soup.select('tr.us-post:not([data-type="icon_notice"])')
    if not rows:
        return None

    gall_nums = []
    head_texts = []
    titles = []
    comment_cnts = []
    writers = []
    gall_dates = []
    view_cnts = []
    up_cnts = []

    for row in rows:
        gall_num = row.select_one('td.gall_num')
        if gall_num:
            try:
                gall_nums.append(int(gall_num.get_text(strip=True)))
            except ValueError:
                continue
        else:
            continue

        head = row.select_one('td.gall_subject')
        title = row.select_one('td.gall_tit > a')
        comment = row.select_one('td.gall_tit a.reply_numbox')
        writer = row.select_one('td.gall_writer')
        gall_date = row.select_one('td.gall_date')
        view_cnt = row.select_one('td.gall_count')
        up_cnt = row.select_one('td.gall_recommend')

        head_texts.append(re_text.sub('', head.get_text()) if head else None)
        titles.append(title.get_text(strip=True) if title else None)
        comment_cnts.append(re_text.sub('', comment.get_text()) if comment else '0')
        writers.append((
            writer.attrs.get('data-nick') if writer else None,
            writer.attrs.get('data-uid') if writer else None,
            writer.attrs.get('data-ip') if writer else None,
        ))
        gall_dates.append(gall_date.attrs.get('title') if gall_date and gall_date.has_attr('title') else gall_date.get_text(strip=True) if gall_date else None)
        view_cnts.append(view_cnt.get_text(strip=True) if view_cnt else None)
        up_cnts.append(up_cnt.get_text(strip=True) if up_cnt else None)

    manager = soup.select_one('div.info_contbox div:nth-child(1) > p > span')
    sub_managers = soup.select('div.info_contbox div:nth-child(2) > p span[title]')

    return {
        'crawl_time': crawl_time,
        'gall_nums': gall_nums,
        'head_texts': head_texts,
        'titles': titles,
        'comment_cnts': comment_cnts,
        'writers': writers,
        'gall_dates': gall_dates,
        'view_cnts': view_cnts,
        'up_cnts': up_cnts,
        'manager': re_manager.search(manager.get_text()).group(1) if manager and re_manager.search(manager.get_text()) else None,
        'sub_managers': [sub_manager['title'] for sub_manager in sub_managers] if sub_managers else None,
        'board_cnt': board_cnt,
    }


def fetch_comments(gall_num, e_s_n_o='3eabc219ebdd65f4'):
    params = {
        'id': 'virtual_streamer',
        'no': gall_num,
        'cmt_id': 'virtual_streamer',
        'cmt_no': gall_num,
        'e_s_n_o': e_s_n_o,
        'comment_page': 1,
        '_GALLTYPE_': 'MI',
    }
    body, crawl_time, status_code = crawl('https://gall.dcinside.com/board/comment/', params, 'post')
    if not body:
        return None, crawl_time, status_code

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None, crawl_time, status_code

    comments = parsed.get('comments', [])
    return {
        'crawl_time': crawl_time,
        'gall_num': str(gall_num),
        'total_cnt': parsed.get('total_cnt', len(comments)),
        'comments': comments,
    }, crawl_time, status_code


def export_monthly_posts(db, export_dir):
    now = datetime.now()
    target_year = now.year
    target_month = now.month

    start = datetime(target_year, target_month, 1)
    if target_month == 12:
        end = datetime(target_year + 1, 1, 1)
    else:
        end = datetime(target_year, target_month + 1, 1)

    rows = list(db['post'].find({'crawl_time': {'$gte': start.strftime('%Y-%m-%d 00:00:00'), '$lt': end.strftime('%Y-%m-%d 00:00:00')}}))
    if not rows:
        return None

    os.makedirs(export_dir, exist_ok=True)
    file_name = f"{target_year}{target_month:02d}posts.csv"
    file_path = os.path.join(export_dir, file_name)

    fieldnames = [
        'crawl_time', 'gall_num', 'title', 'nickname', 'uid', 'ip', 'gall_date',
        'content', 'embed_links', 'img_links', 'view_cnt', 'comment_cnt',
        'up_cnt', 'up_fix_cnt', 'down_cnt', 'head_text'
    ]

    with open(file_path, 'w', newline='', encoding='utf-8-sig') as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            clean_row = {k: row.get(k) for k in fieldnames}
            clean_row['embed_links'] = json.dumps(clean_row['embed_links'], ensure_ascii=False)
            clean_row['img_links'] = json.dumps(clean_row['img_links'], ensure_ascii=False)
            writer.writerow(clean_row)

    return file_path


def ensure_indexes(db):
    db['post'].create_index('gall_num', unique=True)
    db['board'].create_index('board_cnt')
    db['comment'].create_index('gall_num', unique=True)


client = MongoClient(os.getenv('MONGO_HOST', 'mongo'), int(os.getenv('MONGO_PORT', '27017')))
db = client['virtual_streamer_gall']
ensure_indexes(db)

base_url = 'https://gall.dcinside.com/mini/board/lists'
view_url = 'https://gall.dcinside.com/mini/board/view/'

page_cnt = 100000
board_cnt = -1
end_gall_num = 10000000000

if os.path.exists('./crawl_info.txt'):
    with open('./crawl_info.txt', 'r', encoding='utf-8') as f:
        board_cnt = int(f.readline())
        end_gall_num = int(f.readline())


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

try:
    log(f'start crawler with board_cnt={board_cnt}, end_gall_num={end_gall_num}')
    board_gall_nums = []
    board_gall_nums_arr = [ith_board['gall_nums'] for ith_board in db['board'].find({'board_cnt': board_cnt})]
    for ith_gall_nums in board_gall_nums_arr:
        board_gall_nums += list(map(int, ith_gall_nums))

    post_gall_nums = list(map(int, db['post'].distinct('gall_num')))
    gall_nums = list(set(board_gall_nums) - set(post_gall_nums))

    while True:
        work_start = time.time()

        if not gall_nums:
            board_cnt += 1
            log(f'collect board list for board_cnt={board_cnt}')
            for i in range(1, page_cnt):
                params = {
                    'id': 'virtual_streamer',
                    'list_num': '100',
                    'sort_type': 'N',
                    'page': i,
                }
                html, crawl_time, status_code = crawl(base_url, params, 'get')
                if html:
                    board_doc = parse_board(html, crawl_time, board_cnt)
                    if not board_doc:
                        break
                    db['board'].insert_one(board_doc)
                    gall_nums_part = board_doc['gall_nums']
                    time.sleep(2)
                else:
                    with open('./boarderror.txt', 'a', encoding='utf-8') as f:
                        f.write('error at: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n')
                        f.write('not 200 at status_code: ' + str(status_code) + '\n')
                        f.write('not 200 at board_cnt: ' + str(board_cnt) + '\n')
                        f.write('not 200 at end_gall_num: ' + str(end_gall_num) + '\n')
                        f.write('not 200 at ith page: ' + str(i) + '\n')
                    continue

                gall_nums += gall_nums_part
                if end_gall_num >= min(gall_nums):
                    break

        if db['post'].estimated_document_count() == 0 and gall_nums and max(gall_nums) <= end_gall_num:
            log(
                'post collection is empty and current board snapshot has no gall_num greater than '
                f'end_gall_num({end_gall_num}). Keep end_gall_num and fetch next board snapshot.'
            )
            gall_nums = []
            continue

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
                post_doc = parse_post(html, crawl_time)
                if post_doc:
                    db['post'].update_one({'gall_num': post_doc['gall_num']}, {'$set': post_doc}, upsert=True)
                    log(f"upsert post gall_num={post_doc['gall_num']}")

                    comment_doc, _, _ = fetch_comments(gall_num)
                    if comment_doc is not None:
                        db['comment'].update_one({'gall_num': comment_doc['gall_num']}, {'$set': comment_doc}, upsert=True)
                        log(f"upsert comments gall_num={comment_doc['gall_num']} total_cnt={comment_doc['total_cnt']}")

                time.sleep(2)
            else:
                with open('./' + str(gall_num) + '.txt', 'w', encoding='utf-8') as f:
                    f.write('error at: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n')
                    f.write('not 200 at board_cnt: ' + str(board_cnt) + '\n')
                    f.write('not 200 at end_gall_num: ' + str(end_gall_num) + '\n')
                    f.write('not 200 at gall_num: ' + str(gall_num) + '\n')
                    f.write('not 200 at status_code: ' + str(status_code) + '\n')

        end_gall_num = max([int(ith_post['gall_num']) for ith_post in db['post'].find({}, {'_id': 0, 'gall_num': 1})])
        with open('./crawl_info.txt', 'w', encoding='utf-8') as f:
            f.write(str(board_cnt) + '\n')
            f.write(str(end_gall_num) + '\n')

        export_monthly_posts(db, './backups')

        gall_nums = []
        work_end = time.time()
        while work_end - work_start < 120:
            work_end = time.time()
except Exception as e:
    with open('./error.txt', 'w', encoding='utf-8') as f:
        f.write('error at: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n')
        f.write('error name is: ' + str(e) + '\n')
        f.write('error at board_cnt: ' + str(board_cnt) + '\n')
        f.write('error at end_gall_num: ' + str(end_gall_num) + '\n')
