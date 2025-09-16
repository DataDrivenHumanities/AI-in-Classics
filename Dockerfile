FROM python:3.10-bullseye
LABEL maintainer="ebozia ai-in-classics"
EXPOSE 8080
WORKDIR /home
# ADD src/ /src/
# ADD Resources /Resources/
ADD requirements.txt .
ADD build.sh .
ADD cleanupXML.py .
ADD LICENSE .
ADD README.md .
ADD .env .
RUN ["apt-get", "upgrade"]
RUN ["apt-get", "update"]
RUN ["apt-get", "install", "ca-certificates", "lsb-release", "wget", "-y"]
RUN ["apt-get", "install", "cmake", "-y"]
RUN ["apt-get", "install", "fish", "-y"]
RUN ["pip", "install", "--upgrade", "pip"]
RUN ["./build.sh"]
ENTRYPOINT ["/usr/bin/fish"]