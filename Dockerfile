FROM mysql:8.0.21

ENV LC_ALL=C.UTF-8
ENV character-set-server utf8
ENV collation-server utf8_general_ci
ENV default-character-set utf8
ENV default-collation utf8_general_ci

ENV MYSQL_DATABASE slack_db
ENV MYSQL_ROOT_PASSWORD qwer1234

WORKDIR /home/slack
COPY ./* /home/slack/

EXPOSE 3306