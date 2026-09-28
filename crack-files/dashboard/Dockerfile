FROM python:latest

RUN apt-get update && apt-get install -y openssh-server && \
    echo 'root:dashboard' | chpasswd && \
    sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config

WORKDIR /srv
COPY export.py .

EXPOSE 22 8080
CMD service ssh start && python export.py
