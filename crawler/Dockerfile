FROM python:3
RUN mkdir /script
# ADD crawl.py /script
# ADD wait-for-it.sh /script
WORKDIR /script
RUN apt-get update
RUN pip install pymysql
RUN pip install pymongo