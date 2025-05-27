# SPDX-FileCopyrightText: 2025 Tsolo.io
#
# SPDX-License-Identifier: Apache-2.0

FROM python:3.12

RUN mkdir /data
ENV CYCAX_VAR_DIR=/data
RUN mkdir /app
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# ENV WATCHFILES_FORCE_POLLING=true
ENTRYPOINT /app/src/start.sh
