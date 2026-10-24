# Receipted API as an AWS Lambda container image.
# Build:  docker build -f api/Dockerfile -t receipted-api .
# The policy index and the embedding model are baked in at build time so a cold start downloads nothing.
FROM public.ecr.aws/lambda/python:3.12

# Lambda's filesystem is read-only except /tmp: everything Receipted writes goes there.
ENV RECEIPTED_DATA_DIR=/tmp/receipted \
    RECEIPTED_CHROMA_EPHEMERAL=1 \
    RECEIPTED_BAKED_HOME=/var/task/home \
    HOME=/var/task/home \
    PYTHONPATH=/var/task/src

COPY api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY src ./src
COPY fixtures ./fixtures
COPY api/app.py ./api/app.py

# Warm the embedding model into the image (chroma downloads it to $HOME/.cache on first use)
RUN mkdir -p /var/task/home && python -c "import sys; sys.path.insert(0,'src'); from receipted.retrieve import collections; collections(); collections(currency='SGD')"

CMD ["api.app.handler"]
