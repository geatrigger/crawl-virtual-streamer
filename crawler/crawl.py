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
import traceback
from datetime import datetime

re_text = re.compile('[^가-힣a-zA-Z0-9.]')
re_manager = re.compile(r'[(](\S+)[)]')

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
}

comment_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
}



def crawl(base_url, params, how, request_headers=None):
    req_headers = request_headers or headers

    if how == 'get':
        res = s.get(base_url, headers=req_headers, params=params, timeout=15)
    elif how == 'post':
        res = s.post(base_url, headers=req_headers, data=params, timeout=15)
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
    e_s_n_o = soup.select_one('#e_s_n_o')

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
        'e_s_n_o': e_s_n_o.get('value') if e_s_n_o else None,
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


def fetch_comments(gall_num, e_s_n_o=None):
    params = {
        'id': 'virtual_streamer',
        'no': gall_num,
        'cmt_id': 'virtual_streamer',
        'cmt_no': gall_num,
        'e_s_n_o': e_s_n_o or '',
        'comment_page': 1,
        '_GALLTYPE_': 'MI',
    }
    body, crawl_time, status_code = crawl('https://gall.dcinside.com/board/comment/', params, 'post', request_headers=comment_headers)
    if not body:
        return None, crawl_time, status_code

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None, crawl_time, status_code

    comments = parsed.get('comments')
    if comments is None:
        comments = []
    return {
        'crawl_time': crawl_time,
        'gall_num': str(gall_num),
        'total_cnt': parsed.get('total_cnt', len(comments)),
        'comments': comments,
    }, crawl_time, status_code


def upsert_comment_data(db, comment_doc):
    db['comment'].update_one({'gall_num': comment_doc['gall_num']}, {'$set': comment_doc}, upsert=True)

    history_doc = {
        'gall_num': comment_doc['gall_num'],
        'crawl_time': comment_doc['crawl_time'],
        'total_cnt': comment_doc['total_cnt'],
        'comments': comment_doc['comments'],
    }
    db['comment_history'].update_one(
        {'gall_num': history_doc['gall_num'], 'crawl_time': history_doc['crawl_time']},
        {'$setOnInsert': history_doc},
        upsert=True,
    )


def fetch_post_with_retry(gall_num):
    params = {
        'id': 'virtual_streamer',
        'no': gall_num,
    }
    post_doc = None
    last_html = None
    last_status_code = None
    crawl_time = None

    for post_attempt in range(1, post_retry_count + 1):
        html, crawl_time, status_code = crawl(view_url, params, 'get')
        last_html = html
        last_status_code = status_code
        if not html:
            log_debug(
                f'post fetch failed gall_num={gall_num} attempt={post_attempt}/{post_retry_count} '
                f'status={status_code}'
            )

        if html:
            post_doc = parse_post(html, crawl_time)
            if post_doc:
                log_debug(f'post parsed gall_num={gall_num} attempt={post_attempt}/{post_retry_count}')
                break
            log_debug(
                f'post parse returned None gall_num={gall_num} attempt={post_attempt}/{post_retry_count} '
                f'status={status_code}'
            )
        if post_attempt < post_retry_count:
            time.sleep(retry_sleep_seconds)

    return post_doc, last_html, last_status_code, crawl_time


