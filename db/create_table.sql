drop database if exists virtual_streamer_board;
create database virtual_streamer_board default character set utf8 collate utf8_general_ci;
use virtual_streamer_board;

drop table if exists post;
drop table if exists word;
drop table if exists link;

create table post (
	gall_num int primary key,
    title varchar(100),
    nickname varchar(20),
    uid varchar(20),
    ip varchar(10),
    gall_date timestamp,
    content text
);

create table word (
	gall_num int,
    word varchar(20),
    word_type varchar(20),
    word_count int,
    primary key (gall_num, word),
    foreign key (gall_num) references post(gall_num)
);

create table link (
	gall_num int,
	link varchar(200),
    link_type varchar(20),
    link_count int,
    virtual varchar(20),
    primary key (gall_num, link),
    foreign key (gall_num) references post(gall_num)
);

insert into post values 
	(8862, "볼거없나", "ㅇㅇ", null, "175.223", "2021.02.04 15:54:52", "백수되어서 볼거 필요함 빨리"), 
	(5786, "나만 기루방송 멈추냐", "ㅅㅇ방송켜", "eesh1106", null, "2021.01.24 23:55:21", "자꾸 뚝뚝 끊어지는데\nhttps://www.youtube.com/watch?v=BvCaSvWM-AU&feature=youtu\n.be");

insert into word values
	(8862, "볼", "Verb", 2),
	(8862, "거", "Noun", 2),
	(8862, "백수", "Noun", 1),
	(5786, "나", "Noun", 1);
	
insert into link values
	(5786, "https://www.youtube.com/watch?v=BvCaSvWM-AU&feature=youtu\n.be", "youtube", 1, "신기루");