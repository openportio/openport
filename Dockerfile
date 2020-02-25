FROM python:3.6.10-stretch
WORKDIR /apps/openport
COPY setup.py /apps/openport/setup.py
RUN pip install -e .
ADD . /apps/openport
CMD python -m openport