def collect_recent_comment_history(db, recent_board_count, recent_post_target):
    if recent_board_count <= 0:
        log_debug('skip recent comment history collection because recent_board_count <= 0')
        return 0

    board_docs = list(db['board'].find({}, {'_id': 0, 'board_cnt': 1, 'gall_nums': 1}).sort('board_cnt', -1).limit(recent_board_count))
    if not board_docs:
        log_warn('skip recent comment history collection because there are no board snapshots')
        return 0

    target_gall_nums = []
    seen_gall_nums = set()
    boards_used = 0
    for board_doc in board_docs:
        boards_used += 1
        for gall_num in board_doc.get('gall_nums', []):
            gall_num_str = str(gall_num)
            if gall_num_str in seen_gall_nums:
                continue
            seen_gall_nums.add(gall_num_str)
            target_gall_nums.append(gall_num_str)

        if recent_post_target > 0 and len(target_gall_nums) >= recent_post_target:
            break

    if recent_post_target > 0:
        target_gall_nums = target_gall_nums[:recent_post_target]

    log(
        f'recent comment history collection start boards={boards_used} '
        f'target_posts={len(target_gall_nums)} recent_board_count={recent_board_count} '
        f'recent_post_target={recent_post_target}'
    )

    collected_comments = 0
    missing_posts = 0
    failed_comments = 0

    for idx, gall_num in enumerate(target_gall_nums, start=1):
        post_doc = db['post'].find_one({'gall_num': gall_num}, {'_id': 0, 'gall_num': 1, 'e_s_n_o': 1})
        if not post_doc or post_doc.get('e_s_n_o') is None:
            fetched_post_doc, _, _, _ = fetch_post_with_retry(gall_num)
            if fetched_post_doc:
                db['post'].update_one({'gall_num': fetched_post_doc['gall_num']}, {'$set': fetched_post_doc}, upsert=True)
                post_doc = fetched_post_doc
            else:
                missing_posts += 1
                log_warn(f'recent comment history skipped gall_num={gall_num} reason=missing_post')
                continue

        comment_doc = None
        comment_status = None
        for comment_attempt in range(1, comment_retry_count + 1):
            comment_doc, _, comment_status = fetch_comments(gall_num, post_doc.get('e_s_n_o'))
            if comment_doc is not None:
                upsert_comment_data(db, comment_doc)
                collected_comments += 1
                break
            log_debug(
                f'recent comment history fetch failed gall_num={gall_num} '
                f'attempt={comment_attempt}/{comment_retry_count} status={comment_status}'
            )
            if comment_attempt < comment_retry_count:
                time.sleep(retry_sleep_seconds)

        if comment_doc is None:
            failed_comments += 1
            log_warn(
                f'recent comment history fetch failed after retries gall_num={gall_num} '
                f'retries={comment_retry_count} status={comment_status}'
            )

        time.sleep(2)

        if idx % 20 == 0:
            log(
                f'recent comment history progress {idx}/{len(target_gall_nums)} '
                f'collected={collected_comments} missing_posts={missing_posts} failed_comments={failed_comments}'
            )

    log(
        f'recent comment history collection done target_posts={len(target_gall_nums)} '
        f'collected={collected_comments} missing_posts={missing_posts} failed_comments={failed_comments}'
    )
    return collected_comments


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
    db['comment_history'].create_index([('gall_num', 1), ('crawl_time', 1)], unique=True)


client = MongoClient(os.getenv('MONGO_HOST', 'mongo'), int(os.getenv('MONGO_PORT', '27017')))
db = client['virtual_streamer_gall']
ensure_indexes(db)

base_url = 'https://gall.dcinside.com/mini/board/lists'
view_url = 'https://gall.dcinside.com/mini/board/view/'

page_cnt = 100000
board_cnt = -1
end_gall_num = 10000000000
board_stop_match_cnt = int(os.getenv('BOARD_STOP_MATCH_COUNT', '5'))
post_retry_count = int(os.getenv('POST_RETRY_COUNT', '3'))
comment_retry_count = int(os.getenv('COMMENT_RETRY_COUNT', '3'))
retry_sleep_seconds = float(os.getenv('RETRY_SLEEP_SECONDS', '1'))
recent_comment_history_interval_seconds = int(os.getenv('RECENT_COMMENT_HISTORY_INTERVAL_SECONDS', '600'))
recent_comment_history_board_count = int(os.getenv('RECENT_COMMENT_HISTORY_BOARD_COUNT', '5'))
recent_comment_history_post_target = int(os.getenv('RECENT_COMMENT_HISTORY_POST_TARGET', '100'))

if os.path.exists('./crawl_info.txt'):
    with open('./crawl_info.txt', 'r', encoding='utf-8') as f:
        board_cnt = int(f.readline())
        end_gall_num = int(f.readline())


LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_LEVEL_PRIORITY = {
    'DEBUG': 10,
    'INFO': 20,
    'WARN': 30,
    'ERROR': 40,
}


def should_log(level):
    configured = LOG_LEVEL_PRIORITY.get(LOG_LEVEL, LOG_LEVEL_PRIORITY['INFO'])
    current = LOG_LEVEL_PRIORITY.get(level, LOG_LEVEL_PRIORITY['INFO'])
    return current >= configured


def log(msg, level='INFO'):
    upper_level = level.upper()
    if not should_log(upper_level):
        return
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{upper_level}] {msg}", flush=True)


def log_debug(msg):
    log(msg, 'DEBUG')


