FROM postgres:18@sha256:4ef4dbc939d61acea57712655ddb4b4ab27419c913f94cca0cd57cb3ea3c2280

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-18-pgvector=0.8.6-1.pgdg13+1 \
    && rm -rf /var/lib/apt/lists/*

COPY init_vector.sql /docker-entrypoint-initdb.d/init_vector.sql
