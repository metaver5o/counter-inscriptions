FROM --platform=linux/amd64 counterparty/counterparty:latest

USER root

# patch_mime.py is in the same dir as this Dockerfile (xcp-api-mime/)
# Build context is xcp-api-mime/ when using xcp-api-mime/docker-compose.yml
COPY patch_mime.py /tmp/patch_mime.py
RUN python3 /tmp/patch_mime.py && rm /tmp/patch_mime.py

COPY entrypoint.sh /entrypoint-custom.sh
RUN chmod +x /entrypoint-custom.sh

EXPOSE 4000
ENTRYPOINT ["/entrypoint-custom.sh"]