def log_warn(msg):
    log(msg, 'WARN')


def log_error(msg):
    log(msg, 'ERROR')


def html_snippet(html, limit=200):
    if html is None:
        return None
    try:
        text = html.decode('utf-8') if isinstance(html, (bytes, bytearray)) else str(html)
    except UnicodeDecodeError:
        text = html.decode('utf-8', errors='replace') if isinstance(html, (bytes, bytearray)) else str(html)
    text = ' '.join(text.split())
    return text[:limit]

try:
    log(
        f'start crawler board_cnt={board_cnt}, end_gall_num={end_gall_num}, '
        f'log_level={LOG_LEVEL}, board_stop_match_cnt={board_stop_match_cnt}, '
        f'post_retry_count={post_retry_count}, comment_retry_count={comment_retry_count}, '
        f'retry_sleep_seconds={retry_sleep_seconds}, '
        f'recent_comment_history_interval_seconds={recent_comment_history_interval_seconds}, '
        f'recent_comment_history_board_count={recent_comment_history_board_count}, '
        f'recent_comment_history_post_target={recent_comment_history_post_target}'
    )
    board_gall_nums = []
    board_gall_nums_arr = [ith_board['gall_nums'] for ith_board in db['board'].find({'board_cnt': board_cnt})]
    for ith_gall_nums in board_gall_nums_arr:
        board_gall_nums += list(map(int, ith_gall_nums))

    post_gall_nums = list(map(int, db['post'].distinct('gall_num')))
    gall_nums = [gall_num for gall_num in (set(board_gall_nums) - set(post_gall_nums)) if gall_num > end_gall_num]
    last_recent_comment_history_at = 0

    while True:
        work_start = time.time()

        if not gall_nums:
            board_cnt += 1
            log(f'collect board snapshot board_cnt={board_cnt}')
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
                        log_debug(f'board page parse returned empty board_cnt={board_cnt} page={i}')
                        break
                    db['board'].insert_one(board_doc)
                    gall_nums_part = board_doc['gall_nums']
                    log_debug(
                        f'board page collected board_cnt={board_cnt} page={i} '
                        f'gall_nums_count={len(gall_nums_part)} '
                        f'min={min(gall_nums_part) if gall_nums_part else None} '
                        f'max={max(gall_nums_part) if gall_nums_part else None}'
                    )
                    time.sleep(2)
                else:
                    with open('./boarderror.txt', 'a', encoding='utf-8') as f:
                        f.write('error at: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n')
                        f.write('not 200 at status_code: ' + str(status_code) + '\n')
                        f.write('not 200 at board_cnt: ' + str(board_cnt) + '\n')
                        f.write('not 200 at end_gall_num: ' + str(end_gall_num) + '\n')
                        f.write('not 200 at ith page: ' + str(i) + '\n')
                    log_warn(f'board fetch non-200 board_cnt={board_cnt} page={i} status={status_code}')
                    continue

                gall_nums += gall_nums_part
                collected_old_cnt = sum(1 for gall_num in gall_nums if gall_num <= end_gall_num)
                if collected_old_cnt >= board_stop_match_cnt:
                    log_debug(
                        f'stop board snapshot due to old match board_cnt={board_cnt} page={i} '
                        f'collected_old_cnt={collected_old_cnt}'
                    )
                    break

        with open('./crawl_info.txt', 'w', encoding='utf-8') as f:
            f.write(str(board_cnt) + '\n')
            f.write(str(end_gall_num) + '\n')

        gall_nums = sorted(list(set(gall_nums)), reverse=True)
        log(f'candidate gall_nums={len(gall_nums)} max={max(gall_nums) if gall_nums else None} min={min(gall_nums) if gall_nums else None} end_gall_num={end_gall_num}')

        processed_posts = 0
        processed_comments = 0
        skipped_by_end = 0
        parse_post_failed = 0
        view_non_200 = 0
        abnormal_access = 0
        progress_every = int(os.getenv('PROGRESS_LOG_EVERY', '200'))
        to_process_cnt = sum(1 for gall_num in gall_nums if gall_num > end_gall_num)

        for idx, gall_num in enumerate(gall_nums, start=1):
            if idx == 1:
                log(f'begin processing total_candidates={len(gall_nums)} to_process={to_process_cnt}')
            if gall_num <= end_gall_num:
                skipped_by_end += 1
                continue
            post_doc, last_html, last_status_code, _ = fetch_post_with_retry(gall_num)

            if post_doc:
                db['post'].update_one({'gall_num': post_doc['gall_num']}, {'$set': post_doc}, upsert=True)
                processed_posts += 1

                comment_doc = None
                comment_status = None
                for comment_attempt in range(1, comment_retry_count + 1):
                    comment_doc, _, comment_status = fetch_comments(gall_num, post_doc.get('e_s_n_o'))
                    if comment_doc is not None:
                        log_debug(
                            f'comment fetched gall_num={gall_num} attempt={comment_attempt}/{comment_retry_count} '
                            f'total_cnt={comment_doc.get("total_cnt")}'
                        )
                        break
                    log_debug(
                        f'comment fetch failed gall_num={gall_num} attempt={comment_attempt}/{comment_retry_count} '
                        f'status={comment_status}'
                    )
                    if comment_attempt < comment_retry_count:
                        time.sleep(retry_sleep_seconds)

                if comment_doc is not None:
                    upsert_comment_data(db, comment_doc)
                    processed_comments += 1
                else:
                    log_warn(f'comment fetch failed after retries gall_num={gall_num} retries={comment_retry_count} status={comment_status}')
            else:
                if last_html is None:
                    view_non_200 += 1
                    with open('./' + str(gall_num) + '.txt', 'w', encoding='utf-8') as f:
                        f.write('error at: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n')
                        f.write('not 200 at board_cnt: ' + str(board_cnt) + '\n')
                        f.write('not 200 at end_gall_num: ' + str(end_gall_num) + '\n')
                        f.write('not 200 at gall_num: ' + str(gall_num) + '\n')
                        f.write('not 200 at status_code: ' + str(last_status_code) + '\n')
                else:
                    parse_post_failed += 1
                    if parse_post_failed <= 10:
                        snippet = html_snippet(last_html)
                        if snippet and '정상적인 접근이 아닙니다' in snippet:
                            abnormal_access += 1
                        log_warn(
                            f'post parse failed after retries gall_num={gall_num} retries={post_retry_count} '
                            f'status={last_status_code} html_prefix={snippet}'
                        )

            time.sleep(2)

            if progress_every > 0 and idx % progress_every == 0:
                elapsed = int(time.time() - work_start)
                log(
                    f'progress {idx}/{len(gall_nums)} elapsed={elapsed}s '
                    f'posts_upserted={processed_posts} comments_upserted={processed_comments} '
                    f'skipped_by_end={skipped_by_end} parse_post_failed={parse_post_failed} view_non_200={view_non_200}'
                )

        log(
            f'cycle summary board_cnt={board_cnt} candidates={len(gall_nums)} skipped_by_end={skipped_by_end} '
            f'view_non_200={view_non_200} parse_post_failed={parse_post_failed} abnormal_access={abnormal_access} posts_upserted={processed_posts} comments_upserted={processed_comments}'
        )

        all_post_nums = [int(ith_post['gall_num']) for ith_post in db['post'].find({}, {'_id': 0, 'gall_num': 1}) if ith_post.get('gall_num') is not None]
        if all_post_nums:
            end_gall_num = max(all_post_nums)
        with open('./crawl_info.txt', 'w', encoding='utf-8') as f:
            f.write(str(board_cnt) + '\n')
            f.write(str(end_gall_num) + '\n')

        export_monthly_posts(db, './backups')

        now_ts = time.time()
        if recent_comment_history_interval_seconds > 0 and now_ts - last_recent_comment_history_at >= recent_comment_history_interval_seconds:
            collect_recent_comment_history(
                db,
                recent_comment_history_board_count,
                recent_comment_history_post_target,
            )
            last_recent_comment_history_at = now_ts

        gall_nums = []
        work_end = time.time()
        while work_end - work_start < 120:
            work_end = time.time()
except Exception as e:
    stack = traceback.format_exc()
    log_error(f'crawler crashed with exception={e}')
    log_error(stack)
    with open('./error.txt', 'w', encoding='utf-8') as f:
        f.write('error at: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n')
        f.write('error name is: ' + str(e) + '\n')
        f.write('error at board_cnt: ' + str(board_cnt) + '\n')
        f.write('error at end_gall_num: ' + str(end_gall_num) + '\n')
        f.write('traceback:\n' + stack + '\n')
