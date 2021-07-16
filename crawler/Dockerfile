FROM python:3
RUN mkdir /script
# ADD crawl.py /script
# ADD wait-for-it.sh /script
WORKDIR /script
RUN apt-get update
RUN pip install pymysql
RUN pip install pymongo
RUN pip install requests
RUN pip install bs4
RUN pip install lxml