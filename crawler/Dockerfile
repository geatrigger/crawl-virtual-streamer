# FROM python:3
FROM arm32v7/python:3.9.2
RUN mkdir /script
# ADD crawl.py /script
# ADD wait-for-it.sh /script
WORKDIR /script
RUN pip install pymongo==3.13.0
RUN pip install requests
RUN pip install bs4
RUN pip install lxml
RUN pip install pymysql
