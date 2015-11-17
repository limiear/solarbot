MAINTAINER Eloy Adonis Colell
FROM ubuntu
RUN make virtualenv deploy; make run
