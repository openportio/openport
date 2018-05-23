FROM python:2.7
ADD . /apps/openport
WORKDIR /apps/openport
RUN pip install -e .
CMD python -m openport
