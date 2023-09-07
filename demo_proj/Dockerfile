FROM python:3.10.2-slim-bullseye

#ENV PIP_DISABLE_PIP_VERSION_CHECK 1
#ENV PYTHONDONTWRITEBYTECODE 1
#ENV PYTHONUNBUFFERED 1
#
#WORKDIR /code
#
#COPY ./requirements.txt .
#
#RUN apt-get update
#RUN apt-get install -y libpq-dev gcc git
#RUN pip install -r requirements.txt
#RUN pip install git+https://github.com/ra-systems/django-slick-reporting.git@develop#egg=django-slick-reporting --upgrade
#
COPY . .
RUN ls -al

