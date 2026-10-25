# Receipted API as an AWS Lambda container image.
# Build:  docker build -f api/Dockerfile -t receipted-api .
# The policy index and the embedding model are baked in at build time so a cold start downloads nothing.
FROM public.ecr.aws/lambda/python:3.12

# Lambda's filesystem is read-only except /tmp: everything Receipted writes goes there.
ENV RECEIPTED_DATA_DIR=/tmp/receipted \
    RECEIPTED_BAKED_HOME=/var/task/home \
    HOME=/var/task/home \
    PYTHONPATH=/var/task/src

COPY api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY src ./src
COPY fixtures ./fixtures
COPY api/app.py ./api/app.py
COPY api/cache_seed ./cache_seed

# Build the policy index into the image: a persistent Chroma store at /var/task/chroma_db (copied to /tmp at
# runtime, since Chroma writes to its store) and the embedding model it downloads into $HOME/.cache.
RUN mkdir -p /var/task/home && RECEIPTED_CHROMA_PATH=/var/task/chroma_db python -c "import sys; sys.path.insert(0,'src'); from receipted.retrieve import collections; collections(); collections(currency='SGD')" \
    && chmod -R a+rX /var/task/home /var/task/chroma_db   # the build runs as root; Lambda runs as another user and must read these

CMD ["api.app.handler"]
