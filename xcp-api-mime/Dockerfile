FROM counterparty/counterparty-server:latest

USER root

# Install lightweight networking tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and execute the custom MIME parsing patch
COPY xcp-api-mime/patch_mime.py /tmp/patch_mime.py
RUN python3 /tmp/patch_mime.py && rm /tmp/patch_mime.py

WORKDIR /root
EXPOSE 4000

# Start core binary directly
CMD ["counterparty-server", "start", "--api-host=0.0.0.0", "--api-port=4000", "--rpc-host=0.0.0.0"]