import pymysql

conn = pymysql.connect(host='mysql', port=3306, user='root', passwd='bus', db='virtual_streamer_board')
cur = conn.cursor()
sql = '''create table test(
    name varchar(20) primary key,
    num int not null
);'''
cur.execute(sql)
conn.commit()
conn.close()
with open('./hi.txt', 'w', encoding='utf-8') as f:
    f.write('where are you slave..\n')
while True:
    pass
