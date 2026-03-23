FROM arm32v7/python:3

# contourpy (dependency of matplotlib) can hit GCC 14 warnings promoted to errors
# when built from source on arm32. Relax the specific warnings so the build succeeds.
ENV CXXFLAGS="-Wno-array-bounds -Wno-free-nonheap-object"

RUN pip install --upgrade pip
RUN pip install jupyter
RUN pip install pymysql
RUN pip install pymongo
RUN pip install requests
RUN pip install bs4
RUN pip install pandas
RUN pip install plotly
RUN pip install tqdm
RUN pip install matplotlib
