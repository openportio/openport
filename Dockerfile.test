FROM python:3.6.10-stretch
WORKDIR /apps/openport
COPY setup.py /apps/openport/setup.py
COPY requirements.txt /apps/openport/
COPY requirements.test.txt /apps/openport/
RUN pip install -r requirements.test.txt
ADD . /apps/openport
CMD tox
