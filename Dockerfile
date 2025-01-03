FROM python:3.12

RUN mkdir /data
ENV CYCAX_VAR_DIR=/data
RUN mkdir /app
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt


# ENV WATCHFILES_FORCE_POLLING=true
ENTRYPOINT /app/src/start.sh

# FROM ubuntu:22.04
# 
# 
# RUN apt update; apt install -y python3-pip curl
# ENV PIP_ROOT_USER_ACTION=ignore
# ENV PIP_EXTRA_INDEX_URL="https://gitea.tu.tsolo.net/api/packages/Tsolo/pypi/simple/"
# 
# RUN --mount=type=cache,target=/root/.cache pip3 install -r /app/requirements.txt
# RUN pip3 install .
